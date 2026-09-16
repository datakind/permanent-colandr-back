"""Test factories for creating database records.

Each factory takes the test session as its first arg, flushes the records it creates,
and returns the primary object it created. Default values are deterministic and unique
within a truncated world, so a failure reproduces byte-for-byte on the next run.
Override any default attribute by passing in the override's value.

Factories return objects whose state matches the database, including columns written
by model event listeners: :func:`create_screening()` expires the study it touched,
so ``citation_status``/``fulltext_status`` read fresh.

IMPORTANT:

- ``Review`` insert auto-creates its ``ReviewPlan`` with the same id, so never create
  a plan by hand; use :func:`update_review_plan()` to set its fields.
- A ``Screening`` insert/update/delete recomputes the parent study's stage status
  from the screenings in that stage and writes it with a Core UPDATE, so factories
  expire the study they touched.
- A *citation* stage that recomputes to anything but "included" deletes that study's
  *fulltext* screenings. The reverse never happens: a fulltext screening inserted after
  the citation stage is left alone, which yields a citation-excluded study with
  ``fulltext_status == "included"`` and a stray ``DataExtraction`` row. therefore,
  :func:`create_screening()` raises instead of letting you build that state.
- Order: create studies before their screenings, and for an included study
  screen the citation stage before the fulltext stage.
"""

import itertools
import os
import pathlib
import typing as t
from collections.abc import Sequence

import flask
import sqlalchemy.orm as sa_orm

from colandr import models


# TODO: add more factory funcs
# - `create_study_with_screenings()` that combines 1 study and 1+ screening factory calls
#   analogous to `create_review_with_team`

DEFAULT_REVIEWER_PCTS = [{"num": 1, "pct": 100}]
UNUSABLE_PASSWORD = "!"  # werkzeug sentinel: satisfies NOT NULL, hashing-free
_AUTO_NUM = itertools.count(1)  # deterministic default names, unique per session


def create_user(
    session: sa_orm.Session,
    *,
    name: str = "Test User",
    email: t.Optional[str] = None,
    password: t.Optional[str] = None,
    is_admin: bool = False,
    is_confirmed: bool = True,
) -> models.User:
    """Create a user with a unique email address.

    Args:
        session
        name: User's display name. Seeds the generated email when omitted.
        email: User's email address; generated (unique) when omitted.
        password: Plaintext password, hashed via the model's setter. When omitted,
            an unusable sentinel is stored instead.
        is_admin: Whether the user has admin privileges.
        is_confirmed: Whether the user has confirmed their account.
    """
    user = models.User(
        name=name,
        email=email or _unique_email(name),
        is_admin=is_admin,
        is_confirmed=is_confirmed,
    )
    if password is None:
        user._password = UNUSABLE_PASSWORD  # sentinel value, skips scrypt
    else:
        user.password = password  # => property setter hashes it
    session.add(user)
    session.flush()
    return user


# TODO: don't bother with the slug, just use numbered users
def _unique_email(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name)
    return f"{slug or 'user'}-{next(_AUTO_NUM)}@test.local"


def create_users(session: sa_orm.Session, *, n: int) -> list[models.User]:
    """Create ``n`` users with auto-incrementing name/email, default attributes otherwise.

    Call `:func:`create_user()` for more configurable user creation.
    """
    users = []
    for _ in range(n):
        i = next(_AUTO_NUM)
        user = models.User(
            name=f"User{i}",
            email=f"user{i}@test.local",
            is_admin=False,
            is_confirmed=True,
        )
        user._password = UNUSABLE_PASSWORD
        session.add(user)
        users.append(user)
    session.flush()
    return users


def create_review(
    session: sa_orm.Session,
    *,
    name: str = "Test Review",
    description: t.Optional[str] = None,
    status: str = "active",
    citation_reviewer_num_pcts: t.Optional[list[dict[str, int]]] = None,
    fulltext_reviewer_num_pcts: t.Optional[list[dict[str, int]]] = None,
) -> models.Review:
    """Create a review; a model event listener also inserts its empty review plan.

    Reviewer percentage lists default to a single 100% option so ``Review.after_update``
    listener's random choices are degenerate => tests are deterministic unless overridden.

    Args:
        session
        name: Review name.
        description: Review description.
        status: Review status: "active" or "frozen".
        citation_reviewer_num_pcts: Number-of-reviewers options for citation screening.
        fulltext_reviewer_num_pcts: Number-of-reviewers options for fulltext screening.
    """
    review = models.Review(
        name=name,
        description=description,
        status=status,
        citation_reviewer_num_pcts=citation_reviewer_num_pcts or DEFAULT_REVIEWER_PCTS,
        fulltext_reviewer_num_pcts=fulltext_reviewer_num_pcts or DEFAULT_REVIEWER_PCTS,
    )
    session.add(review)
    session.flush()
    return review


