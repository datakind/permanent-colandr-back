import functools
import logging
import pathlib
import urllib.parse
from collections.abc import Iterable
from typing import Any, Optional

import dedupe

from .. import utils


LOGGER = logging.getLogger(__name__)

SETTINGS_FNAME = "deduper_settings"
TRAINING_FNAME = "deduper_training.json"
VARIABLES: list[dict[str, Any]] = [
    {"field": "type_of_reference", "type": "ShortString"},
    {"field": "title", "type": "String", "variable name": "title"},
    {"field": "pub_year", "type": "Exact", "variable name": "pub_year"},
    {"field": "authors", "type": "Set", "has missing": True},
    {"field": "authors_joined", "type": "String", "has missing": True},
    {"field": "abstract", "type": "Text", "has missing": True},
    {"field": "doi", "type": "ShortString", "has missing": True},
    {"type": "Interaction", "interaction variables": ["title", "pub_year"]},
]


class Deduper:
    def __init__(
        self,
        *,
        settings_fpath: Optional[str | pathlib.Path] = None,
        num_cores: int = 1,
        in_memory: bool = False,
    ):
        self.settings_fpath = settings_fpath
        self.num_cores = num_cores
        self.in_memory = in_memory

    @classmethod
    def load(
        cls, dir_path: str | pathlib.Path, num_cores: int = 1, in_memory: bool = False
    ):
        settings_fpath = utils.to_path(dir_path) / SETTINGS_FNAME
        return cls(
            settings_fpath=settings_fpath, num_cores=num_cores, in_memory=in_memory
        )

    @functools.cached_property
    def model(self) -> dedupe.Dedupe | dedupe.StaticDedupe:
        if self.settings_fpath is None:
            _model = dedupe.Dedupe(
                VARIABLES,  # type: ignore
                num_cores=self.num_cores,
                in_memory=self.in_memory,
            )
        else:
            with open(self.settings_fpath, mode="rb") as f:
                _model = dedupe.StaticDedupe(
                    f, num_cores=self.num_cores, in_memory=self.in_memory
                )
        return _model

    def preprocess_data(
        self,
        data: Iterable[dict[str, Any]],
        id_key: str,
    ) -> dict[Any, dict[str, Any]]:
        fields = [pv.field for pv in self.model.data_model.primary_variables]
        LOGGER.info("preprocessing data with fields %s ...", fields)
        return {record.pop(id_key): self._preprocess_record(record) for record in data}

    def _preprocess_record(self, record: dict[str, Any]) -> dict[str, Any]:
        # base fields
        record = {
            "type_of_reference": (
                record["type_of_reference"].strip().lower()
                if record.get("type_of_reference")
                else None
            ),
            "title": (
                record["title"].strip().strip(".").lower()
                if record.get("title")
                else None
            ),
            "pub_year": record.get("pub_year", None),
            "authors": (
                tuple(sorted(author.strip().lower() for author in record["authors"]))
                if record.get("authors")
                else None
            ),
            "abstract": (
                record["abstract"].strip().lower()[:500]  # truncated for performance
                if record.get("abstract")
                else None
            ),
            "doi": (_sanitize_doi(record["doi"]) if record.get("doi") else None),
        }
        # derivative fields
        record["authors_joined"] = (
            "; ".join(record["authors"]) if record.get("authors") else None
        )
        return record

    def fit(
        self,
        data: dict[Any, dict[str, Any]],
        training_fpath: Optional[str | pathlib.Path] = None,
        recall: float = 1.0,
        index_predicates: bool = True,
    ) -> "Deduper":
        if isinstance(self.model, dedupe.StaticDedupe):
            raise TypeError("deduper loaded from a settings file can't be re-fit")
        LOGGER.info("preparing model %s for training ...", self.model)
        if training_fpath is None:
            self.model.prepare_training(data)
        else:
            training_fpath = utils.to_path(training_fpath)
            with training_fpath.open(mode="r") as f:
                self.model.prepare_training(data, training_file=f)

        dedupe.console_label(self.model)
        LOGGER.info("training model on labeled examples ...")
        self.model.train(recall, index_predicates)
        return self

    def predict(
        self, data: dict[Any, dict[str, Any]], threshold: float = 0.5
    ) -> list[tuple[tuple, tuple[float, ...]]]:
        return self.model.partition(data, threshold=threshold)  # type: ignore

    def save(self, dir_path: str | pathlib.Path) -> None:
        if isinstance(self.model, dedupe.StaticDedupe):
            raise TypeError("deduper loaded from a settings file can't be re-saved")
        dir_path = utils.to_path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        LOGGER.info("saving deduper model setings and training data to %s", dir_path)
        with (dir_path / SETTINGS_FNAME).open(mode="wb") as f:
            self.model.write_settings(f)
        with (dir_path / TRAINING_FNAME).open(mode="w") as f:
            self.model.write_training(f)


def _sanitize_doi(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("http://") or value.startswith("https://"):
        value = urllib.parse.unquote(value)
    return value
