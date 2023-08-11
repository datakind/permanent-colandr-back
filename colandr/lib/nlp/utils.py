import collections
import logging

import spacy


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
