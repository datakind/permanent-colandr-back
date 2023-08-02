from __future__ import annotations

import functools
import logging
import pathlib
from collections.abc import Iterable
from typing import Any, Optional

import dedupe

from .. import utils


LOGGER = logging.getLogger(__name__)

SETTINGS_FNAME = "deduper_settings"
TRAINING_FNAME = "deduper_training.json"
VARIABLES_DEFAULT: list[dict[str, Any]] = [
    {"field": "title", "type": "String"},
    {"field": "pub_year", "type": "Exact"},
    {"field": "authors", "type": "Set", "has missing": True},
    # TODO: figure out if/how we want to incorporate abstract
    # {"field": "abstract", "type": "Text", "has missing": True},
    {"field": "doi", "type": "ShortString", "has missing": True},
    {"field": "issn", "type": "ShortString", "has missing": True},
]


class Deduper:
    def __init__(
        self,
        *,
        variables: Optional[list[dict[str, Any]]] = None,
        settings_fpath: Optional[str | pathlib.Path] = None,
        num_cores: int = 1,
        in_memory: bool = False,
    ):
        self.variables = variables or VARIABLES_DEFAULT
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
                self.variables,  # type: ignore
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
        def _preprocess_value(value):
            if not value:
                return None
            if isinstance(value, str):
                value = value.strip().lower() or None
            elif isinstance(value, list):
                value = tuple(value)
            return value

        fields = [pv.field for pv in self.model.data_model.primary_variables]
        LOGGER.info("preprocessing data with fields %s ...", fields)
        return {
            record.pop(id_key): {
                field: _preprocess_value(record.get(field, None)) for field in fields
            }
            for record in data
        }

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
        self.model.train(recall, index_predicates)
        self.model.cleanup_training()
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
