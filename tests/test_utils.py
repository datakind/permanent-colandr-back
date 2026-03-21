import pytest

from colandr import utils


@pytest.mark.parametrize(
    ["keyterms", "exp_result"],
    [
        (
            [{"term": "foo", "group": "test", "synonyms": ["bar", "bat"]}],
            '("foo" OR "bar" OR "bat")',
        ),
        (
            [
                {"term": "foo", "group": "test1"},
                {"term": "spam", "group": "test2", "synonyms": ["eggs"]},
            ],
            '"foo"\nAND\n("spam" OR "eggs")',
        ),
    ],
)
def test_get_boolean_search_query(keyterms, exp_result):
    result = utils.get_boolean_search_query(keyterms)
    assert result == exp_result