def create_reviews(session: sa_orm.Session, *, n: int) -> list[models.Review]:
    """Create ``n`` reviews with auto-incrementing name, default attributes otherwise.

    Call `:func:`create_review()` for more configurable review creation.
    """
    reviews = []
    for _ in range(n):
        i = next(_AUTO_NUM)
        review = models.Review(
            name=f"Review{i}",
            description=None,
            status="active",
            citation_reviewer_num_pcts=DEFAULT_REVIEWER_PCTS,
            fulltext_reviewer_num_pcts=DEFAULT_REVIEWER_PCTS,
        )
        session.add(review)
        reviews.append(review)
    session.flush()
    return reviews


def add_review_user(
    session: sa_orm.Session,
    review: models.Review,
    user: models.User,
    role: str = "member",
) -> models.ReviewUserAssoc:
    """Associate a user with a review, as an owner or member."""
    assoc = models.ReviewUserAssoc(review, user, role)
    session.add(assoc)
    session.flush()
    return assoc


def update_review_plan(
    session: sa_orm.Session, review: models.Review, **fields: t.Any
) -> models.ReviewPlan:
    """Set fields on a review's auto-created plan, then flush.

    ``Review`` insert already created the plan (w/ same id) via a model listener;
    this helper makes that dependency explicit and fails loudly if it ever goes
    away, instead of leaving every caller to re-derive it.

    Example:
        update_review_plan(
            session,
            review,
            objective="OBJECTIVE",
            pico={"population": "POPULATION"},
            keyterms={"term1": ["TERM1"]},
        )
    """
    plan = session.get(models.ReviewPlan, review.id)
    if plan is None:
        raise LookupError(
            f"no review plan for review {review.id}: the Review after-insert "
            "listener did not run (or no longer creates plans)"
        )
    for name, value in fields.items():
        setattr(plan, name, value)
    session.flush()
    return plan


def create_data_source(
    session: sa_orm.Session,
    *,
    source_type: str = "database",
    source_name: t.Optional[str] = None,
    source_url: t.Optional[str] = None,
) -> models.DataSource:
    """Create a data source; the (type, name, url) triple is unique-constrained."""
    data_source = models.DataSource(
        source_type=source_type,
        source_name=source_name or f"source-{next(_AUTO_NUM)}",
        source_url=source_url,
    )
    session.add(data_source)
    session.flush()
    return data_source


def create_import(
    session: sa_orm.Session,
    review: models.Review,
    *,
    user: t.Optional[models.User] = None,
    data_source: t.Optional[models.DataSource] = None,
    record_type: str = "citation",
    num_records: int = 1,
    status: str = "not_screened",
) -> models.Import:
    """Create an import record for a review."""
    import_record = models.Import(
        review_id=review.id,
        user_id=user.id if user is not None else None,
        data_source_id=data_source.id if data_source is not None else None,
        record_type=record_type,
        num_records=num_records,
        status=status,
    )
    session.add(import_record)
    session.flush()
    return import_record


def create_study(
    session: sa_orm.Session,
    review: models.Review,
    *,
    user: t.Optional[models.User] = None,
    data_source: t.Optional[models.DataSource] = None,
    citation: t.Optional[dict[str, t.Any]] = None,
    fulltext: t.Optional[dict[str, t.Any]] = None,
    tags: t.Optional[list[str]] = None,
    num_citation_reviewers: int = 1,
    num_fulltext_reviewers: int = 1,
) -> models.Study:
    """Create a study in a review, optionally with fulltext and tags.

    Args:
        session
        review: Review the study belongs to.
        user: User who uploaded the study, if any.
        data_source: Source the study came from, if any.
        citation: Full citation dict; a minimal journal-style citation is generated
            with a unique title, when omitted.
        fulltext: Fulltext dict; no fulltext when omitted. On-disk files must be stored
            separately via :func:`store_fulltext_file()`.
        tags: Tag strings for the study.
        num_citation_reviewers: Number of reviewers assigned at citation stage.
        num_fulltext_reviewers: Number of reviewers assigned at fulltext stage.
    """
    study = models.Study(
        review_id=review.id,
        user_id=user.id if user is not None else None,
        data_source_id=data_source.id if data_source is not None else None,
        citation=citation if citation is not None else _default_citation(),
        fulltext=fulltext,
        tags=tags,
        num_citation_reviewers=num_citation_reviewers,
        num_fulltext_reviewers=num_fulltext_reviewers,
    )
    session.add(study)
    session.flush()
    return study


def _default_citation() -> dict[str, t.Any]:
    """Return a minimal, valid journal-style citation with a unique title."""
    return {
        "type_of_reference": "journal",
        "title": f"Test Study {next(_AUTO_NUM)}",
        "abstract": "Test abstract.",
        "pub_year": 2026,
        "authors": ["Lastname, Firstname"],
        "keywords": [],
        "journal_name": "Journal of Test Studies",
        "language": "English",
        "other_fields": {},
    }


