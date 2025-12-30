import pytest
from spacy.language import Language
from spacy.tokens import Doc

from colandr.lib.nlp import utils


@pytest.mark.parametrize(
    ["text", "exp_lang"],
    [
        (
            "This is a short text. Which language is it in? Hopefully the model can identify it.",
            "en",
        ),
        (
            "Voici un court texte. Dans quelle langue est-il écrit ? Espérons que le modèle pourra l'identifier.",
            "fr",
        ),
        (
            "Esta es un texto corto. ¿En qué idioma está? Esperemos que este modelo pueda identificarlo.",
            "es",
        ),
        ("这是一段简短的文字。它是用哪种语言写的？希望模型能够识别出来。", "zh"),
        (
            "これは短い文章です。何語で書かれているでしょうか？モデルが識別できることを願っています。",
            "ja",
        ),
        (
            "Dies ist ein kurzer Text. In welcher Sprache ist er verfasst? Hoffentlich kann das Modell die Sprache erkennen.",
            "de",
        ),
        (
            "이것은 짧은 글입니다. 이 글은 어떤 언어로 쓰여 있을까요? 모델이 언어를 식별할 수 있기를 바랍니다.",
            "ko",
        ),
        (
            "Detta är en kort text. Vilket språk är den på? Förhoppningsvis kan modellen identifiera den.",
            "sv",
        ),
        (
            "Это короткий текст. На каком языке он написан? Надеюсь, модель сможет это определить.",
            "ru",
        ),
        # yes, this is None, bc the model isn't confident enough b/w Spanish and Portuguese
        (
            "Este é um texto curto. Em que língua está? Espero que o modelo o consiga identificar.",
            None,
        ),
    ],
)
def test_detect_language(text, exp_lang):
    obs_lang = utils.detect_language(text)
    assert obs_lang == exp_lang


@pytest.mark.parametrize(
    ["texts", "exp_langs"],
    [
        (
            [
                "This is a short text. Which language is it in? Hopefully the model can identify it.",
                "Voici un court texte. Dans quelle langue est-il écrit ? Espérons que le modèle pourra l'identifier.",
                "Esta es un texto corto. ¿En qué idioma está? Esperemos que este modelo pueda identificarlo.",
                "这是一段简短的文字。它是用哪种语言写的？希望模型能够识别出来。",
                "これは短い文章です。何語で書かれているでしょうか？モデルが識別できることを願っています。",
                "Dies ist ein kurzer Text. In welcher Sprache ist er verfasst? Hoffentlich kann das Modell die Sprache erkennen.",
                "이것은 짧은 글입니다. 이 글은 어떤 언어로 쓰여 있을까요? 모델이 언어를 식별할 수 있기를 바랍니다.",
                "Detta är en kort text. Vilket språk är den på? Förhoppningsvis kan modellen identifiera den.",
                "Это короткий текст. На каком языке он написан? Надеюсь, модель сможет это определить.",
                "Este é um texto curto. Em que língua está? Espero que o modelo o consiga identificar.",
            ],
            ["en", "fr", "es", "zh", "ja", "de", "ko", "sv", "ru", None],
        ),
    ],
)
def test_detect_languages(texts, exp_langs):
    obs_langs = utils.detect_languages(texts)
    assert obs_langs == exp_langs


@pytest.mark.parametrize(
    ["text", "max_len", "fallback_lang"],
    [
        (
            "This is a short -- but not too short -- example English sentence.",
            1000,
            None,
        ),
        ("And this is another short example English sentence.", 100, "en"),
        ("Esta es una frase corta de ejemplo en español.", None, None),
    ],
)
def test_process_text_into_doc(text, max_len, fallback_lang, app):
    doc = utils.process_text_into_doc(
        text,
        max_len=max_len,
        fallback_lang=fallback_lang,
        exclude=("parser", "ner"),
    )
    assert isinstance(doc, Doc) or doc is None
    if doc.lang_ == "en":
        spacy_lang = utils.load_spacy_lang(
            utils.get_lang_to_models()["en"], exclude=("parser", "ner")
        )
        assert isinstance(spacy_lang, Language) and isinstance(doc, Doc)  # type guards
        assert spacy_lang(text).to_bytes() == doc.to_bytes()


@pytest.mark.parametrize(
    ["texts", "max_len", "fallback_lang"],
    [
        (
            [
                "This is a short -- but not too short -- example English sentence.",
                "And this is another short example English sentence.",
                "Esta es una frase corta de ejemplo en español.",
            ],
            1000,
            None,
        ),
        (
            [
                "This is a short -- but not too short -- example English sentence.",
                "And this is another short example English sentence.",
                "Esta es una frase corta de ejemplo en español.",
            ],
            100,
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
        ),
    ],
)
def test_process_texts_into_docs(texts, max_len, fallback_lang, app):
    docs = list(
        utils.process_texts_into_docs(
            texts,
            max_len=max_len,
            fallback_lang=fallback_lang,
            exclude=("parser", "ner"),
        )
    )
    assert len(docs) == len(texts)
    assert all(isinstance(doc, Doc) or doc is None for doc in docs)
    assert any(isinstance(doc, Doc) for doc in docs)
    # sanity-check vector value for first text only
    spacy_lang = utils.load_spacy_lang(
        utils.get_lang_to_models()["en"], exclude=("parser", "ner")
    )
    doc = docs[0]
    assert isinstance(spacy_lang, Language) and isinstance(doc, Doc)  # type guards
    assert spacy_lang(texts[0]).to_bytes() == doc.to_bytes()
