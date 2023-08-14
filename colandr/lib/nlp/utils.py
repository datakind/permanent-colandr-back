import collections
import logging
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


def make_spacy_doc_if_possible(
    text: str, lang_models: dict[str, list[str]], **kwargs: Any
) -> Optional[Doc]:
    lang = textacy.identify_lang(text)
    if lang not in lang_models:
        LOGGER.warning(
            "unable to load spacy model for text='%s' with lang='%s'", text[:50], lang
        )
        return None

    try:
        spacy_lang = textacy.load_spacy_lang(lang_models[lang][0], **kwargs)
        return spacy_lang(text)
    except Exception:
        LOGGER.exception(
            "unable to make spacy doc for text='%s' with lang='%s'", text, lang
        )
        return None
