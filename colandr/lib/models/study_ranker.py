import logging
import os
import typing as t
from collections.abc import Iterable

import fsspec
import joblib
import pandas as pd
import river.compose
import river.feature_extraction
import river.feature_selection
import river.imblearn
import river.linear_model
import river.optim
import scipy.sparse


LOGGER = logging.getLogger(__name__)


class StudyRanker:
    _model_fname_tmpl: str = "study_ranker__review_{review_id:08}.pkl"

    def __init__(
        self,
        review_id: int,
        dir_path: str,
        fs: fsspec.AbstractFileSystem,
        *,
        text_col: str = "text",
        target_col: str = "target",
    ):
        self.review_id = review_id
        self.dir_path = dir_path
        self.fs = fs
        self.text_col = text_col
        self.target_col = target_col
        self._model: t.Optional[river.compose.Pipeline] = None

    def __str__(self) -> str:
        return f"StudyRanker(review_id={self.review_id}, dir_path='{self.dir_path}')"

    def __eq__(self, other):
        return self.review_id == other.review_id and self.dir_path == other.dir_path

    def __hash__(self):
        return hash((self.review_id, self.dir_path))

    @property
    def model(self) -> river.compose.Pipeline:
        if self._model is None:
            if self.model_exists:
                try:
                    self._model = self.load()
                except AttributeError:
                    LOGGER.exception("unable to load existing model; cloning instead")
                    self._model = self.clone()
            else:
                self._model = self.clone()
        return self._model

    @model.setter
    def model(self, value: river.compose.Pipeline) -> None:
        self._model = value

    @property
    def model_fpath(self) -> str:
        return os.path.join(
            self.dir_path,
            f"review_{self.review_id:08}",
            self._model_fname_tmpl.format(review_id=self.review_id),
        )

    @property
    def model_exists(self) -> bool:
        return self.fs.exists(self.model_fpath)

    def clone(self) -> river.compose.Pipeline:
        """Make a fresh clone of :attr:`StudyRanker._model` ."""
        _model = _MODEL.clone()
        LOGGER.info(
            "<Review(id=%s)>: new study ranker model cloned ...", self.review_id
        )
        return _model

    def load(self) -> river.compose.Pipeline:
        """Load existing model from disk at :attr:`StudyRanker.model_fpath` ."""
        model_fpath = self.model_fpath
        with self.fs.open(model_fpath, mode="rb") as f:
            _model = joblib.load(f)
        LOGGER.info(
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
        self.fs.makedirs(os.path.dirname(model_fpath), exist_ok=True)
        with self.fs.open(model_fpath, mode="wb") as f:
            joblib.dump(_model, f)
        LOGGER.info(
            "<Review(id=%s)>: study ranker model saved to %s",
            self.review_id,
            model_fpath,
        )

    def learn_one(self, record: dict[str, t.Any]) -> None:
        x = record[self.text_col]
        y = record[self.target_col]
        if not x:
            LOGGER.warning(
                "StudyRanker.learn_one() can't learn from empty record text; skipping ..."
            )
            return
        self.model.learn_one(x, y)

    def predict_one(
        self, record: dict[str, t.Any], *, proba: bool = False
    ) -> bool | dict[bool, float]:
        x = record[self.text_col]
        if not proba:
            return self.model.predict_one(x)
        else:
            return self.model.predict_proba_one(x)

    @property
    def _num_texts_learned(self) -> int:
        return self.model["featurizer"].n


# NOTE: when the model has a feature selector included, we can't learn/transform many
# so it's best just to skip this custom tfidf extractor
# class ColandrTFIDF(river.feature_extraction.TFIDF):
#     """
#     Child of :class:`river.feature_extraction.TFIDF` that adds mini-batch functionality,
#     i.e. ``transform_many()`` and ``learn_many()`` methods.
#     """

#     def learn_many(self, X: pd.Series) -> None:
#         # increment global document counter
#         self.n += X.shape[0]
#         # update document counts
#         doc_counts = (
#             X.map(lambda x: set(self.process_text(x)))
#             .explode()
#             .value_counts()
#             .to_dict()
#         )
#         self.dfs.update(doc_counts)

#     def transform_many(self, X: pd.Series) -> pd.DataFrame:
#         """Transform pandas series of string into tf-idf pandas sparse dataframe."""
#         indptr, indices, data = [0], [], []
#         index: dict[int, int] = {}
#         for doc in X:
#             term_weights: dict[int, float] = self.transform_one(doc)
#             for term, weight in term_weights.items():
#                 indices.append(index.setdefault(term, len(index)))
#                 data.append(weight)
#             indptr.append(len(data))

#         return pd.DataFrame.sparse.from_spmatrix(
#             scipy.sparse.csr_matrix((data, indices, indptr)),
#             index=X.index,
#             columns=index.keys(),
#         )


# NOTE: if we decide that we prefer to limit the tfidf vocabulary, add xxhash as a dep
# and swap this in for the tfidf transformer's tokenizer
# def hash_tokenizer(text: str, pattern: re.Pattern | str, vocab_size: int) -> t.Iterator[str]:
#     tokens = river.feature_extraction.vectorize.tokenize_using_regex_pattern(text, pattern)
#     for token in tokens:
#         yield xxhash.xxh128_intdigest(bytes(token, encoding="utf-8")) % vocab_size


_MODEL = river.compose.Pipeline(
    (
        "featurizer",
        river.feature_extraction.TFIDF(
            # this is handled via StudyRanker.text_col
            on=None,
            normalize=True,
            strip_accents=False,
            # tokenizer=ft.partial(hash_tokenizer, pattern=r"(?u)\b\w[\w\-]+\b", vocab_size=50_000),
            ngram_range=(1, 2),
        ),
    ),
    # chop off the long tail of rare vocabulary words
    ("selector", river.feature_selection.PoissonInclusion(p=0.25, seed=0)),
    (
        "classifier",
        # re-learning from hard examples should help with expected class imbalance
        river.imblearn.HardSamplingClassifier(
            classifier=river.linear_model.LogisticRegression(
                optimizer=river.optim.SGD(
                    lr=river.optim.schedulers.Optimal(
                        loss=river.optim.losses.BinaryFocalLoss(),
                        alpha=0.001,
                    ),
                ),
                # this loss func also helps with expected class imbalance
                loss=river.optim.losses.BinaryFocalLoss(),
                initializer=river.optim.initializers.Zeros(),
                l2=0.001,
            ),
            size=25,
            p=0.1,
            loss=river.optim.losses.BinaryFocalLoss(),
        ),
    ),
)
