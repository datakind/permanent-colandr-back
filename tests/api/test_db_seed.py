"""Minimal smoke test for ``flask db-seed`` and the seed dataset it loads.

This is deliberately not comprehensive, since API endpoints are already well-covered.
Instead this covers the *ingestion* path -- cli.db_seed's ``models.X(**record)`` loops,
the password setter on seeded users, and raw-SQL sequence resync that keeps later inserts
from colliding with the seed's explicit ids -- plus the validity of the shipped dataset.

TODO: This only exists to keep ``db-seed`` and ``tests/fixtures/seed_data.json`` honest;
the file is a hand-maintained description of the schema that only this module reads.
The proper fix is to derive it from the factories, or move it out of ``tests/``
as a dev-only artifact. Either way, this module and ``db_seeded`` can then be deleted.
"""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_seeded")

SEEDED_REVIEW_ID = 1


def test_db_seed_loads_reviews_and_studies(api):
    """Seeded reviews, plans, and studies ingest and read back."""
    response = api.get("reviews.review", id=SEEDED_REVIEW_ID)
    assert response.status_code == 200
    assert response.json["name"] == "NAME1"
    assert response.json["description"] == "DESCRIPTION1"

    response = api.get("studies.studies", review_id=SEEDED_REVIEW_ID)
    assert response.status_code == 200
    assert len(response.json) == 3
    assert sorted(study["citation"]["title"] for study in response.json) == [
        "TITLE1",
        "TITLE2",
        "TITLE3",
    ]


def test_db_seed_stores_hashed_user_passwords(client, db_session):
    """Seeded users can log in, so ``db-seed`` hashed their plaintext passwords.

    ``db_session`` is load-bearing even though the request goes through the raw
    ``client``: without an active savepoint session, the route reads through the
    long-lived app-context session, whose read transaction is never committed and
    whose locks then block the next world's TRUNCATE indefinitely.
    """
    response = client.post(
        "/api/auth/login",
        json={"email": "name1@example.com", "password": "PASSWORD1"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json


def test_db_seed_resyncs_id_sequences(db_session):
    """Creating rows after seeding doesn't collide with the seed's explicit ids."""
    user = factories.create_user(db_session)
    assert user.id > 5  # the seed defines users 1-5
