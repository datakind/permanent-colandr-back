import functools as ft
import itertools
import logging
import math
import pathlib
import re
import statistics
import typing as t
import urllib.parse
from collections.abc import Iterable

import pandas as pd
import splink
from splink import comparison_level_library as cll
from splink import comparison_library as cl

from .. import utils
from ..nlp import preprocessing


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
        id_col: str = "record_id",
        label_col: t.Optional[str] = None,
        duckdb_conn: str = ":memory:",
        settings: t.Optional[str | pathlib.Path | dict[str, t.Any]] = None,
    ):
        self.df = df
        self.id_col = id_col
        self.label_col = label_col
        self.duckdb_conn = duckdb_conn
        self.db_api = splink.DuckDBAPI(connection=self.duckdb_conn)
        self.settings = settings or self._default_settings()

    @classmethod
    def from_records(
        cls,
        records: Iterable[dict[str, t.Any]],
        *,
        id_col: str = "record_id",
        label_col: t.Optional[str] = None,
        duckdb_conn: str = ":memory:",
        settings: t.Optional[str | pathlib.Path | dict[str, t.Any]] = None,
    ):
        df = cls.preprocess_records(records, id_col=id_col, label_col=label_col)
        return cls(
            df=df,
            id_col=id_col,
            label_col=label_col,
            duckdb_conn=duckdb_conn,
            settings=settings,
        )

    def _default_settings(self) -> splink.SettingsCreator:
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
            unique_id_column_name=self.id_col,
        )

    @ft.cached_property
    def model(self) -> splink.Linker:
        return splink.Linker(self.df, self.settings, self.db_api)  # type: ignore

    @staticmethod
    def preprocess_records(
        records: Iterable[dict[str, t.Any]],
        *,
        id_col: str = "record_id",
        label_col: t.Optional[str] = None,
    ) -> pd.DataFrame:
        LOGGER.info("preprocessing records for deduplication ...")
        df = pd.DataFrame(data=records)
        if id_col not in df.columns:
            raise ValueError(f"records don't include id_col '{id_col}'")
        if label_col and label_col not in df.columns:
            raise ValueError(f"records don't include label_col '{label_col}'")

        preproc_cols = [
            id_col,
            "doi",
            "title",
            "abstract",
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
        if label_col:
            preproc_cols.append(label_col)

        return (
            df.rename(
                columns={
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
                # TODO: figure out if/how we want to separate isbn and issn in raw data
                isbn=lambda df: df["issn"].map(_standardize_isbn, na_action="ignore"),
                issn=lambda df: df["issn"].map(_standardize_issn, na_action="ignore"),
                # TODO: handle abbreviations?
                journal_name=lambda df: df["journal_name"].map(
                    ft.partial(_standardize_journal_name, abbrevs_map=None),
                    na_action="ignore",
                ),
                # derive new columns
                isxn=lambda df: df["issn"].fillna(df["isbn"]),
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
                    "abstract": "string",
                    "author": "string",
                    "author_initials": "string",
                    "isxn": "string",
                    "journal_name": "string",
                    "journal_name_initials": "string",
                    "pub_year": "Int16",
                }
            )
            .reindex(columns=preproc_cols)
        )

    def fit(
        self,
        max_pairs: int = 1_000_000,
        seed: t.Optional[int] = None,
    ) -> "DeduperV2":
        LOGGER.info("training dedupe model on labeled examples ...")
        self._estimate_prob_two_records_match()
        self._estimate_u_parameters(max_pairs, seed)
        self._estimate_m_parameters()
        return self

    def _estimate_prob_two_records_match(self) -> None:
        if self.label_col:
            prob = self._compute_probability_two_records_match_from_label_column()
            self.model._settings_obj._probability_two_random_records_match = prob
        else:
            deterministic_rules = [
                splink.block_on("doi"),
                splink.block_on("title", "author"),
            ]
            self.model.training.estimate_probability_two_random_records_match(
                deterministic_rules,  # type: ignore
                recall=0.7,
            )

    def _estimate_u_parameters(
        self, max_pairs: int, seed: t.Optional[int] = None
    ) -> None:
        self.model.training.estimate_u_using_random_sampling(
            max_pairs=max_pairs,
            seed=seed,  # type: ignore
        )

    def _estimate_m_parameters(self) -> None:
        if self.label_col:
            self.model.training.estimate_m_from_label_column(self.label_col)
        else:
            training_blocking_rules = [
                splink.block_on("isxn", "pub_year"),
                splink.block_on("journal_name_initials"),
                splink.block_on("authors", arrays_to_explode=["authors"]),
            ]
            for blocking_rule in training_blocking_rules:
                _ = self.model.training.estimate_parameters_using_expectation_maximisation(
                    blocking_rule
                )

    def _compute_probability_two_records_match_from_label_column(self) -> float:
        clusters_with_dupes = (
            self.df.groupby(self.label_col).size().gt(1).loc[lambda s: s.eq(True)].index
        )
        # for multi-record clusters, one is non-dupe and the rest are dupes
        num_dupe_records = len(
            self.df.loc[self.df[self.label_col].isin(clusters_with_dupes)]
        ) - len(clusters_with_dupes)
        num_record_pairs = math.comb(len(self.df), 2)
        probability_two_random_records_match = num_dupe_records / num_record_pairs
        LOGGER.info(
            "computed probability two records match = %s from labels in '%s'",
            probability_two_random_records_match,
            self.label_col,
        )
        return probability_two_random_records_match

    def predict(self, threshold: float = 0.5) -> list[tuple[list[int], list[float]]]:
        LOGGER.info("predicting dedupe status for %s records ...", len(self.df))
        df_predict = self.model.inference.predict(threshold_match_probability=threshold)
        df_clustered = self.model.clustering.cluster_pairwise_predictions_at_threshold(
            df_predict, threshold_match_probability=threshold
        )
        id_col_l, id_col_r = f"{self.id_col}_l", f"{self.id_col}_r"
        df_preds = df_predict.as_pandas_dataframe()
        record_pair_match_probs: dict[tuple[int, int], float] = {
            tuple(sorted([rec[id_col_l], rec[id_col_r]])): rec["match_probability"]
            for rec in (
                df_preds.loc[:, [id_col_l, id_col_r, "match_probability"]]
                .sort_values("match_probability", ascending=True)
                .to_dict(orient="records")
            )
        }
        df_clusters = df_clustered.as_pandas_dataframe()
        clusters_record_ids = [
            grp["record_id"].to_list()
            for _, grp in df_clusters.sort_values(by=self.id_col).groupby("cluster_id")
            if len(grp) > 1
        ]
        # mediocre version of dedupe's "confidence score", to match deduper v1's api
        # ref: https://docs.dedupe.io/en/latest/API-documentation.html#dedupe.Dedupe.cluster
        clusters_records_avg_match_probs = (
            self._compute_clusters_record_avg_match_probs(
                clusters_record_ids, record_pair_match_probs
            )
        )
        return list(zip(clusters_record_ids, clusters_records_avg_match_probs))

    def _compute_clusters_record_avg_match_probs(
        self,
        clusters_record_ids: list[list],
        record_pair_match_probs: dict[tuple, float],
    ) -> list[list[float]]:
        clusters_records_avg_match_probs = []
        for cluster_record_ids in clusters_record_ids:
            all_comb_match_probs = {
                comb: record_pair_match_probs[comb]
                for comb in itertools.combinations(cluster_record_ids, 2)
                if comb in record_pair_match_probs
            }
            cluster_record_avg_match_probs = [
                statistics.mean(
                    match_prob
                    for comb, match_prob in all_comb_match_probs.items()
                    if cluster_record_id in comb
                )
                for cluster_record_id in cluster_record_ids
            ]
            clusters_records_avg_match_probs.append(cluster_record_avg_match_probs)
        return clusters_records_avg_match_probs

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
    return preprocessing.remove_brackets(
        _standardize_str(value),
        only="round",
    )


def _compute_authors_initials(authors: list[str]) -> list[str]:
    return ["".join(token[0] for token in author.split()) for author in authors]


def _compute_journal_name_initials(journal_name: str) -> str:
    return "".join(
        token[:2]
        for token in preprocessing.remove_punctuation(journal_name).split()
        if len(token) >= 2
    )


def _standardize_str(text: str) -> str:
    text = preprocessing.remove_punctuation(text, only=[".", "?", "!", ",", ";", "—"])
    text = preprocessing.normalize_quotation_marks(text)
    text = preprocessing.normalize_whitespace(text)
    text = text.lower()
    return text
