import logging
import pathlib
import typing as t
from collections.abc import Iterable

import joblib
import pandas as pd
import river.compose
import river.feature_extraction
import river.linear_model
import river.optim
import scipy.sparse


LOGGER = logging.getLogger(__name__)


class StudyRanker:
    _model_fname_tmpl: str = "study_ranker__review_{review_id:06}.pkl"
    feature_col: str = "text"
    target_col: str = "target"

    def __init__(self, review_id: int, dir_path: str | pathlib.Path):
        self.review_id = review_id
        self.dir_path = pathlib.Path(dir_path)
        self._model = None

    def __str__(self) -> str:
        return f"StudyRanker(review_id={self.review_id}, dir_path='{self.dir_path}')"

    def __eq__(self, other):
        return self.review_id == other.review_id and self.dir_path == other.dir_path

    def __hash__(self):
        return hash((self.review_id, self.dir_path))

    @property
    def model_fpath(self) -> pathlib.Path:
        return (
            self.dir_path
            / f"review_{self.review_id:06}"
            / self._model_fname_tmpl.format(review_id=self.review_id)
        )

    @property
    def model(self) -> river.compose.Pipeline:
        if self._model is None:
            model_fpath = self.model_fpath
            if model_fpath.exists():
                self._model = self.load()
            else:
                self._model = _MODEL.clone()
        return self._model

    @model.setter
    def model(self, value: river.compose.Pipeline) -> None:
        self._model = value

    def clone(self) -> river.compose.Pipeline:
        """Make a fresh clone of :attr:`StudyRanker._model` ."""
        _model = _MODEL.clone()
        LOGGER.debug(
            "<Review(id=%s)>: new study ranker model cloned ...", self.review_id
        )
        return _model

    def load(self) -> river.compose.Pipeline:
        """Load existing model from disk at :attr:`StudyRanker.model_fpath` ."""
        model_fpath = self.model_fpath
        with model_fpath.open(mode="rb") as f:
            _model = joblib.load(f)
        LOGGER.debug(
            "<Review(id=%s)>: study ranker model loaded from %s ...",
            self.review_id,
            model_fpath,
        )
        return _model

    def save(self) -> None:
        """
        Save instance of :attr:`StudyRanker._model`
        to disk at :attr:`StudyRanker.model_fpath` .
        """
        model_fpath = self.model_fpath
        _model = self.model
        model_fpath.parent.mkdir(parents=True, exist_ok=True)
        with model_fpath.open(mode="wb") as f:
            joblib.dump(_model, f)
        LOGGER.info(
            "<Review(id=%s)>: study ranker model saved to %s",
            self.review_id,
            model_fpath,
        )

    def learn_one(self, record: dict[str, t.Any]) -> None:
        x = record[self.feature_col]
        y = record[self.target_col]
        self.model.learn_one(x, y)

    def learn_many(self, records: Iterable[dict[str, t.Any]]) -> None:
        df = pd.DataFrame(data=records)
        if df.empty:
            LOGGER.warning("no records in batch to learn from! skipping ...")
            return

        X = df[self.feature_col].astype("string")
        y = df[self.target_col]
        self.model.learn_many(X, y)
        # sequential fallback in case minibatching isn't feasible
        # for record in records:
        #     self.learn_one(record)

    def predict_one(
        self, record: dict[str, t.Any], *, proba: bool = False
    ) -> bool | dict[bool, float]:
        x = record[self.feature_col]
        if not proba:
            return self.model.predict_one(x)
        else:
            return self.model.predict_proba_one(x)

    def predict_many(
        self, records: Iterable[dict[str, t.Any]], *, proba: bool = False
    ) -> pd.Series | pd.DataFrame:
        X = pd.DataFrame(data=records)[self.feature_col].astype("string")
        if not proba:
            return self.model.predict_many(X)
        else:
            return self.model.predict_proba_many(X)


class ColandrTFIDF(river.feature_extraction.TFIDF):
    """
    Child of :class:`river.feature_extraction.TFIDF` that adds mini-batch functionality,
    i.e. ``transform_many()`` and ``learn_many()`` methods.
    """

    def learn_many(self, X: pd.Series) -> None:
        # increment global document counter
        self.n += X.shape[0]
        # update document counts
        doc_counts = (
            X.map(lambda x: set(self.process_text(x)))
            .explode()
            .value_counts()
            .to_dict()
        )
        self.dfs.update(doc_counts)

    def transform_many(self, X: pd.Series) -> pd.DataFrame:
        """Transform pandas series of string into tf-idf pandas sparse dataframe."""
        indptr, indices, data = [0], [], []
        index: dict[int, int] = {}
        for doc in X:
            term_weights: dict[int, float] = self.transform_one(doc)
            for term, weight in term_weights.items():
                indices.append(index.setdefault(term, len(index)))
                data.append(weight)
            indptr.append(len(data))

        return pd.DataFrame.sparse.from_spmatrix(
            scipy.sparse.csr_matrix((data, indices, indptr)),
            index=X.index,
            columns=index.keys(),
        )


_MODEL = river.compose.Pipeline(
    (
        "featurizer",
        # TODO: use river.feature_extraction.TFIDF once mini-batch capabilities added
        # TODO: use ngram_range=(1, 2) for unigrams and bigrams?
        ColandrTFIDF(normalize=True, strip_accents=False, ngram_range=(1, 1)),
    ),
    # TODO: do we need an l2 normalizer...?
    # ("normalizer", preprocessing.Normalizer(order=2))
    (
        "classifier",
        river.linear_model.LogisticRegression(
            optimizer=river.optim.SGD(lr=0.5),
            loss=river.optim.losses.BinaryFocalLoss(),
            initializer=river.optim.initializers.Zeros(),
            l2=0.001,
        ),
    ),
)
