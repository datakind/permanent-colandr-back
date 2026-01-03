import os

import pandas as pd
import pytest
import river.compose

from colandr.lib.models import StudyRanker


TEST_RECORDS = (
    {
        "text": (
            "Mary had a little lamb, its fleece was white as snow; "
            "and everywhere that Mary went the lamb was sure to go."
        ),
        "target": True,
    },
    {
        "text": (
            "It followed her to school one day, which was against the rule; "
            "it made the children laugh and play to see a lamb at school."
        ),
        "target": True,
    },
    {
        "text": (
            "And so the teacher turned it out, but still it lingered near, "
            "and waited patiently about till Mary did appear."
        ),
        "target": True,
    },
    {
        "text": (
            "Why does the lamb love Mary so? the eager children cry; "
            "Why, Mary loves the lamb, you know, the teacher did reply."
        ),
        "target": True,
    },
    {
        "text": (
            "Jack and Jill went up the hill to fetch a pail of water. "
            "Jack fell down and broke his crown, and Jill came tumbling after."
        ),
        "target": False,
    },
    {
        "text": (
            "Up Jack got and home did trot as fast as he could caper; "
            "And went to bed and bound his head with vinegar and brown paper."
        ),
        "target": False,
    },
    {
        "text": (
            "When Jill came in how she did grin to see Jack's paper plaster; "
            "Mother vexed did whip her next for causing Jack's disaster."
        ),
        "target": False,
    },
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
        assert sranker._num_texts_learned == 7
        assert model_["featurizer"].n == 7
        assert model_["featurizer"].dfs
        assert all(value >= 1 for value in model_["featurizer"].dfs.values())
        assert model_["classifier"].classifier.weights
        assert all(
            value != 0.0 for value in model_["classifier"].classifier.weights.values()
        )
        assert (
            "mary" in model_["featurizer"].dfs and model_["featurizer"].dfs["mary"] == 3
        )
        assert len(model_["selector"].included) > 0
        if "mary" in model_["selector"].included:
            assert (
                "mary" in model_["classifier"].classifier.weights
                and model_["classifier"].classifier.weights["mary"] != 0.0
            )

        # persist trained model for use in subsequent tests
        sranker.save()

    @pytest.mark.parametrize(
        ["record", "proba", "exp_pred"],
        [
            ({"text": "Mary ate a little breakfast with her lamb."}, False, True),
            ({"text": "Jill went up the hill with Jack to fetch water."}, True, False),
            (
                {"text": "Mary went to school with the white lamb, despite the rule."},
                True,
                True,
            ),
            (
                {"text": "Jill broke the pail of water, which vexed Mother and Jack."},
                False,
                False,
            ),
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

    @pytest.mark.parametrize("review_id", [1, 2])
    def test_save(self, review_id, app, tmp_study_ranker_path):
        fs = app.extensions["filesystem"]
        sranker1 = StudyRanker(review_id, tmp_study_ranker_path, fs)
        sranker1.save()
        sranker2 = StudyRanker(review_id, tmp_study_ranker_path, fs)
        assert (
            sranker1.model["classifier"].classifier.weights
            == sranker2.model["classifier"].classifier.weights
        )
        os.unlink(sranker1.model_fpath)
