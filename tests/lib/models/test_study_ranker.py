import os

import pandas as pd
import pytest
import river.compose

from colandr.lib.models import StudyRanker


TEST_RECORDS = (
    {"text": "Mary had a little lamb.", "target": True},
    {"text": "Its fleece was white as snow.", "target": False},
    {"text": "And everywhere that Mary went...", "target": True},
    {"text": "The lamb was sure to go.", "target": False},
)


@pytest.fixture(scope="class")
def tmp_study_ranker_path(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("ranker_models")
    yield tmp_path


class TestStudyRanker:
    @pytest.mark.parametrize("review_id", [1, 2])
    def test_init(self, review_id, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(review_id, tmp_study_ranker_path, fs)
        assert sranker.review_id == review_id
        assert sranker.dir_path == tmp_study_ranker_path
        assert sranker._model is None

    @pytest.mark.parametrize("review_id", [1, 2])
    def test_model_fpath(self, review_id, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(review_id, tmp_study_ranker_path, fs)
        assert str(tmp_study_ranker_path) in sranker.model_fpath
        assert f"review_{review_id:08}" in os.path.basename(sranker.model_fpath)

    @pytest.mark.parametrize("review_id", [1, 2])
    def test_dunders(self, review_id, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(review_id, tmp_study_ranker_path, fs)
        assert sranker == StudyRanker(review_id, tmp_study_ranker_path, fs)  # __eq__
        assert sranker in {
            StudyRanker(review_id, tmp_study_ranker_path, fs)
        }  # __hash__

    @pytest.mark.parametrize("review_id", [1, 2])
    def test_model(self, review_id, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(review_id, tmp_study_ranker_path, fs)
        assert sranker.model is not None
        assert isinstance(sranker.model, river.compose.Pipeline)

    @pytest.mark.parametrize("records", [TEST_RECORDS])
    def test_learn_one(self, records, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(1, tmp_study_ranker_path, fs)
        for record in records:
            sranker.learn_one(record)
        model_ = sranker.model
        assert sranker._num_texts_learned == 4
        assert model_["featurizer"].n == 4
        assert model_["featurizer"].dfs
        assert all(value >= 1 for value in model_["featurizer"].dfs.values())
        assert model_["classifier"].weights
        assert all(value != 0.0 for value in model_["classifier"].weights.values())
        assert (
            "mary" in model_["featurizer"].dfs and model_["featurizer"].dfs["mary"] == 2
        )
        assert (
            "mary" in model_["classifier"].weights
            and model_["classifier"].weights["mary"] != 0.0
        )
        # persist trained model for use in subsequent tests
        sranker.save()

    @pytest.mark.parametrize("records", [TEST_RECORDS])
    def test_learn_many(self, records, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(2, tmp_study_ranker_path, fs)
        sranker.learn_many(records)
        model_ = sranker.model
        assert sranker._num_texts_learned == 4
        assert model_["featurizer"].n == 4
        assert model_["featurizer"].dfs
        assert all(value >= 1 for value in model_["featurizer"].dfs.values())
        assert model_["classifier"].weights
        assert all(value != 0.0 for value in model_["classifier"].weights.values())
        assert (
            "mary" in model_["featurizer"].dfs and model_["featurizer"].dfs["mary"] == 2
        )
        assert (
            "mary" in model_["classifier"].weights
            and model_["classifier"].weights["mary"] != 0.0
        )
        # persist trained model for use in subsequent tests
        sranker.save()

    @pytest.mark.parametrize(
        ["record", "proba", "exp_pred"],
        [
            ({"text": "Mary ate a little breakfast."}, False, True),
            ({"text": "The lamb was white in color."}, True, False),
            ({"text": "Mary went everywhere with the lamb."}, True, True),
            ({"text": "Fleece is soft and fluffy like snow."}, False, False),
        ],
    )
    def test_predict_one(self, record, proba, exp_pred, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(1, tmp_study_ranker_path, fs)
        pred = sranker.predict_one(record, proba=proba)
        if proba:
            assert pred and isinstance(pred, dict)
            assert pred[True] >= 0.0 and pred[True] <= 1.0
            assert pred[True] > pred[False] if exp_pred else pred[True] < pred[False]
        else:
            assert isinstance(pred, bool)
            assert pred is exp_pred

    @pytest.mark.parametrize(
        ["records", "proba", "exp_preds"],
        [
            (
                [
                    {"text": "Mary ate a little breakfast."},
                    {"text": "The lamb was white in color."},
                ],
                False,
                pd.Series([True, False]),
            ),
            (
                [
                    {"text": "Mary went everywhere with the lamb."},
                    {"text": "Fleece is soft and fluffy like snow."},
                ],
                True,
                pd.Series([True, False]),
            ),
        ],
    )
    def test_predict_many(self, records, proba, exp_preds, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker = StudyRanker(2, tmp_study_ranker_path, fs)
        preds = sranker.predict_many(records, proba=proba)
        if proba:
            assert isinstance(preds, pd.DataFrame)
            assert (preds.columns == [False, True]).all()
            assert preds.idxmax(axis="columns").equals(exp_preds)
        else:
            assert isinstance(preds, pd.Series)
            assert preds.equals(exp_preds)

    @pytest.mark.parametrize("review_id", [1, 2])
    def test_save(self, review_id, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker1 = StudyRanker(review_id, tmp_study_ranker_path, fs)
        sranker1.save()
        sranker2 = StudyRanker(review_id, tmp_study_ranker_path, fs)
        assert (
            sranker1.model["classifier"].weights == sranker2.model["classifier"].weights
        )
        os.unlink(sranker1.model_fpath)
