import functools as ft
import logging
import pathlib
import re
import typing as t
import urllib.parse
from collections.abc import Iterable

import pandas as pd
import splink
from splink import comparison_level_library as cll
from splink import comparison_library as cl
from textacy import preprocessing

from .. import utils


LOGGER = logging.getLogger(__name__)

RE_DOI_PREFIX = re.compile(r"^https?(://)?dx\.doi\.org/", flags=re.IGNORECASE)
RE_ISSN = re.compile(r"^(\d{4})-?(\d{3}[0-9a-z]{1})($|\b)", flags=re.IGNORECASE)
RE_ISBN = re.compile(r"^(\d{10}|\d{13})($|\b)", flags=re.IGNORECASE)
RE_SPACED_HYPHEN = re.compile(r" *(–|-) *")
RE_SPACE_OR_DOT = re.compile(r"[\s.]+")


class DeduperV2:
    def __init__(
        self,
        *,
        df: pd.DataFrame,
        duckdb_conn: str = ":memory:",
        settings: t.Optional[str | pathlib.Path | dict[str, t.Any]] = None,
    ):
        self.df = df
        self.duckdb_conn = duckdb_conn
        self.db_api = splink.DuckDBAPI(connection=self.duckdb_conn)
        self.settings = settings or self._init_settings()

    def _init_settings(self) -> splink.SettingsCreator:
        return splink.SettingsCreator(
            link_type="dedupe_only",
            blocking_rules_to_generate_predictions=[
                # tier 1
                splink.block_on("doi"),
                splink.block_on("title"),
                splink.block_on("author"),
                # TODO: leverage duckdb funcs to avoid derivative columns?
                # block_on("array_to_string(authors, ' ')"),
                # block_on("list_aggregate(authors, 'string_agg', '|')"),
                # block_on("concat_ws('|', authors)"),
                splink.block_on(
                    "substring(title, 1, 25)", "authors", arrays_to_explode=["authors"]
                ),
                # tier 2
                splink.block_on("pub_year", "substring(title, 1, 25)"),
                splink.block_on("pub_year", "authors", arrays_to_explode=["authors"]),
                splink.block_on(
                    "pub_year",
                    "journal_name",
                    "authors_initials",
                    arrays_to_explode=["authors_initials"],
                ),
                splink.block_on("isxn", "substring(title, 1, 25)"),
                splink.block_on("isxn", "authors", arrays_to_explode=["authors"]),
                # tier 3
                splink.block_on(
                    "substring(title, 1, 25)",
                    "authors_initials",
                    "journal_name_initials",
                    arrays_to_explode=["authors_initials"],
                ),
                splink.block_on(
                    "substring(abstract, 1, 50)",
                    "authors_initials",
                    arrays_to_explode=["authors_initials"],
                ),
                splink.block_on("pub_year", "substring(reverse(title), 1, 50)"),
            ],
            comparisons=[
                cl.ExactMatch("doi"),
                cl.CustomComparison(
                    output_column_name="content",
                    comparison_description="exact and fuzzy content comparisons",
                    comparison_levels=[
                        cll.And(
                            cll.NullLevel("title"),
                            cll.NullLevel("abstract"),
                        ).configure(is_null_level=True),
                        cll.Or(
                            cll.ExactMatchLevel("title"),
                            cll.ExactMatchLevel("abstract"),
                        ),
                        cll.Or(
                            cll.LevenshteinLevel("title", 10),
                            cll.LevenshteinLevel("abstract", 25),
                        ),
                        cll.ElseLevel(),
                    ],
                ),
                cl.CustomComparison(
                    output_column_name="authorship",
                    comparison_description="exact and fuzzy authorship comparisons",
                    comparison_levels=[
                        cll.NullLevel("authors"),
                        cll.ExactMatchLevel("author", term_frequency_adjustments=True),
                        cll.CustomLevel(
                            "len(list_intersect(authors_l, authors_r)) / list_unique(list_concat(authors_l, authors_r)) >= 0.5",
                            "Jaccard similarity of authors >= 0.5",
                            base_dialect_str="duckdb",
                        ),
                        cll.CustomLevel(
                            "len(list_intersect(authors_initials_l, authors_initials_r)) / list_unique(list_concat(authors_initials_l, authors_initials_r)) >= 0.5",
                            "Jaccard similarity of authors initials >= 0.5",
                            base_dialect_str="duckdb",
                        ),
                        cll.ArrayIntersectLevel("authors", 1),
                        cll.ArrayIntersectLevel("authors_initials", 1),
                        # alternative comparisons
                        # cll.PairwiseStringDistanceFunctionLevel(
                        #     "authors", "levenshtein", 3
                        # ),
                        # cll.ArraySubsetLevel("authors", empty_is_subset=False),
                        # cll.LevenshteinLevel("author", 10),
                        cll.ElseLevel(),
                    ],
                ),
                cl.CustomComparison(
                    output_column_name="venue",
                    comparison_description="exact and fuzzy venue comparisons",
                    comparison_levels=[
                        cll.And(
                            cll.NullLevel("journal_name"),
                            cll.NullLevel("isxn"),
                        ).configure(is_null_level=True),
                        cll.Or(
                            cll.ExactMatchLevel(
                                "journal_name", term_frequency_adjustments=True
                            ),
                            cll.ExactMatchLevel(
                                "isxn", term_frequency_adjustments=True
                            ),
                        ),
                        cll.Or(
                            cll.LevenshteinLevel("journal_name", 3),
                            cll.ExactMatchLevel(
                                "journal_name_initials", term_frequency_adjustments=True
                            ),
                        ),
                        cll.Or(
                            cll.LevenshteinLevel("journal_name", 10),
                            cll.JaroLevel("journal_name_initials", 0.9),
                        ),
                        cll.ElseLevel(),
                    ],
                ),
                cl.CustomComparison(
                    output_column_name="time",
                    comparison_description="exact and fuzzy time comparisons",
                    comparison_levels=[
                        cll.And(
                            cll.NullLevel("journal_volume"),
                            cll.NullLevel("journal_number"),
                            cll.NullLevel("pub_year"),
                        ).configure(is_null_level=True),
                        cll.And(
                            cll.ExactMatchLevel(
                                "journal_volume", term_frequency_adjustments=True
                            ),
                            cll.ExactMatchLevel(
                                "journal_number", term_frequency_adjustments=True
                            ),
                            cll.ExactMatchLevel(
                                "pub_year", term_frequency_adjustments=True
                            ),
                        ),
                        cll.ExactMatchLevel(
                            "pub_year", term_frequency_adjustments=True
                        ),
                        cll.AbsoluteDifferenceLevel("pub_year", 1),
                        # alternative comparison
                        # cll.AbsoluteDateDifferenceLevel(
                        #     "pub_dt", input_is_string=False, threshold=1, metric="year"
                        # ),
                        cll.ElseLevel(),
                    ],
                ),
            ],
            retain_matching_columns=True,
            retain_intermediate_calculation_columns=True,
            unique_id_column_name="record_id",
        )

    @ft.cached_property
    def model(self) -> splink.Linker:
        return splink.Linker(self.df, self.settings, self.db_api)  # type: ignore

    @staticmethod
    def preprocess_records(records: Iterable[dict[str, t.Any]]) -> pd.DataFrame:
        LOGGER.info("preprocessing records for deduplication ...")
        return (
            pd.DataFrame(data=records)
            .rename(
                columns={
                    # TODO: rename id col to "record_id" ?
                    "volume": "journal_volume",
                    "issue_number": "journal_number",
                }
            )
            .assign(
                # standardize existing columns
                doi=lambda df: df["doi"].map(_standardize_doi, na_action="ignore"),
                title=lambda df: df["title"].map(
                    _standardize_title, na_action="ignore"
                ),
                abstract=lambda df: df["abstract"].map(
                    ft.partial(_standardize_abstract, maxlen=500), na_action="ignore"
                ),
                authors=lambda df: df["author"].map(
                    _standardize_authors, na_action="ignore"
                ),
                issn=lambda df: df["isbn"].map(_standardize_issn, na_action="ignore"),
                isbn=lambda df: df["isbn"].map(_standardize_isbn, na_action="ignore"),
                # TODO: handle abbreviations?
                journal_name=lambda df: df["journal_name"].map(
                    ft.partial(_standardize_journal_name, abbrevs_map=None),
                    na_action="ignore",
                ),
                # derive new columns
                isxn=lambda df: df["issn"].fillna(df["isbn"]),
                # title_excerpt=lambda df: df["title"].str.slice(stop=25),
                # abstract_excerpt=lambda df: df["title"].str.slice(stop=50),
                authors_initials=lambda df: df["authors"].map(
                    _compute_authors_initials, na_action="ignore"
                ),
                author=lambda df: df["authors"].map(" ".join, na_action="ignore"),
                author_initials=lambda df: df["authors_initials"].map(
                    " ".join, na_action="ignore"
                ),
                journal_name_initials=lambda df: df["journal_name"].map(
                    _compute_journal_name_initials, na_action="ignore"
                ),
            )
            .drop(columns=["issn", "isbn"])
            .astype(
                {
                    "doi": "string",
                    "title": "string",
                    # "title_excerpt":"string",
                    "abstract": "string",
                    # "abstract_excerpt": "string",
                    "author": "string",
                    "author_initials": "string",
                    "isxn": "string",
                    "journal_name": "string",
                    "journal_name_initials": "string",
                    "pub_year": "Int16",
                }
            )
            .reindex(
                columns=[
                    "doi",
                    "title",
                    # "title_excerpt",
                    "abstract",
                    # "abstract_excerpt",
                    "authors",
                    "authors_initials",
                    "author",
                    "author_initials",
                    "isxn",
                    "journal_name",
                    "journal_name_initials",
                    "journal_volume",
                    "journal_number",
                    "pub_year",
                ]
            )
        )

    def fit(
        self,
        max_pairs: int = 1_000_000,
        label_col: t.Optional[str] = None,
        seed: t.Optional[int] = None,
    ) -> "DeduperV2":
        LOGGER.info("training dedupe model on labeled examples ...")
        self.model.training.estimate_u_using_random_sampling(
            max_pairs=max_pairs,
            seed=seed,  # type: ignore
        )
        if label_col:
            self.model.training.estimate_m_from_label_column(label_col)
        return self

    def predict(
        self, threshold: float = 0.5
    ):  # -> list[tuple[tuple, tuple[float, ...]]]:
        df_preds = self.model.inference.predict(threshold_match_probability=threshold)
        df_clusters = self.model.clustering.cluster_pairwise_predictions_at_threshold(
            df_preds, threshold_match_probability=threshold
        )
        # TODO: finish this

    def save(self, dir_path: str | pathlib.Path) -> None:
        dir_path = utils.to_path(dir_path).resolve()
        if not dir_path.exists():
            dir_path.mkdir()
        file_path = str(dir_path / "dedupe-splink-model.json")
        self.model.misc.save_model_to_json(file_path, overwrite=True)
        LOGGER.info("model settings saved to %s", file_path)


