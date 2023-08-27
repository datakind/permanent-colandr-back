import collections
import itertools
import logging
from collections.abc import Iterable
from operator import itemgetter
from typing import Optional

import spacy
import textacy
from spacy.tokens import Doc


LOGGER = logging.getLogger(__name__)


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
