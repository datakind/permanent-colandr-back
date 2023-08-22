import pytest

from colandr.lib.nlp import utils


@pytest.mark.parametrize(
    ["texts", "max_len", "min_prob", "fallback_lang"],
    [
        (
            [
                "This is an example English sentence.",
                "And this is another example English sentence.",
                "Esta es una frase de ejemplo en español.",
            ],
            1000,
            0.5,
            "en",
        ),
    ],
)
def test_get_text_content_vectors(texts, max_len, min_prob, fallback_lang):
    cvs = list(
        utils.get_text_content_vectors(
            texts,
            max_len=max_len,
            min_prob=min_prob,
            fallback_lang=fallback_lang,
            disable=("tagger", "parser", "ner"),
        )
    )
    assert len(cvs) == len(texts)
    assert all(isinstance(cv, list) or cv is None for cv in cvs)
    assert any(isinstance(cv, list) for cv in cvs)