def _standardize_doi(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("http://") or value.startswith("https://"):
        value = urllib.parse.unquote(value)
        value = RE_DOI_PREFIX.sub("", value)
    return value


def _standardize_isbn(value: str) -> str | None:
    if match := RE_ISBN.match(value.replace("-", "")):
        return match.group()
    else:
        return None


def _standardize_issn(value: str) -> str | None:
    if match := RE_ISSN.match(value):
        return f"{match.group(1)}-{match.group(2)}"
    else:
        return None


def _standardize_title(value: str) -> str:
    return _standardize_str(value)


def _standardize_abstract(value: str, *, maxlen: int = 500) -> str:
    return _standardize_str(value[:maxlen])


def _standardize_authors(value: list[str]) -> list[str] | None:
    value = sorted(
        _standardize_str(RE_SPACED_HYPHEN.sub(r"\1", author)) for author in value
    )
    value = [author for author in value if author and author != "anonymous"]
    return value if value else None


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


def _compute_authors_initials(authors: list[str]) -> list[str]:
    return ["".join(token[0] for token in author.split()) for author in authors]


def _compute_journal_name_initials(journal_name: str) -> str:
    return "".join(
        token[:2]
        for token in preprocessing.remove.punctuation(journal_name).split()
        if len(token) >= 2
    )


_standardize_str = preprocessing.make_pipeline(
    ft.partial(preprocessing.remove.punctuation, only=[".", "?", "!", ",", ";", "—"]),
    preprocessing.normalize.quotation_marks,
    preprocessing.normalize.whitespace,
    str.lower,
)
