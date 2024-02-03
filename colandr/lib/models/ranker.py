import functools
import logging
import pathlib
import typing as t
from collections.abc import Iterable, Sequence

import joblib
import numpy as np
import sklearn.base
import sklearn.linear_model

from .. import utils


LOGGER = logging.getLogger(__name__)

_MODEL_FNAME = "citation_ranking_model_review_{review_id}.pkl"


class Ranker:
    def __init__(
        self, *, review_id: int, model_fpath: t.Optional[str | pathlib.Path] = None
    ):
        self.review_id = review_id
        self.model_fpath = model_fpath

    @classmethod
    def load(cls, dir_path: str | pathlib.Path, review_id: int) -> "Ranker":
        model_fpath = utils.to_path(dir_path) / _MODEL_FNAME.format(review_id=review_id)
        return cls(model_fpath=model_fpath, review_id=review_id)

    @functools.cached_property
    def model(self) -> sklearn.base.BaseEstimator:
        if self.model_fpath is None:
            _model = sklearn.linear_model.SGDClassifier(class_weight="balanced")
        else:
            with open(self.model_fpath, mode="rb") as f:
                _model = joblib.load(f)
        return _model

    def fit(
        self,
        feature_vecs: Iterable[Sequence[float]],
        labels: Iterable[str],
    ) -> "Ranker":
        X = np.vstack(tuple(feature_vec for feature_vec in feature_vecs))
        y = np.array(tuple(1 if label == "included" else 0 for label in labels))
        self.model.fit(X, y)
        return self

    def predict(
        self, feature_vecs: Iterable[Sequence[float]]
    ) -> list[tuple[tuple, tuple[float, ...]]]:
        X = np.vstack(tuple(feature_vec for feature_vec in feature_vecs))
        return self.model.decision_function(X).tolist()

    def save(self, dir_path: str | pathlib.Path) -> None:
        dir_path = utils.to_path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / _MODEL_FNAME.format(review_id=self.review_id)
        with file_path.open(mode="wb") as f:
            joblib.dump(self.model, f)
        LOGGER.info(
            "<Review(id=%s)>: citation ranking model saved to %s",
            self.review_id,
            file_path,
        )
