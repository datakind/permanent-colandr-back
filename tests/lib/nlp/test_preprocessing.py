import pytest

from colandr.lib.nlp import preprocessing


@pytest.mark.parametrize(
    "text_in, text_out",
    [
        ("These are ´funny single quotes´.", "These are 'funny single quotes'."),
        ("These are ‘fancy single quotes’.", "These are 'fancy single quotes'."),
        ("These are “fancy double quotes”.", 'These are "fancy double quotes".'),
    ],
)
def test_normalize_quotation_marks(text_in, text_out):
    assert preprocessing.normalize_quotation_marks(text_in) == text_out


@pytest.mark.parametrize(
    "text_in, text_out",
    [
        ("Well… That's a long story.", "Well... That's a long story."),
    ],
)
def test_normalize_unicode(text_in, text_out):
    assert preprocessing.normalize_unicode(text_in, form="NFKC") == text_out


@pytest.mark.parametrize(
    "text_in, text_out",
    [
        ("Hello,  world!", "Hello, world!"),
        ("Hello,     world!", "Hello, world!"),
        ("Hello,\tworld!", "Hello, world!"),
        ("Hello,\t\t  world!", "Hello, world!"),
        ("Hello,\n\nworld!", "Hello,\nworld!"),
        ("Hello,\r\nworld!", "Hello,\nworld!"),
        ("Hello\ufeff, world!", "Hello, world!"),
        ("Hello\u200b\u200b, world!", "Hello, world!"),
        ("Hello\ufeff,\n\n\nworld   !  ", "Hello,\nworld !"),
    ],
)
def test_normalize_whitespace(text_in, text_out):
    assert preprocessing.normalize_whitespace(text_in) == text_out


@pytest.mark.parametrize(
    "text_in, fast, text_out",
    [
        (
            "El niño se asustó del pingüino -- qué miedo!",
            True,
            "El nino se asusto del pinguino -- que miedo!",
        ),
        (
            "El niño se asustó del pingüino -- qué miedo!",
            False,
            "El nino se asusto del pinguino -- que miedo!",
        ),
        (
            "Le garçon est très excité pour la forêt.",
            True,
            "Le garcon est tres excite pour la foret.",
        ),
        (
            "Le garçon est très excité pour la forêt.",
            False,
            "Le garcon est tres excite pour la foret.",
        ),
    ],
)
def test_remove_accents(text_in, fast, text_out):
    assert preprocessing.remove_accents(text_in, fast=fast) == text_out


@pytest.mark.parametrize(
    "text_in, only, text_out",
    [
        ("Hello, {name}!", None, "Hello, !"),
        ("Hello, world (DeWilde et al., 2021, p. 42)!", None, "Hello, world !"),
        ("Hello, world (1)!", None, "Hello, world !"),
        ("Hello, world [1]!", None, "Hello, world !"),
        (
            "Hello, world (and whomever it may concern [not that it's any of my business])!",
            None,
            "Hello, world !",
        ),
        (
            "Hello, world (and whomever it may concern (not that it's any of my business))!",
            None,
            "Hello, world (and whomever it may concern )!",
        ),
        (
            "Hello, world (and whomever it may concern [not that it's any of my business])!",
            "square",
            "Hello, world (and whomever it may concern )!",
        ),
        ("Hello, world [1]!", "round", "Hello, world [1]!"),
        ("Hello, world [1]!", ("curly", "round"), "Hello, world [1]!"),
    ],
)
def test_remove_brackets(text_in, only, text_out):
    assert preprocessing.remove_brackets(text_in, only=only) == text_out


@pytest.mark.parametrize(
    "text_in, only, text_out",
    [
        (
            "I can't. No, I won't! It's a matter of \"principle\"; of -- what's the word? -- conscience.",
            None,
            "I can t  No  I won t  It s a matter of  principle   of    what s the word     conscience ",
        ),
        (
            "I can't. No, I won't! It's a matter of \"principle\"; of -- what's the word? -- conscience.",
            ".",
            "I can't  No, I won't! It's a matter of \"principle\"; of -- what's the word? -- conscience ",
        ),
        (
            "I can't. No, I won't! It's a matter of \"principle\"; of -- what's the word? -- conscience.",
            ["-", "'", '"'],
            "I can t. No, I won t! It s a matter of  principle ; of   what s the word?   conscience.",
        ),
    ],
)
def test_remove_punct(text_in, only, text_out):
    assert preprocessing.remove_punctuation(text_in, only=only) == text_out
