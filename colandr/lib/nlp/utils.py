import collections
import itertools
import logging
import typing as t
from collections.abc import Iterable
from operator import itemgetter

import lingua
import spacy
import textacy
from spacy.tokens import Doc


LOGGER = logging.getLogger(__name__)

LANG_DETECTOR = (
    lingua.LanguageDetectorBuilder.from_all_languages()
    .with_low_accuracy_mode()
    # alternatively, we might try detecting only those languages for which we have models
    # and run that in "high-accuracy" mode; unclear if this is worth the trade-off
    # .from_languages(Language.CHINESE, Language.ENGLISH, Language.FRENCH, Language.JAPANESE, Language.SPANISH)
    .with_minimum_relative_distance(0.8)
    .build()
)


def detect_language(text: str) -> t.Optional[str]:
    """
    Detect language of input text, and return it as a ISO-639-1 short code
    if sufficiently confident or None otherwise.
    """
    lang = LANG_DETECTOR.detect_language_of(text)
    return lang.iso_code_639_1.name.lower() if lang is not None else None


def detect_languages(texts: Iterable[str]) -> list[t.Optional[str]]:
    """
    Detect languages of input texts, and return them as ISO-639-1 short codes
    if sufficiently confident or None otherwise, in the same order as inputs.
    """
    langs = LANG_DETECTOR.detect_languages_in_parallel_of(texts)  # type: ignore
    return [
        lang.iso_code_639_1.name.lower() if lang is not None else None for lang in langs
    ]


def get_lang_to_models() -> dict[str, list[str]]:
    """Get a mapping of ISO language code to installed spacy language models."""
    lang_to_models = collections.defaultdict(list)
    models = spacy.util.get_installed_models()
    for model in models:
        if "_" in model:
            lang, _ = model.split("_", 1)
            lang_to_models[lang].append(model)
        else:
            LOGGER.warning("found unexpected spacy model name: %s", model)

    return dict(lang_to_models)


def process_texts_into_docs(
    texts: Iterable[str],
    *,
    max_len: t.Optional[int] = 1000,
    min_prob: t.Optional[float] = 0.5,
    fallback_lang: t.Optional[str] = "en",
    **kwargs,
) -> Iterable[t.Optional[Doc]]:
    """
    Args:
        texts
        max_len: Maximum number of chars (code points) in each text to include
            when identifying its language and processing into a spacy document.
        min_prob: Minimum probability of language prediction for it to be used;
            if prob < min_prob, ``fallback_lang`` is used instead.
        fallback_lang: Fallback language used in place of low-probability predictions.
        **kwargs: Passed as-is into :func:`textacy.load_spacy_lang()` .
    """
    identify_lang = textacy.identify_lang
    # clean up whitespace, since lang identifier model is picky
    texts = (text.strip().replace("\n", " ") for text in texts)
    # truncate texts, optionally
    if max_len is not None:
        texts = (text[:max_len] for text in texts)
    # identify most probable language (w/ optional fallback) for texts
    if min_prob is not None:
        text_lang_probs = (
            (text, identify_lang(text, with_probs=True)) for text in texts
        )
        text_langs = (
            (text, lang) if prob >= min_prob else (text, fallback_lang)
            for text, (lang, prob) in text_lang_probs
        )
    else:
        text_langs = ((text, identify_lang(text, with_probs=False)) for text in texts)
    # join texts to langs, then iterate over lang-groups for processing efficiency
    lang_models = get_lang_to_models()
    for lang, tl_grp in itertools.groupby(text_langs, key=itemgetter(1)):
        if lang in lang_models:
            spacy_lang = textacy.load_spacy_lang(lang_models[lang][0], **kwargs)
            spacy_docs = spacy_lang.pipe((text for text, _ in tl_grp), n_process=1)
            for spacy_doc in spacy_docs:
                yield spacy_doc
        else:
            num_texts = sum(1 for _ in tl_grp)
            LOGGER.info(
                "unable to load spacy model for %s texts with lang='%s'; docs set to null ...",
                num_texts,
                lang,
            )
            for _ in range(num_texts):
                yield None
