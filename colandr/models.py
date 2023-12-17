import datetime
import itertools
import logging
from typing import Optional

import sqlalchemy as sa
import werkzeug.security
from sqlalchemy import event as sa_event
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapped_column as mapcol, Mapped as M

from . import tasks, utils
from .extensions import db


LOGGER = logging.getLogger(__name__)


class User(db.Model):
    __tablename__ = "users"

    # columns
    id: M[int] = mapcol(sa.Integer, primary_key=True, autoincrement=True)
    created_at: M[datetime.datetime] = mapcol(
        sa.DateTime(timezone=False),
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated: M[datetime.datetime] = mapcol(
        sa.DateTime(timezone=False),
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    name: M[str] = mapcol(sa.String(length=200))
    email: M[str] = mapcol(sa.String(length=200), unique=True, index=True)
    _password: M[str] = mapcol("password", sa.String(length=256))
    is_confirmed: M[bool] = mapcol(sa.Boolean, server_default=sa.false())
    is_admin: M[bool] = mapcol(sa.Boolean, server_default=sa.false())

    # relationships
    review_user_assoc = db.relationship(
        "ReviewUserAssoc",
        back_populates="user",
        cascade="all, delete",
        lazy="dynamic",
    )
    reviews = association_proxy("review_user_assoc", "review")

    imports = db.relationship(
        "Import", back_populates="user", lazy="dynamic", passive_deletes=True
    )
    studies = db.relationship(
        "Study", back_populates="user", lazy="dynamic", passive_deletes=True
    )
    citation_screenings = db.relationship(
        "CitationScreening", back_populates="user", lazy="dynamic"
    )
    fulltext_screenings = db.relationship(
        "FulltextScreening", back_populates="user", lazy="dynamic"
    )

    def __repr__(self):
        return f"<User(id={self.id})>"

    @property
    def owned_reviews(self) -> list["Review"]:
        return [
            rua.review
            for rua in db.session.execute(
                sa.select(ReviewUserAssoc).filter_by(user_id=self.id, user_role="owner")
            ).scalars()
        ]

    @property
    def password(self):
        """User's (automatically hashed) password."""
        return self._password

    @password.setter
    def password(self, value):
        """Hash and set user password."""
        self._password = self.hash_password(value)

    def check_password(self, password: str) -> bool:
        return werkzeug.security.check_password_hash(self._password, password)

    @staticmethod
    def hash_password(password: str) -> str:
        return werkzeug.security.generate_password_hash(password, method="pbkdf2")


class Review(db.Model):
    __tablename__ = "reviews"

    # columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    name = sa.Column(sa.String(length=500), nullable=False)
    description = sa.Column(sa.Text)
    status = sa.Column(sa.String(length=25), server_default="active", nullable=False)
    num_citation_screening_reviewers = sa.Column(
        sa.SmallInteger, server_default="1", nullable=False
    )
    num_fulltext_screening_reviewers = sa.Column(
        sa.SmallInteger, server_default="1", nullable=False
    )
    num_citations_included = sa.Column(sa.Integer, server_default="0", nullable=False)
    num_citations_excluded = sa.Column(sa.Integer, server_default="0", nullable=False)
    num_fulltexts_included = sa.Column(sa.Integer, server_default="0", nullable=False)
    num_fulltexts_excluded = sa.Column(sa.Integer, server_default="0", nullable=False)

    # relationships
    review_user_assoc = db.relationship(
        "ReviewUserAssoc",
        back_populates="review",
        cascade="all, delete",
        lazy="dynamic",
    )
    users = association_proxy("review_user_assoc", "user")

    review_plan = db.relationship(
        "ReviewPlan",
        uselist=False,
        back_populates="review",
        lazy="select",
        passive_deletes=True,
    )
    imports = db.relationship(
        "Import", back_populates="review", lazy="dynamic", passive_deletes=True
    )
    studies = db.relationship(
        "Study", back_populates="review", lazy="dynamic", passive_deletes=True
    )
    dedupes = db.relationship(
        "Dedupe", back_populates="review", lazy="dynamic", passive_deletes=True
    )
    citations = db.relationship(
        "Citation", back_populates="review", lazy="dynamic", passive_deletes=True
    )
    citation_screenings = db.relationship(
        "CitationScreening",
        back_populates="review",
        lazy="dynamic",
        passive_deletes=True,
    )
    fulltexts = db.relationship(
        "Fulltext", back_populates="review", lazy="dynamic", passive_deletes=True
    )
    fulltext_screenings = db.relationship(
        "FulltextScreening",
        back_populates="review",
        lazy="dynamic",
        passive_deletes=True,
    )
    data_extractions = db.relationship(
        "DataExtraction", back_populates="review", lazy="dynamic", passive_deletes=True
    )

    def __init__(self, name, description=None):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"<Review(id={self.id})>"

    @property
    def owners(self) -> list[User]:
        return [
            rua.user
            for rua in db.session.execute(
                sa.select(ReviewUserAssoc).filter_by(
                    review_id=self.id, user_role="owner"
                )
            ).scalars()
        ]


class ReviewUserAssoc(db.Model):
    __tablename__ = "review_user_assoc"

    review_id = sa.Column(
        sa.Integer, sa.ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = sa.Column(
        sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    user_role = sa.Column(sa.Text, nullable=False, server_default=sa.text("'member'"))
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )

    review = db.relationship("Review", back_populates="review_user_assoc")
    user = db.relationship("User", back_populates="review_user_assoc")

    def __init__(self, review: Review, user: User, user_role: Optional[str] = None):
        self.review = review
        self.user = user
        self.user_role = user_role

    def __repr__(self):
        return f"<ReviewUserAssoc(review_id={self.review_id}, user_id={self.user_id})>"


class ReviewPlan(db.Model):
    __tablename__ = "review_plans"

    # columns
    id = sa.Column(
        sa.BigInteger, sa.ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    objective = sa.Column(sa.Text)
    research_questions = sa.Column(
        postgresql.ARRAY(sa.String(length=300)), server_default="{}"
    )
    pico = sa.Column(postgresql.JSONB(none_as_null=True), server_default="{}")
    keyterms = sa.Column(postgresql.JSONB(none_as_null=True), server_default="{}")
    selection_criteria = sa.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )
    data_extraction_form = sa.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )
    suggested_keyterms = sa.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )

    @hybrid_property
    def boolean_search_query(self):
        if not self.keyterms:
            return ""
        else:
            return utils.get_boolean_search_query(self.keyterms)

    # relationships
    review = db.relationship(
        "Review", foreign_keys=[id], back_populates="review_plan", lazy="select"
    )

    def __init__(
        self,
        id_,
        objective=None,
        research_questions=None,
        pico=None,
        keyterms=None,
        selection_criteria=None,
        data_extraction_form=None,
    ):
        self.id = id_
        self.objective = objective
        self.research_questions = research_questions
        self.pico = pico
        self.keyterms = keyterms
        self.selection_criteria = selection_criteria
        self.data_extraction_form = data_extraction_form

    def __repr__(self):
        return f"<ReviewPlan(review_id={self.id})>"


class DataSource(db.Model):
    __tablename__ = "data_sources"
    __table_args__ = (
        db.UniqueConstraint(
            "source_type", "source_name", name="source_type_source_name_uc"
        ),
    )

    # columns
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    source_type = sa.Column(sa.String(length=20), nullable=False, index=True)
    source_name = sa.Column(sa.String(length=100), index=True)
    source_url = sa.Column(sa.String(length=500))

    @hybrid_property
    def source_type_and_name(self):
        if self.source_name:
            return f"{self.source_type}: {self.source_name}"
        else:
            return self.source_type

    # relationships
    imports = db.relationship(
        "Import", back_populates="data_source", lazy="dynamic", passive_deletes=True
    )
    studies = db.relationship(
        "Study", back_populates="data_source", lazy="dynamic", passive_deletes=True
    )

    def __init__(self, source_type, source_name=None, source_url=None):
        self.source_type = source_type
        self.source_name = source_name
        self.source_url = source_url

    def __repr__(self):
        return f"<DataSource(id={self.id})>"


class Import(db.Model):
    __tablename__ = "imports"

    # columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_source_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    record_type = sa.Column(sa.String(length=10), nullable=False)
    num_records = sa.Column(sa.Integer, nullable=False)
    status = sa.Column(sa.String(length=20), server_default="not_screened")

    # relationships
    review = db.relationship(
        "Review", foreign_keys=[review_id], back_populates="imports", lazy="select"
    )
    user = db.relationship(
        "User", foreign_keys=[user_id], back_populates="imports", lazy="subquery"
    )  # TODO: change to 'selectin' when sqlalchemy>=1.2.0 ?
    data_source = db.relationship(
        "DataSource",
        foreign_keys=[data_source_id],
        back_populates="imports",
        lazy="subquery",
    )  # TODO: change to 'selectin' when sqlalchemy>=1.2.0 ?

    def __init__(
        self, review_id, user_id, data_source_id, record_type, num_records, status=None
    ):
        self.review_id = review_id
        self.user_id = user_id
        self.data_source_id = data_source_id
        self.record_type = record_type
        self.num_records = num_records
        self.status = status

    def __repr__(self):
        return f"<Import(id={self.id})>"


class Study(db.Model):
    __tablename__ = "studies"

    # columns
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tags = sa.Column(
        postgresql.ARRAY(sa.String(length=64)), server_default="{}", index=False
    )
    data_source_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dedupe_status = sa.Column(
        sa.String(length=20), server_default="not_duplicate", nullable=True, index=True
    )
    citation_status = sa.Column(
        sa.String(length=20), server_default="not_screened", nullable=False, index=True
    )
    fulltext_status = sa.Column(
        sa.String(length=20), server_default="not_screened", nullable=False, index=True
    )
    data_extraction_status = sa.Column(
        sa.String(length=20), server_default="not_started", nullable=False, index=True
    )

    # relationships
    user = db.relationship(
        "User", foreign_keys=[user_id], back_populates="studies", lazy="select"
    )
    review = db.relationship(
        "Review", foreign_keys=[review_id], back_populates="studies", lazy="select"
    )
    data_source = db.relationship(
        "DataSource",
        foreign_keys=[data_source_id],
        back_populates="studies",
        lazy="select",
    )
    dedupe = db.relationship(
        "Dedupe",
        uselist=False,
        back_populates="study",
        lazy="joined",
        passive_deletes=True,
    )
    citation = db.relationship(
        "Citation",
        uselist=False,
        back_populates="study",
        lazy="joined",
        passive_deletes=True,
    )
    fulltext = db.relationship(
        "Fulltext",
        uselist=False,
        back_populates="study",
        lazy="joined",
        passive_deletes=True,
    )
    data_extraction = db.relationship(
        "DataExtraction",
        uselist=False,
        back_populates="study",
        lazy="joined",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Study(id={self.id})>"


class Dedupe(db.Model):
    __tablename__ = "dedupes"

    # columns
    id = sa.Column(
        sa.BigInteger, sa.ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duplicate_of = sa.Column(
        sa.BigInteger,
        nullable=True,  # sa.ForeignKey('studies.id', ondelete='SET NULL'),
    )
    duplicate_score = sa.Column(sa.Float, nullable=True)

    # relationships
    study = db.relationship(
        "Study", foreign_keys=[id], back_populates="dedupe", lazy="select"
    )
    review = db.relationship(
        "Review", foreign_keys=[review_id], back_populates="dedupes", lazy="select"
    )

    def __init__(self, id_, review_id, duplicate_of, duplicate_score):
        self.id = id_
        self.review_id = review_id
        self.duplicate_of = duplicate_of
        self.duplicate_score = duplicate_score

    def __repr__(self):
        return f"<Dedupe(study_id={self.id})>"


class Citation(db.Model):
    __tablename__ = "citations"
    # indexing doesn't work here — we'd need to specify the config e.g. 'english'
    # but we can't guarantee that is correct in all cases -- oh well!
    # __table_args__ = (
    #     db.Index('citations_title_fulltext_idx',
    #              db.func.to_tsvector('title'), postgresql_using='gin'),
    #     db.Index('citations_abstract_fulltext_idx',
    #              db.func.to_tsvector('abstract'), postgresql_using='gin'),
    #     )

    # columns
    id = sa.Column(
        sa.BigInteger, sa.ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type_of_work = sa.Column(sa.String(length=25))
    title = sa.Column(sa.String(length=300), server_default="untitled", nullable=False)
    secondary_title = sa.Column(sa.String(length=300))
    abstract = sa.Column(sa.Text)
    pub_year = sa.Column(sa.SmallInteger)
    pub_month = sa.Column(sa.SmallInteger)
    authors = sa.Column(postgresql.ARRAY(sa.String(length=100)))
    keywords = sa.Column(postgresql.ARRAY(sa.String(length=100)))
    type_of_reference = sa.Column(sa.String(length=50))
    journal_name = sa.Column(sa.String(length=100))
    volume = sa.Column(sa.String(length=20))
    issue_number = sa.Column(sa.String(length=20))
    doi = sa.Column(sa.String(length=100))
    issn = sa.Column(sa.String(length=20))
    publisher = sa.Column(sa.String(length=100))
    language = sa.Column(sa.String(length=50))
    other_fields = sa.Column(postgresql.JSONB(none_as_null=True), server_default="{}")
    text_content_vector_rep = sa.Column(postgresql.ARRAY(sa.Float), server_default="{}")

    @hybrid_property
    def text_content(self):
        return "\n\n".join(
            (self.title or "", self.abstract or "", ", ".join(self.keywords or []))
        ).strip()

    @text_content.expression
    def text_content(cls):
        return db.func.concat_ws(
            "\n\n", cls.title, cls.abstract, db.func.array_to_string(cls.keywords, ", ")
        )

    @hybrid_property
    def exclude_reasons(self):
        return sorted(
            set(
                itertools.chain.from_iterable(
                    scrn.exclude_reasons or [] for scrn in self.screenings
                )
            )
        )

    # relationships
    study = db.relationship(
        "Study", foreign_keys=[id], back_populates="citation", lazy="select"
    )
    review = db.relationship(
        "Review", foreign_keys=[review_id], back_populates="citations", lazy="select"
    )
    screenings = db.relationship(
        "CitationScreening",
        back_populates="citation",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __init__(
        self,
        id_,
        review_id,
        type_of_work=None,
        title=None,
        secondary_title=None,
        abstract=None,
        pub_year=None,
        pub_month=None,
        authors=None,
        keywords=None,
        type_of_reference=None,
        journal_name=None,
        volume=None,
        issue_number=None,
        doi=None,
        issn=None,
        publisher=None,
        language=None,
        other_fields=None,
    ):
        self.id = id_
        self.review_id = review_id
        self.type_of_work = type_of_work
        self.title = title
        self.secondary_title = secondary_title
        self.abstract = abstract
        self.pub_year = pub_year
        self.pub_month = pub_month
        self.authors = authors
        self.keywords = keywords
        self.type_of_reference = type_of_reference
        self.journal_name = journal_name
        self.volume = volume
        self.issue_number = issue_number
        self.doi = doi
        self.issn = issn
        self.publisher = publisher
        self.language = language
        self.other_fields = other_fields

    def __repr__(self):
        return f"<Citation(study_id={self.id})>"


class Fulltext(db.Model):
    __tablename__ = "fulltexts"

    # columns
    id = sa.Column(
        sa.BigInteger, sa.ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = sa.Column(sa.String(length=30), unique=True, nullable=True)
    original_filename = sa.Column(sa.String, unique=False, nullable=True)
    text_content = sa.Column(sa.Text, nullable=True)
    text_content_vector_rep = sa.Column(postgresql.ARRAY(sa.Float), server_default="{}")

    @hybrid_property
    def exclude_reasons(self):
        return sorted(
            set(
                itertools.chain.from_iterable(
                    scrn.exclude_reasons or [] for scrn in self.screenings
                )
            )
        )

    # relationships
    study = db.relationship(
        "Study", foreign_keys=[id], back_populates="fulltext", lazy="select"
    )
    review = db.relationship(
        "Review", foreign_keys=[review_id], back_populates="fulltexts", lazy="select"
    )
    screenings = db.relationship(
        "FulltextScreening",
        back_populates="fulltext",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __init__(self, id_, review_id, filename=None, original_filename=None):
        self.id = id_
        self.review_id = review_id
        self.filename = filename
        self.original_filename = original_filename

    def __repr__(self):
        return f"<Fulltext(study_id={self.id})>"


class CitationScreening(db.Model):
    __tablename__ = "citation_screenings"
    __table_args__ = (
        db.UniqueConstraint(
            "review_id", "user_id", "citation_id", name="review_user_citation_uc"
        ),
    )

    # columns
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    citation_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = sa.Column(sa.String(length=20), nullable=False, index=True)
    exclude_reasons = sa.Column(postgresql.ARRAY(sa.String(length=64)), nullable=True)

    # relationships
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="citation_screenings",
        lazy="select",
    )
    review = db.relationship(
        "Review",
        foreign_keys=[review_id],
        back_populates="citation_screenings",
        lazy="select",
    )
    citation = db.relationship(
        "Citation",
        foreign_keys=[citation_id],
        back_populates="screenings",
        lazy="select",
    )

    def __init__(self, review_id, user_id, citation_id, status, exclude_reasons=None):
        self.review_id = review_id
        self.user_id = user_id
        self.citation_id = citation_id
        self.status = status
        self.exclude_reasons = exclude_reasons

    def __repr__(self):
        return f"<CitationScreening(citation_id={self.citation_id})>"


class FulltextScreening(db.Model):
    __tablename__ = "fulltext_screenings"
    __table_args__ = (
        db.UniqueConstraint(
            "review_id", "user_id", "fulltext_id", name="review_user_fulltext_uc"
        ),
    )

    # columns
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fulltext_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("fulltexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = sa.Column(sa.String(length=20), nullable=False, index=True)
    exclude_reasons = sa.Column(postgresql.ARRAY(sa.String(length=64)), nullable=True)

    # relationships
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="fulltext_screenings",
        lazy="select",
    )
    review = db.relationship(
        "Review",
        foreign_keys=[review_id],
        back_populates="fulltext_screenings",
        lazy="select",
    )
    fulltext = db.relationship(
        "Fulltext",
        foreign_keys=[fulltext_id],
        back_populates="screenings",
        lazy="select",
    )

    def __init__(self, review_id, user_id, fulltext_id, status, exclude_reasons=None):
        self.review_id = review_id
        self.user_id = user_id
        self.fulltext_id = fulltext_id
        self.status = status
        self.exclude_reasons = exclude_reasons

    def __repr__(self):
        return f"<FulltextScreening(fulltext_id={self.fulltext_id})>"


class DataExtraction(db.Model):
    __tablename__ = "data_extractions"

    # columns
    id = sa.Column(
        sa.BigInteger, sa.ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = sa.Column(
        sa.DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extracted_items = sa.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )

    # relationships
    study = db.relationship(
        "Study", foreign_keys=[id], back_populates="data_extraction", lazy="select"
    )
    review = db.relationship(
        "Review",
        foreign_keys=[review_id],
        back_populates="data_extractions",
        lazy="select",
    )

    def __init__(self, id_, review_id, extracted_items=None):
        self.id = id_
        self.review_id = review_id
        self.extracted_items = extracted_items

    def __repr__(self):
        return f"<DataExtraction(study_id={self.id})>"


# EVENTS


@sa_event.listens_for(CitationScreening, "after_insert")
@sa_event.listens_for(CitationScreening, "after_delete")
@sa_event.listens_for(CitationScreening, "after_update")
def update_citation_status(mapper, connection, target):
    citation_id = target.citation_id
    review_id = target.review_id
    citation = target.citation
    # TODO(burton): you added this so that conftest populate_db func would work
    # for reasons unknown, the target here didn't have a loaded citation object
    # but this is _probably_ a bad thing, and you should find a way to fix it
    if citation is None:
        citation = db.session.execute(
            sa.select(Citation).filter_by(id=citation_id)
        ).scalar_one_or_none()
    # get the current (soon to be *old*) citation_status of the study
    old_status = connection.execute(
        sa.select(Study.citation_status).where(Study.id == citation_id)
    ).fetchone()[0]
    # now compute the new status, and update the study accordingly
    status = utils.assign_status(
        [
            cs.status
            for cs in db.session.execute(
                sa.select(CitationScreening).filter_by(citation_id=citation_id)
            ).scalars()
        ],
        citation.review.num_citation_screening_reviewers,
    )
    connection.execute(
        sa.update(Study).where(Study.id == citation_id).values(citation_status=status)
    )
    LOGGER.info("%s => %s with status = %s", target, citation, status)
    # we may have to insert or delete a corresponding fulltext record
    fulltext = connection.execute(
        sa.select(Fulltext).where(Fulltext.id == citation_id)
    ).first()
    fulltext_inserted_or_deleted = False
    if status == "included" and fulltext is None:
        connection.execute(
            sa.insert(Fulltext).values(id=citation_id, review_id=review_id)
        )
        LOGGER.info("inserted <Fulltext(study_id=%s)>", citation_id)
        fulltext_inserted_or_deleted = True
    elif status != "included" and fulltext is not None:
        connection.execute(sa.delete(Fulltext).where(Fulltext.id == citation_id))
        LOGGER.info("deleted <Fulltext(study_id=%s)>", citation_id)
        fulltext_inserted_or_deleted = True
    # we may have to update our counts for review num_citations_included / excluded
    if old_status != status:
        if old_status == "included":  # decrement num_citations_included
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_citations_included=Review.num_citations_included - 1)
            )
        elif status == "included":  # increment num_citations_included
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_citations_included=Review.num_citations_included + 1)
            )
        elif old_status == "excluded":  # decrement num_citations_excluded
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_citations_included=Review.num_citations_excluded - 1)
            )
        elif status == "excluded":  # increment num_citations_excluded
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_citations_included=Review.num_citations_excluded + 1)
            )
    if fulltext_inserted_or_deleted is True:
        status_counts = connection.execute(
            sa.select(
                Review.num_citations_included, Review.num_citations_excluded
            ).where(Review.id == review_id)
        ).fetchone()
        LOGGER.info(
            "<Review(id=%s)> citation_status counts = %s", review_id, status_counts
        )
        n_included, n_excluded = status_counts
        # if at least 25 citations have been included AND excluded
        # and only once every 25 included citations
        # (re-)compute the suggested keyterms
        if n_included >= 25 and n_excluded >= 25 and n_included % 25 == 0:
            sample_size = min(n_included, n_excluded)
            tasks.suggest_keyterms.apply_async(args=[review_id, sample_size])
        # if at least 100 citations have been included AND excluded
        # and only once every 50 included citations
        # (re-)train a citation ranking model
        if n_included >= 100 and n_excluded >= 100 and n_included % 50 == 0:
            tasks.train_citation_ranking_model.apply_async(args=[review_id])