def create_screening(
    session: sa_orm.Session,
    study: models.Study,
    *,
    user: models.User,
    stage: str = "citation",
    status: str = "included",
    exclude_reasons: t.Optional[list[str]] = None,
) -> models.Screening:
    """Create a screening; a model event listener recomputes the study status.

    The listener writes the study's status columns with a Core UPDATE, so the in-session
    ``study`` is expired before this returns: callers always read a fresh
    ``citation_status``/``fulltext_status``.

    Args:
        session
        study: Study being screened.
        user: Reviewer whose decision this is.
        stage: "citation" or "fulltext".
        status: Screening decision.
        exclude_reasons: Reasons, when the status is an exclusion.

    Raises:
        ValueError: If ``stage == "fulltext"`` but the study's citation status is not
            "included". The listener deletes fulltext screenings when a citation stage
            recomputes to anything else, but it doesn't clean up a fulltext row created
            afterwards, so the factory refuses to build that state. Screen the citation
            first, and for multi-reviewer studies resolve every citation decision
            *before* screening the fulltext stage.

    NOTE: (user, review, study, stage) is unique per screening.
    """
    if stage == "fulltext" and study.citation_status != "included":
        raise ValueError(
            f"can't create a fulltext screening for study {study.id}: "
            f"citation_status is {study.citation_status!r}, not 'included'"
        )
    screening = models.Screening(
        user_id=user.id,
        review_id=study.review_id,
        study_id=study.id,
        stage=stage,
        status=status,
        exclude_reasons=exclude_reasons,
    )
    session.add(screening)
    session.flush()
    session.expire(study)  # the listener's Core UPDATE is invisible to the ORM
    return screening


def create_review_with_team(
    session: sa_orm.Session,
    *,
    owner: models.User,
    members: Sequence[models.User] = (),
    **review_kwargs: t.Any,
) -> models.Review:
    """Create a review and associate an owner plus optional members."""
    review = create_review(session, **review_kwargs)
    add_review_user(session, review, owner, role="owner")
    for member in members:
        add_review_user(session, review, member, role="member")
    return review


def create_screened_review(
    session: sa_orm.Session,
    *,
    owner: models.User,
    studies: dict[str, dict[str, t.Any]],
    decisions: Sequence[
        tuple[str, t.Optional[models.User], str, str, t.Optional[list[str]]]
    ] = (),
    screening_reviewer: t.Optional[models.User] = None,
    **review_kwargs: t.Any,
) -> tuple[models.Review, dict[str, models.Study]]:
    """Create a review, its labeled studies, and their screenings in one call.

    The single decision-table shape for the whole suite. Rows address studies by label,
    never by position, so reordering ``studies`` can't silently screen the wrong study.

    Args:
        session
        owner: User to associate with the review as owner.
        studies: ``{label: create_study kwargs}``, with the review automatically injected.
        decisions: Rows of ``(label, user, stage, status, exclude_reasons)``,
            applied in order. Pass None as ``user`` to use ``screening_reviewer``.
            Citation rows must precede any fulltext row for the same study, which in turn
            requires an included citation stage -- see :func:`create_screening()`.
        screening_reviewer: Default reviewer for rows whose ``user`` is None.
        review_kwargs: Extra keyword arguments for :func:`create_review()`.

    Returns:
        The created review, and its ``{label: study}`` mapping.

    Raises:
        ValueError: If a decision row resolves to no user at all.

    Example:
        review, studies = create_screened_review(
            session,
            owner=owner,
            studies={
                "s1": {"tags": ["TAG1"], "citation": CITATION_1, "fulltext": FULLTEXT_1},
                "s2": {"tags": ["TAG2"], "citation": CITATION_2},
            },
            screening_reviewer=reviewer,
            decisions=[
                ("s1", None, "citation", "included", None),
                ("s1", None, "fulltext", "included", None),
                ("s2", None, "citation", "excluded", ["REASON1"]),
            ],
        )
    """
    review = create_review(session, **review_kwargs)
    add_review_user(session, review, owner, role="owner")
    created = {
        label: create_study(session, review, **kwargs)
        for label, kwargs in studies.items()
    }
    for label, user, stage, status, exclude_reasons in decisions:
        reviewer = user if user is not None else screening_reviewer
        if reviewer is None:
            raise ValueError(
                f"decision for {label!r} has no user and no screening_reviewer"
            )
        create_screening(
            session,
            created[label],
            user=reviewer,
            stage=stage,
            status=status,
            exclude_reasons=exclude_reasons,
        )
    return review, created


def store_fulltext_file(
    app: flask.Flask,
    review_id: int,
    filename: str,
    # TODO: should filename be uniquely generated, like user emails and such?
    source_filename: str = "example-journal.pdf",
) -> None:
    """Copy a fixture PDF into the app's fulltext uploads dir for a review.

    Intentionally takes ``app`` rather than ``session`` -- this touches the filesystem,
    not the database. Kept next to the DB factories because the DB and the on-disk file
    must agree (``db_empty``/``db_seeded`` clear the uploads dir on setup, so nothing here
    leaks into another world).
    """
    src_file = (
        pathlib.Path(__file__).parent / "fixtures" / "fulltexts" / source_filename
    )
    tgt_file = os.path.join(
        app.config["FULLTEXT_UPLOADS_DIR"], str(review_id), filename
    )
    fs = app.extensions["filesystem"]
    fs.makedirs(os.path.dirname(tgt_file), exist_ok=True)
    fs.put_file(src_file, tgt_file)
