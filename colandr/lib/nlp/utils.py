import collections
import functools
import itertools
import logging
import typing as t
from collections.abc import Iterable
from operator import itemgetter

import lingua
import spacy
from spacy.language import Language as SpacyLang
from spacy.tokens import Doc as SpacyDoc


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


def get_lang_to_models() -> dict[str, str]:
    """Get a mapping of ISO language code to installed spacy language models."""
    lang_to_models = {}
    models = spacy.util.get_installed_models()
    for model in models:
        if "_" in model:
            lang, _ = model.split("_", 1)
            lang_to_models[lang] = model
        else:
            LOGGER.warning("found unexpected spacy model name: %s", model)

    return lang_to_models


@functools.lru_cache(maxsize=10)
def load_spacy_lang(name: str, **kwargs) -> SpacyLang:
    """
    Load a spaCy ``Language`` — a shared vocabulary and language-specific data
    for tokenizing text, and (if available) model data and a processing pipeline
    containing a sequence of components for annotating a document — and cache results,
    for quick reloading as needed.

    .. code-block:: pycon

        >>> en_nlp = load_spacy_lang("en_core_web_sm")
        >>> en_nlp = load_spacy_lang("en_core_web_sm", disable=("parser",))
        >>> load_spacy_lang("ar")
        ...
        OSError: [E050] Can't find model 'ar'. It doesn't seem to be a Python package or a valid path to a data directory.

    Note:
        Although spaCy's API specifies some kwargs as ``list[str]``, here we require
        ``tuple[str, ...]`` equivalents. Language pipelines are stored in an LRU cache
        with unique identifiers generated from the hash of the function name and args —
        and lists aren't hashable.

    See Also:
        https://spacy.io/api/top-level#spacy.load
    """
    spacy_lang = spacy.load(name, **kwargs)
    LOGGER.info("loaded '%s' spaCy language pipeline", name)
    return spacy_lang


def process_texts_into_docs(
    texts: Iterable[str],
    *,
    max_len: t.Optional[int] = 1000,
    fallback_lang: t.Optional[str] = "en",
    **kwargs,
) -> Iterable[t.Optional[SpacyDoc]]:
    """
    Args:
        texts
        max_len: Maximum number of chars (code points) in each text to include
            when identifying its language and processing into a spacy document.
        fallback_lang: Fallback language used in place of low-confidence predictions.
        **kwargs: Passed as-is into :func:`load_spacy_lang()` .
    """
    # clean up whitespace, to make it easier on lang detector
    texts = (text.strip().replace("\n", " ") for text in texts)
    # truncate texts, optionally
    if max_len is not None:
        texts = (text[:max_len] for text in texts)
    # identify most probable language (w/ optional fallback) for texts
    texts = list(texts)
    langs = detect_languages(texts)
    text_langs = (
        (text, lang) if lang is not None else (text, fallback_lang)
        for text, lang in zip(texts, langs)
    )
    # join texts to langs, then iterate over lang-groups for processing efficiency
    lang_models = get_lang_to_models()
    for lang, tl_grp in itertools.groupby(text_langs, key=itemgetter(1)):
        if lang in lang_models:
            spacy_lang = load_spacy_lang(lang_models[lang], **kwargs)
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
