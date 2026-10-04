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

NOT_FOUND_ID = 999_999


def create_user(
    session: sa_orm.Session,
    *,
    name: t.Optional[str] = None,
    email: t.Optional[str] = None,
    password: t.Optional[str] = None,
    is_admin: bool = False,
    is_confirmed: bool = True,
) -> models.User:
    """Create a user with a unique email address.

    Args:
        session
        name: User's display name, default "User{i}".
        email: User's email address, generated from ``name`` when omitted,
            like "user{i}@test.local".
        password: Plaintext password, hashed via the model's setter.
            When omitted, an unusable sentinel is stored instead.
        is_admin: Whether the user has admin privileges.
        is_confirmed: Whether the user has confirmed their account.
    """
    user = _new_user(
        name=name,
        email=email,
        password=password,
        is_admin=is_admin,
        is_confirmed=is_confirmed,
    )
    session.add(user)
    session.flush()
    return user


def create_users(
    session: sa_orm.Session,
    n: int,
    *,
    names: t.Optional[Sequence[str]] = None,
    emails: t.Optional[Sequence[str]] = None,
) -> list[models.User]:
    """Create ``n`` users with auto-incrementing name/email, default attributes otherwise.

    Each argument is either omitted -- values are generated, one per user --
    or specifies exactly ``n`` values, the i-th of which belongs to the i-th user.
    Call :func:`create_user()` for a single user with more options.
    """
    _names = _to_values(names, n)
    _emails = _to_values(emails, n)
    users = [
        _new_user(name=name, email=email)
        for name, email in zip(_names, _emails, strict=True)
    ]
    session.add_all(users)
    session.flush()
    return users


def _new_user(
    *,
    name: t.Optional[str] = None,
    email: t.Optional[str] = None,
    password: t.Optional[str] = None,
    is_admin: bool = False,
    is_confirmed: bool = True,
) -> models.User:
    """Create a new user without adding it to the session, shared by both single-
    and multi-user creation factories.
    """
    # always auto-increment, to avoid coupling between factory calls
    i = next(_AUTO_NUM)
    if name is None:
        name = f"User{i}"
    if email is None:
        email = _user_email_from_name(name)
    user = models.User(
        name=name, email=email, is_admin=is_admin, is_confirmed=is_confirmed
    )
    if password is None:
        user._password = UNUSABLE_PASSWORD  # sentinel value, skips scrypt
    else:
        user.password = password  # => property setter hashes it
    return user


def _user_email_from_name(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name)
    return f"{slug}@test.local"


