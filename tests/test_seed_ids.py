"""Tests to ensure that ``seed_ids.py`` stays consistent with ``seed_data.json``."""

import json
import pathlib

import pytest

from .fixtures import seed_ids


@pytest.fixture(scope="module")
def seed_records() -> dict:
    fpath = pathlib.Path(__file__).parent / "fixtures" / "seed_data.json"
    with fpath.open() as f:
        return json.load(f)


@pytest.mark.parametrize(
    ["seed_key", "enum_cls"],
    [("users", seed_ids.Users), ("reviews", seed_ids.Reviews)],
)
def test_enum_ids_match_seed(seed_key, enum_cls, seed_records):
    seed_ids_set = {record["id"] for record in seed_records[seed_key]}
    enum_ids_set = {int(member) for member in enum_cls}
    assert seed_ids_set == enum_ids_set


@pytest.mark.parametrize(
    ["user_enum_val", "is_admin", "is_confirmed"],
    [
        (seed_ids.Users.ADMIN, True, True),
        (seed_ids.Users.OWNER, False, True),
        (seed_ids.Users.UNCONFIRMED, False, False),
    ],
)
def test_user_attributes(user_enum_val, is_admin, is_confirmed, seed_records):
    record = next(r for r in seed_records["users"] if r["id"] == user_enum_val)
    assert record["is_admin"] is is_admin
    assert record["is_confirmed"] is is_confirmed


def test_outsider_user_has_no_review_associations(seed_records):
    associations = [
        a
        for a in seed_records["review_user_associations"]
        if a["user_id"] == seed_ids.Users.OUTSIDER
    ]
    assert associations == []


def test_frozen_review_is_actually_frozen(seed_records):
    record = next(
        r for r in seed_records["reviews"] if r["id"] == seed_ids.Reviews.FROZEN
    )
    assert record.get("status") == "frozen"


def test_nonexistent_ids_truly_absent(seed_records):
    user_ids = {r["id"] for r in seed_records["users"]}
    review_ids = {r["id"] for r in seed_records["reviews"]}
    assert seed_ids.NONEXISTENT_USER_ID not in user_ids
    assert seed_ids.NONEXISTENT_REVIEW_ID not in review_ids
