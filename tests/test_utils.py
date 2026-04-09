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
        (
            [
                {"term": "foo", "group": "test1"},
                {"term": "bar", "group": "test1", "synonyms": ["bat", "baz"]},
                {"term": "spam", "group": "test2", "synonyms": ["eggs"]},
            ],
            '("foo" OR ("bar" OR "bat" OR "baz"))\nAND\n("spam" OR "eggs")',
        ),
        (
            [
                {"term": "TERM1", "group": "GROUP1"},
                {"term": "TERM2", "group": "GROUP2"},
                {"term": "TERM3", "group": "GROUP1"},
            ],
            '("TERM1" OR "TERM3")\nAND\n"TERM2"',
        ),
    ],
)
def test_get_boolean_search_query(keyterms, exp_result):
    result = utils.get_boolean_search_query(keyterms)
    assert result == exp_result
