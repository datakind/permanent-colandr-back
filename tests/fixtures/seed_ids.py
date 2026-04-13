"""Named identifiers for entities in ``tests/fixtures/seed_data.json``.

Tests should reference these enums instead of raw integers so that parametrized cases
are self-documenting and typo-resistant.

Uses :class:`enum.IntEnum`, so that members work anywhere a plain ``int`` is expected,
such as ``db_session.get(User, Users.ADMIN)`` or ``flask.url_for("...", id=Reviews.SHARED)``
When a test fails, pytest renders the member as e.g. ``Users.ADMIN`` rather than ``1``.

Scenario matrix
---------------
The seed file is small and stable. The relationships below are the
authoritative reference for which user/review combinations exercise which
authorization rules::

                                                  REVIEW MEMBERSHIPS
                                                  R1    R2    R3 (frozen)
    USER_ADMIN        (id=1)  admin, confirmed    own   —     —
    USER_OWNER        (id=2)         confirmed    own   own   —
    USER_MEMBER       (id=3)         confirmed    mem   mem   own
    USER_OUTSIDER     (id=4)         confirmed    —     —     —
    USER_UNCONFIRMED  (id=5)         unconfirmed  —     —     —

    REVIEW_SHARED   (id=1)  active, co-owned by ADMIN & OWNER, MEMBER is member
    REVIEW_OWNED    (id=2)  active, owned by OWNER, MEMBER is member
    REVIEW_FROZEN   (id=3)  status='frozen', owned by MEMBER
"""

import enum


class Users(enum.IntEnum):
    """Seed user identifiers, named by their primary role in tests."""

    ADMIN = 1
    OWNER = 2
    MEMBER = 3
    OUTSIDER = 4
    UNCONFIRMED = 5


class Reviews(enum.IntEnum):
    """Seed review identifiers, named by their access pattern."""

    SHARED = 1
    OWNED = 2
    FROZEN = 3


# user id guaranteed not to exist in the seed data, for use in 404 tests
NONEXISTENT_USER_ID = 999

# review id guaranteed not to exist in the seed data, for use in 404 tests
NONEXISTENT_REVIEW_ID = 999
