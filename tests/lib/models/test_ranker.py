from contextlib import nullcontext as does_not_raise

import pytest
from sklearn.utils.validation import check_is_fitted

from colandr.lib.models import Ranker


@pytest.fixture(scope="class")
def tmp_ranker_path(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("ranker")
    yield tmp_path


class TestRanker:
    @pytest.mark.parametrize("review_id", [1, 2])
    def test_init(self, review_id):
        ranker = Ranker(review_id=review_id)
        assert ranker.review_id == review_id
        assert ranker.model is not None

    @pytest.mark.parametrize(
        ["feature_vecs", "labels", "review_id"],
        [
            (
                [[1.0, 0.0, 1.0, 0.5], [1.0, 0.25, 0.75, 0.25], [0.0, 1.0, 0.25, 0.75]],
                ["included", "included", "excluded"],
                1,
            ),
        ],
    )
    def test_fit(self, feature_vecs, labels, review_id):
        ranker = Ranker(review_id=review_id)
        result = ranker.fit(feature_vecs, labels)
        assert ranker.model is not None
        assert isinstance(result, Ranker)
        with does_not_raise():
            check_is_fitted(ranker.model)

    @pytest.mark.parametrize("review_id", [1, 2])
    def test_save_and_load(self, review_id, tmp_ranker_path):
        ranker = Ranker(review_id=review_id)
        ranker.save(tmp_ranker_path)
        ranker_loaded = Ranker.load(tmp_ranker_path, review_id)
        assert ranker_loaded.model is not None
