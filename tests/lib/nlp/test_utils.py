import pytest
import textacy
from spacy.tokens import Doc

from colandr.lib.nlp import utils


@pytest.mark.parametrize(
    ["texts", "max_len", "min_prob", "fallback_lang"],
    [
        (
            [
                "This is a short -- but not too short -- example English sentence.",
                "And this is another short example English sentence.",
                "Esta es una frase corta de ejemplo en español.",
            ],
            1000,
            0.5,
            None,
        ),
        (
            [
                "This is a short -- but not too short -- example English sentence.",
                "And this is another short example English sentence.",
                "Esta es una frase corta de ejemplo en español.",
            ],
            100,
            0.75,
            "en",
        ),
        (
            [
                "This is a short -- but not too short -- example English sentence.",
                "And this is another short example English sentence.",
                "Esta es una frase corta de ejemplo en español.",
            ],
            None,
            None,
            None,
        ),
    ],
)
def test_process_texts_into_docs(texts, max_len, min_prob, fallback_lang):
    docs = list(
        utils.process_texts_into_docs(
            texts,
            max_len=max_len,
            min_prob=min_prob,
            fallback_lang=fallback_lang,
            exclude=("parser", "ner"),
        )
    )
    assert len(docs) == len(texts)
    assert all(isinstance(doc, Doc) or doc is None for doc in docs)
    assert any(isinstance(doc, Doc) for doc in docs)
    # sanity-check vector value for first text only
    spacy_lang = textacy.load_spacy_lang(
        utils.get_lang_to_models()["en"][0], exclude=("parser", "ner")
    )
    assert spacy_lang(texts[0]).to_bytes() == docs[0].to_bytes()
