import pytest

from colandr import utils


@pytest.mark.parametrize(
    ["screening_statuses", "num_screeners", "exp_result"],
    [
        ([], 0, "not_screened"),
        ([], 1, "not_screened"),
        ([], 2, "not_screened"),
        (["included"], 1, "included"),
        (["excluded"], 1, "excluded"),
        (["included"], 2, "screened_once"),
        (["excluded"], 3, "screened_once"),
        (["included", "excluded"], 3, "screened_twice"),
        (["included", "included"], 2, "included"),
        (["excluded", "excluded"], 2, "excluded"),
        (["included", "excluded"], 2, "conflict"),
        (["included", "excluded"], 1, "conflict"),
        (["included", "included", "excluded"], 3, "conflict"),
    ],
)
def test_assign_status(screening_statuses, num_screeners, exp_result):
    assert utils.assign_status(screening_statuses, num_screeners) == exp_result


@pytest.mark.parametrize(
    ["keyterms", "exp_result"],
    [
        ([], ""),
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
        # groups are ordered by name, not by input order
        (
            [
                {"term": "TERM2", "group": "GROUP2"},
                {"term": "TERM1", "group": "GROUP1"},
            ],
            '"TERM1"\nAND\n"TERM2"',
        ),
        # empty synonym list is falsy: term is quoted alone
        ([{"term": "foo", "group": "g", "synonyms": []}], '"foo"'),
        # corrupted data guard: a comma-joined string is split, not iterated
        (
            [{"term": "foo", "group": "g", "synonyms": "bar, bat"}],
            '("foo" OR "bar" OR "bat")',
        ),
    ],
)
def test_get_boolean_search_query(keyterms, exp_result):
    result = utils.get_boolean_search_query(keyterms)
    assert result == exp_result
