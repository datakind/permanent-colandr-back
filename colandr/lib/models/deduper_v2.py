import functools as ft
import json
import logging
import pathlib
import re
import typing as t
import urllib.parse
from collections.abc import Iterable

import pandas as pd
import splink
from textacy import preprocessing

from .. import utils


LOGGER = logging.getLogger(__name__)

RE_DOI_PREFIX = re.compile(r"^https?(://)?dx\.doi\.org/", flags=re.IGNORECASE)
RE_ISSN = re.compile(r"^(\d{4})-?(\d{3}[0-9a-z]{1})($|\b)", flags=re.IGNORECASE)
RE_SPACED_HYPHEN = re.compile(r" *(–|-) *")
RE_SPACE_OR_DOT = re.compile(r"[\s.]+")
RE_SPLIT_AUTHORS = re.compile(
    r"((?:\w{2,}[-– ]+)+(?:\w{1,2}(?:[. ]+|$))+)", flags=re.IGNORECASE
)


class DeduperV2:
    def __init__(
        self,
        *,
        settings_fpath: t.Optional[str | pathlib.Path] = None,
        in_memory: bool = False,
    ):
        self.settings_fpath = settings_fpath
        self.in_memory = in_memory

    def preprocess_records(self, records: Iterable[dict[str, t.Any]]) -> pd.DataFrame:
        # TODO: handle abbreviations?
        # _stdize_jname_prtl = ft.partial(
        #     _standardize_journal_name, abbrevs_map=abbrevs_map
        # )
        LOGGER.info("preprocessing data ...")
        return (
            pd.DataFrame(data=records)
            .rename(
                columns={
                    "volume": "journal_volume",
                    "issue_number": "journal_number",
                }
            )
            .assign(
                # standardize existing columns
                doi=lambda df: df["doi"].map(_standardize_doi, na_action="ignore"),
                isbn=lambda df: df["isbn"].map(_standardize_isbn, na_action="ignore"),
                title=lambda df: df["title"].map(
                    _standardize_title, na_action="ignore"
                ),
                abstract=lambda df: df["abstract"].map(
                    _standardize_abstract, na_action="ignore"
                ),
                authors=lambda df: df["author"].map(
                    _standardize_authors, na_action="ignore"
                ),
                journal_name=lambda df: df["journal_name"].map(
                    _standardize_journal_name, na_action="ignore"
                ),
                # derive new columns
                author=lambda df: df["authors"].map(" ".join, na_action="ignore"),
                pub_dt=lambda df: pd.to_datetime(
                    df["pub_year"], format="%Y", errors="coerce"
                ),
                authors_initials=lambda df: df["authors"].map(
                    _compute_authors_initials, na_action="ignore"
                ),
                journal_name_initials=lambda df: df["journal_name"].map(
                    _compute_journal_name_initials, na_action="ignore"
                ),
                title_excerpt=lambda df: df["title"].str.slice(stop=25),
                abstract_excerpt=lambda df: df["title"].str.slice(stop=50),
            )
        )


def _standardize_doi(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("http://") or value.startswith("https://"):
        value = urllib.parse.unquote(value)
        value = RE_DOI_PREFIX.sub("", value)
    return value


def _standardize_isbn(value: str) -> str:
    return sorted(
        preprocessing.remove.brackets(_standardize_str(value), only="round").split()
    )[0]


def _standardize_title(value: str) -> str:
    return _standardize_str(value)


def _standardize_authors(value: list[str]) -> t.Optional[list[str]]:
    value = sorted(
        _standardize_str(RE_SPACED_HYPHEN.sub(r"\1", author)) for author in value
    )
    value = [author for author in value if author and author != "anonymous"]
    return value if value else None


def _standardize_abstract(value: str, *, maxlen: int = 500) -> str:
    return _standardize_str(value[:maxlen])


def _standardize_journal_name(
    value: str, *, abbrevs_map: t.Optional[dict[str, str]] = None
) -> str:
    if abbrevs_map:
        value = " ".join(
            abbrevs_map.get(tok, tok) for tok in RE_SPACE_OR_DOT.split(value.lower())
        )
    return preprocessing.remove.brackets(
        _standardize_str(value),
        only="round",
    )


def _compute_journal_name_initials(journal_name: str) -> str:
    return "".join(
        token[:2]
        for token in preprocessing.remove.punctuation(journal_name).split()
        if len(token) >= 2
    )


def _compute_authors_initials(authors: list[str]) -> list[str]:
    return ["".join(token[0] for token in author.split()) for author in authors]


_standardize_str = preprocessing.make_pipeline(
    ft.partial(preprocessing.remove.punctuation, only=[".", "?", "!", ",", ";", "—"]),
    preprocessing.normalize.quotation_marks,
    preprocessing.normalize.whitespace,
    str.lower,
)