def create_review(
    session: sa_orm.Session,
    *,
    name: t.Optional[str] = None,
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
        name: Reviews's display name, default "Review{i}".
        description: Review description.
        status: Review status: "active" or "frozen".
        citation_reviewer_num_pcts: Number-of-reviewers options for citation screening.
        fulltext_reviewer_num_pcts: Number-of-reviewers options for fulltext screening.
    """
    review = _new_review(
        name=name,
        description=description,
        status=status,
        citation_reviewer_num_pcts=citation_reviewer_num_pcts,
        fulltext_reviewer_num_pcts=fulltext_reviewer_num_pcts,
    )
    session.add(review)
    session.flush()
    return review


def create_reviews(
    session: sa_orm.Session,
    n: int,
    *,
    names: t.Optional[Sequence[str]] = None,
) -> list[models.Review]:
    """Create ``n`` reviews with auto-incrementing name, default attributes otherwise.

    Each argument is either omitted, in which case every review gets the default
    (``Review{i}`` name,), or specifies exactly ``n`` values, the i-th of which
    belongs to the i-th review. Call :func:`create_review()` for a single review
    with more options.
    """
    _names = _to_values(names, n)
    reviews = [_new_review(name=name) for name in _names]
    session.add_all(reviews)
    session.flush()
    return reviews


def _new_review(
    *,
    name: t.Optional[str] = None,
    description: t.Optional[str] = None,
    status: str = "active",
    citation_reviewer_num_pcts: t.Optional[list[dict[str, int]]] = None,
    fulltext_reviewer_num_pcts: t.Optional[list[dict[str, int]]] = None,
) -> models.Review:
    """Create a new review without adding it to the session, shared by both single-
    and multi-review creation factories.
    """
    # always auto-increment, to avoid coupling between factory calls
    i = next(_AUTO_NUM)
    if name is None:
        name = f"Review{i}"
    return models.Review(
        name=name,
        description=description,
        status=status,
        citation_reviewer_num_pcts=citation_reviewer_num_pcts or DEFAULT_REVIEWER_PCTS,
        fulltext_reviewer_num_pcts=fulltext_reviewer_num_pcts or DEFAULT_REVIEWER_PCTS,
    )


def add_review_user(
    session: sa_orm.Session,
    review: models.Review,
    user: models.User,
    role: str = "member",
) -> models.ReviewUserAssoc:
    """Associate a user with a review, as an owner or member."""
    assoc = models.ReviewUserAssoc(review, user, user_role=role)
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
    i = next(_AUTO_NUM)
    if source_name is None:
        source_name = f"DataSource{i}"
    data_source = models.DataSource(
        source_type=source_type, source_name=source_name, source_url=source_url
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
    *,
    review: models.Review,
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
        fulltext: Fulltext dict; no fulltext when omitted. Its filename is filled in
            as "{study.id}.pdf" when not given, consistent with the upload endpoints.
            On-disk files must be stored separately via :func:`store_fulltext_file()`.
        tags: Tag strings for the study.
        num_citation_reviewers: Number of reviewers assigned at citation stage.
        num_fulltext_reviewers: Number of reviewers assigned at fulltext stage.
    """
    study = _new_study(
        review=review,
        user=user,
        data_source=data_source,
        citation=citation,
        fulltext=fulltext,
        tags=tags,
        num_citation_reviewers=num_citation_reviewers,
        num_fulltext_reviewers=num_fulltext_reviewers,
    )
    session.add(study)
    session.flush()
    _populate_fulltext_filename(study)
    session.flush()
    return study


def create_studies(
    session: sa_orm.Session,
    n: int,
    *,
    review: models.Review,
    users: t.Optional[Sequence[models.User] | models.User] = None,
    data_sources: t.Optional[Sequence[models.DataSource] | models.DataSource] = None,
    citations: t.Optional[Sequence[dict[str, t.Any]]] = None,
    fulltexts: t.Optional[Sequence[t.Optional[dict[str, t.Any]]]] = None,
    tagss: t.Optional[Sequence[list[str]]] = None,
) -> list[models.Study]:
    """Create ``n`` studies in ``review``, default attributes otherwise.

    Each argument is either omitted, in which case every study gets the default (a
    generated citation; no user, source, fulltext, or tags), or specifies exactly ``n``
    values, the i-th of which belongs to the i-th study; pass None as a study's fulltext
    value to leave it without a fulltext. Call :func:`create_study()`
    for a single study with more options.
    """
    _users = _to_values(users, n)
    _data_sources = _to_values(data_sources, n)
    _citations = _to_values(citations, n)
    _fulltexts = _to_values(fulltexts, n)
    _tagss = _to_values(tagss, n)
    studies = [
        _new_study(
            review=review,
            user=user,
            data_source=data_source,
            citation=citation,
            fulltext=fulltext,
            tags=tags,
        )
        for user, data_source, citation, fulltext, tags in zip(
            _users, _data_sources, _citations, _fulltexts, _tagss, strict=True
        )
    ]
    session.add_all(studies)
    session.flush()
    # study id exists only after flushing, and its fulltext filename is derived from it
    for study in studies:
        _populate_fulltext_filename(study)
    session.flush()
    return studies


def _new_study(
    *,
    review: models.Review,
    user: t.Optional[models.User] = None,
    data_source: t.Optional[models.DataSource] = None,
    citation: t.Optional[dict[str, t.Any]] = None,
    fulltext: t.Optional[dict[str, t.Any]] = None,
    tags: t.Optional[list[str]] = None,
    num_citation_reviewers: int = 1,
    num_fulltext_reviewers: int = 1,
) -> models.Study:
    """Create a new study without adding it to the session, shared by both single-
    and multi-study creation factories.
    """
    # always auto-increment, to avoid coupling between factory calls
    i = next(_AUTO_NUM)
    if citation is None:
        citation = _default_citation(i)
    return models.Study(
        review_id=review.id,
        user_id=user.id if user is not None else None,
        data_source_id=data_source.id if data_source is not None else None,
        citation=citation,
        fulltext=fulltext,
        tags=tags,
        num_citation_reviewers=num_citation_reviewers,
        num_fulltext_reviewers=num_fulltext_reviewers,
    )


def _default_citation(num: int) -> dict[str, t.Any]:
    """Return a minimal, valid journal-style citation with a unique title."""
    return {
        "type_of_reference": "journal",
        "title": f"Test Study {num}",
        "abstract": "Test abstract.",
        "pub_year": 2026,
        "authors": ["Lastname, Firstname"],
        "keywords": [],
        "journal_name": "Journal of Test Studies",
        "language": "English",
        "other_fields": {},
    }


def _populate_fulltext_filename(study: models.Study, ext: str = ".pdf") -> None:
    """Fill in a study's fulltext filename, if it has a fulltext and no name yet."""
    fulltext = study.fulltext
    if not fulltext or fulltext.get("filename"):
        return
    study.fulltext = fulltext | {"filename": f"{study.id}{ext}"}


def create_screening(
    session: sa_orm.Session,
    *,
    study: models.Study,
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
    screening = _new_screening(
        study=study,
        user=user,
        stage=stage,
        status=status,
        exclude_reasons=exclude_reasons,
    )
    session.add(screening)
    session.flush()
    session.expire(study)  # the listener's Core UPDATE is invisible to the ORM
    return screening


def create_screenings(
    session: sa_orm.Session,
    n: int,
    *,
    studies: Sequence[models.Study] | models.Study,
    users: Sequence[models.User] | models.User,
    stages: Sequence[str] | str = "citation",
    statuses: Sequence[str] | str = "included",
    exclude_reasonss: t.Optional[Sequence[list[str]]] = None,
) -> list[models.Screening]:
    _studies = _to_values(studies, n)
    _users = _to_values(users, n)
    _stages = _to_values(stages, n)
    _statuses = _to_values(statuses, n)
    _exclude_reasonss = _to_values(exclude_reasonss, n)
    screenings = [
        create_screening(
            session,
            study=study,
            user=user,
            stage=stage,
            status=status,
            exclude_reasons=exclude_reasons,
        )
        for study, user, stage, status, exclude_reasons in zip(
            _studies, _users, _stages, _statuses, _exclude_reasonss, strict=True
        )
    ]
    return screenings


def _new_screening(
    *,
    study: models.Study,
    user: models.User,
    stage: str = "citation",
    status: str = "included",
    exclude_reasons: t.Optional[list[str]] = None,
) -> models.Screening:
    """Create a new screening without adding it to the session, shared by both single-
    and multi-screening creation factories.
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
    return screening


def create_review_with_team(
    session: sa_orm.Session,
    *,
    owner: models.User,
    members: Sequence[models.User] = (),
    **review_kwargs: t.Any,
) -> models.Review:
    """Create a review and associate an owner plus optional members."""
    review = _new_review(**review_kwargs)
    session.add(review)

    review_users = []
    review_users.append(models.ReviewUserAssoc(review, owner, user_role="owner"))
    for member in members:
        review_users.append(models.ReviewUserAssoc(review, member, user_role="member"))
    session.add_all(review_users)
    session.flush()
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
        label: create_study(session, review=review, **kwargs)
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
            study=created[label],
            user=reviewer,
            stage=stage,
            status=status,
            exclude_reasons=exclude_reasons,
        )
    return review, created


def store_fulltext_file(
    app: flask.Flask, study: models.Study, source_filename: str = "example-journal.pdf"
) -> None:
    """Copy a fixture PDF into the app's fulltext uploads dir for a study.

    Intentionally takes ``app`` rather than ``session`` -- this touches the filesystem,
    not the database. Kept next to the DB factories because the DB and the on-disk file
    must agree (``db_empty``/``db_seeded`` clear the uploads dir on setup, so nothing here
    leaks into another world).

    Review and file name come from ``study`` itself, so the record and the file agree.

    Raises:
        ValueError: If ``study`` has no fulltext, or its fulltext has no filename
            to store a file under
    """
    fulltext = study.fulltext
    if not fulltext or not fulltext.get("filename"):
        raise ValueError(
            f"study {study.id} has no fulltext filename to store a file under; "
            "create it with a fulltext, e.g. create_study(..., fulltext={...})"
        )
    src_file = (
        pathlib.Path(__file__).parent / "fixtures" / "fulltexts" / source_filename
    )
    tgt_file = os.path.join(
        app.config["FULLTEXT_UPLOADS_DIR"], str(study.review_id), fulltext["filename"]
    )
    fs = app.extensions["filesystem"]
    fs.makedirs(os.path.dirname(tgt_file), exist_ok=True)
    fs.put_file(src_file, tgt_file)


_T = t.TypeVar("_T")


@t.overload
def _to_values(value: None, n: int) -> list[None]: ...


@t.overload
def _to_values(value: str, n: int) -> list[str]: ...


@t.overload
def _to_values(value: Sequence[_T], n: int) -> list[_T]: ...


@t.overload
def _to_values(value: _T, n: int) -> list[_T]: ...


def _to_values(value: object, n: int) -> list[object] | Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, str) and len(value) != n:
        raise ValueError(f"expected {n} values, got {len(value)}")

    return (
        [None] * n
        if value is None
        else [value] * n
        if isinstance(value, (str, bytes))
        else list(value)
        if isinstance(value, Sequence)
        else [value] * n
    )
