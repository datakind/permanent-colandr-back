import collections
import itertools
import logging
from collections.abc import Iterable
from operator import itemgetter
from typing import Any, Optional

import spacy
import textacy
from spacy.tokens import Doc


LOGGER = logging.getLogger(__name__)


def get_lang_to_models() -> dict[str, list[str]]:
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
    max_len: Optional[int] = 1000,
    min_prob: Optional[float] = 0.5,
    fallback_lang: Optional[str] = "en",
    **kwargs,
) -> Iterable[Optional[Doc]]:
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
    # clean up whitespace, since lang identifier model is picky
    texts = (text.strip().replace("\n", " ") for text in texts)
    # truncate texts, optionally
    if max_len is not None:
        texts = (text[:max_len] for text in texts)
    # identify most probable language (w/ optional fallback) for texts
    if min_prob is not None:
        text_lang_probs = (
            (text, textacy.identify_lang(text, with_probs=True)) for text in texts
        )
        text_langs = (
            (text, lang) if prob >= min_prob else (text, fallback_lang)
            for text, (lang, prob) in text_lang_probs
        )
    else:
        text_langs = (
            (text, textacy.identify_lang(text, with_probs=False)) for text in texts
        )
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


def get_text_content_vectors(
    texts: Iterable[str],
    *,
    max_len: Optional[int] = 1000,
    min_prob: Optional[float] = 0.5,
    fallback_lang: Optional[str] = "en",
    **kwargs,
) -> Iterable[Optional[list[float]]]:
    # clean up whitespace, since lang identifier model is picky
    texts = (text.strip().replace("\n", " ") for text in texts)
    # optionally truncate texts
    texts = [text[:max_len] for text in texts] if max_len is not None else list(texts)
    # identify most probable language (w/ optional fallback) for texts
    if min_prob is not None:
        lang_probs = (textacy.identify_lang(text, with_probs=True) for text in texts)
        langs = (
            lang if prob >= min_prob else fallback_lang for lang, prob in lang_probs
        )
    else:
        langs = (textacy.identify_lang(text, with_probs=False) for text in texts)
    # join texts to langs, then iterate over lang-groups for processing efficiency
    lang_models = get_lang_to_models()
    text_langs = zip(texts, langs, strict=True)
    for lang, tl_grp in itertools.groupby(text_langs, key=itemgetter(1)):
        if lang in lang_models:
            spacy_lang = textacy.load_spacy_lang(lang_models[lang][0], **kwargs)
            spacy_docs = spacy_lang.pipe((text for text, _ in tl_grp), n_process=1)
            for spacy_doc in spacy_docs:
                yield spacy_doc.vector.tolist()
        else:
            LOGGER.info(
                "unable to load spacy model for lang='%s'; content vectors are set to null ...",
                lang,
            )
            for _ in tl_grp:
                yield None


def make_spacy_doc_if_possible(
    text: str, lang_models: dict[str, list[str]], **kwargs: Any
) -> Optional[Doc]:
    text = text.replace("\n", " ")
    lang, prob = textacy.identify_lang(text, with_probs=True)
    if prob < 0.5 and lang != "en":
        LOGGER.warning(
            "identified lang=%s with probability=%s; falling back to 'en' default",
            lang,
            prob,
        )
        lang = "en"
    if lang not in lang_models:
        LOGGER.info(
            "unable to load spacy model for text='%s' with lang='%s'", text[:50], lang
        )
        return None

    try:
        # TODO: find better way of handling multi-model langs
        spacy_lang = textacy.load_spacy_lang(lang_models[lang][0], **kwargs)
        return spacy_lang(text)
    except Exception:
        LOGGER.exception(
            "unable to make spacy doc for text='%s' with lang='%s'", text, lang
        )
        return None
