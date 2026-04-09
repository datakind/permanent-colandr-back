import functools
import re
import sys
import typing as t
import unicodedata
from collections.abc import Collection, Iterable


RE_BRACKETS_CURLY = re.compile(r"\{[^{}]*?\}")
RE_BRACKETS_ROUND = re.compile(r"\([^()]*?\)")
RE_BRACKETS_SQUARE = re.compile(r"\[[^\[\]]*?\]")

RE_LINEBREAK = re.compile(r"(\r\n|[\n\v])+")
RE_NONBREAKING_SPACE = re.compile(r"[^\S\n\v]+")
RE_ZWSP = re.compile(r"[\u200B\u2060\uFEFF]+")


def normalize_quotation_marks(text: str) -> str:
    """
    Normalize all "fancy" single- and double-quotation marks in ``text``
    to just the basic ASCII equivalents. Note that this will also normalize fancy
    apostrophes, which are typically represented as single quotation marks.
    """
    quote_translation_table = _get_quote_translation_table()
    return text.translate(quote_translation_table)


def normalize_unicode(
    text: str, *, form: t.Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFC"
) -> str:
    """
    Normalize unicode characters in ``text`` into canonical forms.

    Args:
        text
        form: Form of normalization applied to unicode characters.
            For example, an "e" with accute accent "´" can be written as "e´"
            (canonical decomposition, "NFD") or "é" (canonical composition, "NFC").
            Unicode can be normalized to NFC form without any change in meaning,
            so it's usually a safe bet. If "NFKC", additional normalizations are applied
            that can change characters' meanings, e.g. ellipsis characters are replaced
            with three periods.
    """
    return unicodedata.normalize(form, text)


def normalize_whitespace(text: str) -> str:
    """
    Replace all contiguous zero-width spaces with an empty string, line-breaking spaces
    with a single newline, and non-breaking spaces with a single space, then
    strip any leading/trailing whitespace.
    """
    text = RE_ZWSP.sub("", text)
    text = RE_LINEBREAK.sub(r"\n", text)
    text = RE_NONBREAKING_SPACE.sub(" ", text)
    return text.strip()


def remove_accents(text: str, *, fast: bool = False) -> str:
    """
    Remove accents from any accented unicode characters in ``text``, either by
    replacing them with ASCII equivalents or removing them entirely.

    Args:
        text
        fast: If False, accents are removed from any unicode symbol
            with a direct ASCII equivalent; if True, accented chars
            for all unicode symbols are removed, regardless.

            .. note:: ``fast=True`` can be significantly faster than ``fast=False``,
               but its transformation of ``text`` is less "safe" and more likely
               to result in changes of meaning, spelling errors, etc.
    """
    if fast is False:
        return "".join(
            char
            for char in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(char)
        )
    else:
        return (
            unicodedata.normalize("NFKD", text)
            .encode("ascii", errors="ignore")
            .decode("ascii")
        )


def remove_brackets(
    text: str,
    *,
    only: t.Optional[str | Collection[str]] = None,
) -> str:
    """
    Remove text within curly {}, square [], and/or round () brackets, as well as
    the brackets themselves.

    Args:
        text
        only: Remove only those bracketed contents as specified here: "curly", "square",
            and/or "round". For example, ``"square"`` removes only those contents found
            between square brackets, while ``["round", "square"]`` removes those contents
            found between square or round brackets, but not curly.

    Note:
        This function relies on regular expressions, applied sequentially for curly,
        square, then round brackets; as such, it doesn't handle nested brackets of the
        same type and may behave unexpectedly on text with "wild" use of brackets.
        It should be fine removing structured bracketed contents, as is often used,
        for instance, to denote in-text citations.
    """
    only = _to_set(only) if only is not None else None
    if only is None or "curly" in only:
        text = RE_BRACKETS_CURLY.sub("", text)
    if only is None or "square" in only:
        text = RE_BRACKETS_SQUARE.sub("", text)
    if only is None or "round" in only:
        text = RE_BRACKETS_ROUND.sub("", text)
    return text


def remove_punctuation(
    text: str,
    *,
    only: t.Optional[str | Collection[str]] = None,
) -> str:
    """
    Remove punctuation from ``text`` by replacing all instances of punctuation
    (or a subset thereof specified by ``only``) with whitespace.

    Args:
        text
        only: Remove only those punctuation marks specified here. For example,
            ``"."`` removes only periods, while ``[",", ";", ":"]`` removes commas,
            semicolons, and colons; if None, all unicode punctuation marks are removed.

    Note:
        When ``only=None``, Python's built-in :meth:`str.translate()` is
        used to remove punctuation; otherwise, a regular expression is used.
        The former's performance can be up to an order of magnitude faster.
    """
    only = _to_set(only) if only is not None else None
    if only is not None:
        return re.sub("[{}]+".format(re.escape("".join(only))), " ", text)
    else:
        punct_translation_table = _get_punct_translation_table()
        return text.translate(punct_translation_table)


def _to_set(val: t.Any) -> set:
    """Cast ``val`` into a set."""
    if isinstance(val, set):
        return val
    elif isinstance(val, Iterable) and not isinstance(val, (str, bytes)):
        return set(val)
    else:
        return {val}


@functools.cache
def _get_punct_translation_table() -> dict[int, str]:
    return dict.fromkeys(
        (
            i
            for i in range(sys.maxunicode)
            if unicodedata.category(chr(i)).startswith("P")
        ),
        " ",
    )


@functools.cache
def _get_quote_translation_table() -> dict[int, int]:
    return {
        ord(x): ord(y)
        for x, y in [
            ("ʼ", "'"),
            ("‘", "'"),
            ("’", "'"),
            ("´", "'"),
            ("`", "'"),
            ("“", '"'),
            ("”", '"'),
        ]
    }