@sa_event.listens_for(FulltextScreening, "after_insert")
@sa_event.listens_for(FulltextScreening, "after_delete")
@sa_event.listens_for(FulltextScreening, "after_update")
def update_fulltext_status(mapper, connection, target):
    fulltext_id = target.fulltext_id
    review_id = target.review_id
    fulltext = target.fulltext
    # TODO(burton): you added this so that conftest populate_db func would work
    # for reasons unknown, the target here didn't have a loaded fulltext object
    # but this is _probably_ a bad thing, and you should find a way to fix it
    if fulltext is None:
        fulltext = db.session.execute(
            sa.select(Fulltext).filter_by(id=fulltext_id)
        ).scalar_one_or_none()
    # get the current (soon to be *old*) citation_status of the study
    old_status = connection.execute(
        sa.select(Study.fulltext_status).where(Study.id == fulltext_id)
    ).fetchone()[0]
    # now compute the new status, and update the study accordingly
    status = utils.assign_status(
        [
            fs.status
            for fs in db.session.execute(
                sa.select(FulltextScreening).filter_by(fulltext_id=fulltext_id)
            ).scalars()
        ],
        fulltext.review.num_fulltext_screening_reviewers,
    )
    connection.execute(
        sa.update(Study).where(Study.id == fulltext_id).values(fulltext_status=status)
    )
    LOGGER.info("%s => %s with status = %s", target, fulltext, status)
    # we may have to insert or delete a corresponding data extraction record
    data_extraction = connection.execute(
        sa.select(DataExtraction).where(DataExtraction.id == fulltext_id)
    ).first()
    # data_extraction_inserted_or_deleted = False
    if status == "included" and data_extraction is None:
        connection.execute(
            sa.insert(DataExtraction).values(id=fulltext_id, review_id=review_id)
        )
        LOGGER.info("inserted <DataExtraction(study_id=%s)>", fulltext_id)
        # data_extraction_inserted_or_deleted = True
    elif status != "included" and data_extraction is None:
        connection.execute(
            sa.delete(DataExtraction).where(DataExtraction.id == fulltext_id)
        )
        LOGGER.info("deleted <DataExtraction(study_id=%s)>", fulltext_id)
        # data_extraction_inserted_or_deleted = True
    # we may have to update our counts for review num_fulltexts_included / excluded
    if old_status != status:
        if old_status == "included":  # decrement num_fulltexts_included
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_fulltexts_included=Review.num_fulltexts_included - 1)
            )
        elif status == "included":  # increment num_fulltexts_included
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_fulltexts_included=Review.num_fulltexts_included + 1)
            )
        elif old_status == "excluded":  # decrement num_fulltexts_excluded
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_fulltexts_included=Review.num_fulltexts_included - 1)
            )
        elif status == "excluded":  # increment num_fulltexts_excluded
            connection.execute(
                sa.update(Review)
                .where(Review.id == review_id)
                .values(num_fulltexts_included=Review.num_fulltexts_included + 1)
            )
    # TODO: should we do something now?
    # if data_extraction_inserted_or_deleted is True:
    #     with connection.begin():
    #         status_counts = connection.execute(
    #             sa.select(Review.num_fulltexts_included, Review.num_fulltexts_excluded)\
    #             .where(Review.id == review_id)
    #             ).fetchone()
    #         LOGGER.info(
    #             '<Review(id=%s)> fulltext_status counts = %s',
    #             review_id, status_counts)
    #         n_included, n_excluded = status_counts


@sa_event.listens_for(Review, "after_insert")
def insert_review_plan(mapper, connection, target):
    review_plan = ReviewPlan(target.id)
    connection.execute(sa.insert(ReviewPlan).values(id=target.id))
    LOGGER.info("inserted %s and %s", target, review_plan)
