import itertools
import logging

from sqlalchemy import ForeignKey, event, false, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property

from .api.utils import assign_status, get_boolean_search_query
from .extensions import db


logger = logging.getLogger(__name__)


# association table for users-reviews many-to-many relationship
users_reviews = db.Table(
    "users_to_reviews",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), index=True),
    db.Column("review_id", db.Integer, db.ForeignKey("reviews.id"), index=True),
)


class User(db.Model):
    __tablename__ = "users"

    # columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    name = db.Column(db.Unicode(length=200), nullable=False)
    email = db.Column(db.Unicode(length=200), unique=True, nullable=False, index=True)
    password = db.Column(db.Unicode(length=256), nullable=False)
    is_confirmed = db.Column(db.Boolean, nullable=False, server_default=false())
    is_admin = db.Column(db.Boolean, nullable=False, server_default=false())

    # relationships
    owned_reviews = db.relationship(
        "Review", back_populates="owner", lazy="dynamic", passive_deletes=True
    )
    reviews = db.relationship(
        "Review", secondary=users_reviews, back_populates="users", lazy="dynamic"
    )
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
    def identity(self):
        """Unique id of the user instance, required by ``flask-praetorian`` ."""
        return self.id

    @property
    def rolenames(self):
        """Names of roles attached to the user instance, required by ``flask-praetorian`` ."""
        # TODO: actually implement user roles for real in the db model?
        if self.is_admin is True:
            return ["user", "admin"]
        else:
            return ["user"]

    # NOTE: user model already has a password attribute! so we don't need this here
    # @property
    # def password(self):
    #     """Hashed password assigned to the user instance, required by ``flask-praetorian`` ."""
    #     return self.password

    @classmethod
    def lookup(cls, username):
        """
        Look up user in db with given ``username`` (stored as "email" in the db)
        and return it, or None if not found, required by ``flask-praetorian`` .
        """
        return cls.query.filter_by(email=username).one_or_none()

    @classmethod
    def identify(cls, id):
        """
        Identify a single user by their ``id`` and return their user instance,
        or None if not found, required by ``flask-praetorian`` .
        """
        return cls.query.get(id)

    # TODO: figure out if flask praetorian needs this / how uses this
    def is_valid(self):
        # return self.is_confirmed
        return True


class DataSource(db.Model):
    __tablename__ = "data_sources"
    __table_args__ = (
        db.UniqueConstraint(
            "source_type", "source_name", name="source_type_source_name_uc"
        ),
    )

    # columns
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    source_type = db.Column(db.Unicode(length=20), nullable=False, index=True)
    source_name = db.Column(db.Unicode(length=100), index=True)
    source_url = db.Column(db.Unicode(length=500))

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


class Review(db.Model):
    __tablename__ = "reviews"

    # columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    owner_user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.Unicode(length=500), nullable=False)
    description = db.Column(db.UnicodeText)
    status = db.Column(db.Unicode(length=25), server_default="active", nullable=False)
    num_citation_screening_reviewers = db.Column(
        db.SmallInteger, server_default="1", nullable=False
    )
    num_fulltext_screening_reviewers = db.Column(
        db.SmallInteger, server_default="1", nullable=False
    )
    num_citations_included = db.Column(db.Integer, server_default="0", nullable=False)
    num_citations_excluded = db.Column(db.Integer, server_default="0", nullable=False)
    num_fulltexts_included = db.Column(db.Integer, server_default="0", nullable=False)
    num_fulltexts_excluded = db.Column(db.Integer, server_default="0", nullable=False)

    # relationships
    owner = db.relationship(
        "User",
        foreign_keys=[owner_user_id],
        back_populates="owned_reviews",
        lazy="select",
    )
    users = db.relationship(
        "User", secondary=users_reviews, back_populates="reviews", lazy="dynamic"
    )
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

    def __init__(self, name, owner_user_id, description=None):
        self.name = name
        self.owner_user_id = owner_user_id
        self.description = description

    def __repr__(self):
        return f"<Review(id={self.id})>"


class ReviewPlan(db.Model):
    __tablename__ = "review_plans"

    # columns
    id = db.Column(
        db.BigInteger, ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    objective = db.Column(db.UnicodeText)
    research_questions = db.Column(
        postgresql.ARRAY(db.Unicode(length=300)), server_default="{}"
    )
    pico = db.Column(postgresql.JSONB(none_as_null=True), server_default="{}")
    keyterms = db.Column(postgresql.JSONB(none_as_null=True), server_default="{}")
    selection_criteria = db.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )
    data_extraction_form = db.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )
    suggested_keyterms = db.Column(
        postgresql.JSONB(none_as_null=True), server_default="{}"
    )

    @hybrid_property
    def boolean_search_query(self):
        if not self.keyterms:
            return ""
        else:
            return get_boolean_search_query(self.keyterms)

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


class Import(db.Model):
    __tablename__ = "imports"

    # columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_source_id = db.Column(
        db.BigInteger,
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    record_type = db.Column(db.Unicode(length=10), nullable=False)
    num_records = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Unicode(length=20), server_default="not_screened")

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
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tags = db.Column(
        postgresql.ARRAY(db.Unicode(length=64)), server_default="{}", index=False
    )
    data_source_id = db.Column(
        db.Integer,
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dedupe_status = db.Column(
        db.Unicode(length=20), server_default="not_duplicate", nullable=True, index=True
    )
    citation_status = db.Column(
        db.Unicode(length=20), server_default="not_screened", nullable=False, index=True
    )
    fulltext_status = db.Column(
        db.Unicode(length=20), server_default="not_screened", nullable=False, index=True
    )
    data_extraction_status = db.Column(
        db.Unicode(length=20), server_default="not_started", nullable=False, index=True
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

    # TODO: figure out why we have this here, and if we want it
    def __init__(self, user_id, review_id, data_source_id):
        self.user_id = user_id
        self.review_id = review_id
        self.data_source_id = data_source_id

    def __repr__(self):
        return f"<Study(id={self.id})>"


class Dedupe(db.Model):
    __tablename__ = "dedupes"

    # columns
    id = db.Column(
        db.BigInteger, ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duplicate_of = db.Column(
        db.BigInteger, nullable=True  # ForeignKey('studies.id', ondelete='SET NULL'),
    )
    duplicate_score = db.Column(db.Float, nullable=True)

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
    id = db.Column(
        db.BigInteger, ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type_of_work = db.Column(db.Unicode(length=25))
    title = db.Column(db.Unicode(length=300), server_default="untitled", nullable=False)
    secondary_title = db.Column(db.Unicode(length=300))
    abstract = db.Column(db.UnicodeText)
    pub_year = db.Column(db.SmallInteger)
    pub_month = db.Column(db.SmallInteger)
    authors = db.Column(postgresql.ARRAY(db.Unicode(length=100)))
    keywords = db.Column(postgresql.ARRAY(db.Unicode(length=100)))
    type_of_reference = db.Column(db.Unicode(length=50))
    journal_name = db.Column(db.Unicode(length=100))
    volume = db.Column(db.Unicode(length=20))
    issue_number = db.Column(db.Unicode(length=20))
    doi = db.Column(db.Unicode(length=100))
    issn = db.Column(db.Unicode(length=20))
    publisher = db.Column(db.Unicode(length=100))
    language = db.Column(db.Unicode(length=50))
    other_fields = db.Column(postgresql.JSONB(none_as_null=True), server_default="{}")
    text_content_vector_rep = db.Column(postgresql.ARRAY(db.Float), server_default="{}")

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
    id = db.Column(
        db.BigInteger, ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = db.Column(db.Unicode(length=30), unique=True, nullable=True)
    original_filename = db.Column(db.Unicode, unique=False, nullable=True)
    text_content = db.Column(db.UnicodeText, nullable=True)
    text_content_vector_rep = db.Column(postgresql.ARRAY(db.Float), server_default="{}")

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
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    citation_id = db.Column(
        db.BigInteger,
        ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.Unicode(length=20), nullable=False, index=True)
    exclude_reasons = db.Column(postgresql.ARRAY(db.Unicode(length=64)), nullable=True)

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
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fulltext_id = db.Column(
        db.BigInteger,
        ForeignKey("fulltexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.Unicode(length=20), nullable=False, index=True)
    exclude_reasons = db.Column(postgresql.ARRAY(db.Unicode(length=64)), nullable=True)

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
    id = db.Column(
        db.BigInteger, ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    last_updated = db.Column(
        db.TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
        server_onupdate=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extracted_items = db.Column(
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


# tables for citation deduplication


class DedupeBlockingMap(db.Model):
    __tablename__ = "dedupe_blocking_map"

    # columns
    citation_id = db.Column(
        db.BigInteger,
        ForeignKey("citations.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    block_key = db.Column(db.UnicodeText, primary_key=True, nullable=False, index=True)

    def __init__(self, citation_id, review_id, block_key):
        self.citation_id = citation_id
        self.review_id = review_id
        self.block_key = block_key


class DedupePluralKey(db.Model):
    __tablename__ = "dedupe_plural_key"
    __table_args__ = (
        db.UniqueConstraint("review_id", "block_key", name="review_id_block_key_uc"),
    )

    # columns
    block_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_key = db.Column(db.UnicodeText, nullable=False, index=True)

    def __init__(self, block_id, review_id, block_key):
        self.block_id = block_id
        self.review_id = review_id
        self.block_key = block_key


class DedupePluralBlock(db.Model):
    __tablename__ = "dedupe_plural_block"
    # __table_args__ = (
    #     db.UniqueConstraint('block_id', 'citation_id',
    #                         name='block_id_citation_id_uc'),
    #     )

    # columns
    block_id = db.Column(db.BigInteger, primary_key=True)
    citation_id = db.Column(db.BigInteger, primary_key=True, nullable=False, index=True)
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    def __init__(self, block_id, citation_id, review_id):
        self.block_id = block_id
        self.citation_id = citation_id
        self.review_id = review_id


class DedupeCoveredBlocks(db.Model):
    __tablename__ = "dedupe_covered_blocks"

    # columns
    citation_id = db.Column(db.BigInteger, primary_key=True, nullable=False, index=True)
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sorted_ids = db.Column(
        postgresql.ARRAY(db.BigInteger), nullable=False, server_default="{}"
    )

    def __init__(self, citation_id, review_id, sorted_ids):
        self.citation_id = citation_id
        self.review_id = review_id
        self.sorted_ids = sorted_ids


class DedupeSmallerCoverage(db.Model):
    __tablename__ = "dedupe_smaller_coverage"

    # columns
    citation_id = db.Column(db.BigInteger, primary_key=True, nullable=False, index=True)
    review_id = db.Column(
        db.Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    smaller_ids = db.Column(
        postgresql.ARRAY(db.BigInteger), nullable=True, server_default="{}"
    )

    def __init__(self, citation_id, review_id, block_id, smaller_ids):
        self.citation_id = citation_id
        self.review_id = review_id
        self.block_id = block_id
        self.smaller_ids = smaller_ids


# EVENTS


@event.listens_for(CitationScreening, "after_insert")
@event.listens_for(CitationScreening, "after_delete")
@event.listens_for(CitationScreening, "after_update")
def update_citation_status(mapper, connection, target):
    citation_id = target.citation_id
    review_id = target.review_id
    citation = target.citation
    # TODO(burton): you added this so that conftest populate_db func would work
    # for reasons unknown, the target here didn't have a loaded citation object
    # but this is _probably_ a bad thing, and you should find a way to fix it
    if citation is None:
        citation = Citation.query.where(Citation.id == citation_id).one_or_none()
    # get the current (soon to be *old*) citation_status of the study
    with connection.begin():
        old_status = connection.execute(
            db.select([Study.citation_status]).where(Study.id == citation_id)
        ).fetchone()[0]
    # now compute the new status, and update the study accordingly
    status = assign_status(
        [
            cs.status
            for cs in db.session.query(CitationScreening).filter_by(
                citation_id=citation_id
            )
        ],
        citation.review.num_citation_screening_reviewers,
    )
    with connection.begin():
        connection.execute(
            db.update(Study)
            .where(Study.id == citation_id)
            .values(citation_status=status)
        )
    logger.info("%s => %s with status = %s", target, citation, status)
    # we may have to insert or delete a corresponding fulltext record
    with connection.begin():
        fulltext = connection.execute(
            db.select([Fulltext]).where(Fulltext.id == citation_id)
        ).first()
    fulltext_inserted_or_deleted = False
    if status == "included" and fulltext is None:
        with connection.begin():
            connection.execute(
                db.insert(Fulltext).values(id=citation_id, review_id=review_id)
            )
        logger.info("inserted <Fulltext(study_id=%s)>", citation_id)
        fulltext_inserted_or_deleted = True
    elif status != "included" and fulltext is not None:
        with connection.begin():
            connection.execute(db.delete(Fulltext).where(Fulltext.id == citation_id))
        logger.info("deleted <Fulltext(study_id=%s)>", citation_id)
        fulltext_inserted_or_deleted = True
    # we may have to update our counts for review num_citations_included / excluded
    if old_status != status:
        if old_status == "included":  # decrement num_citations_included
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_citations_included=Review.num_citations_included - 1)
                )
        elif status == "included":  # increment num_citations_included
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_citations_included=Review.num_citations_included + 1)
                )
        elif old_status == "excluded":  # decrement num_citations_excluded
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_citations_included=Review.num_citations_excluded - 1)
                )
        elif status == "excluded":  # increment num_citations_excluded
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_citations_included=Review.num_citations_excluded + 1)
                )
    if fulltext_inserted_or_deleted is True:
        with connection.begin():
            status_counts = connection.execute(
                db.select(
                    [Review.num_citations_included, Review.num_citations_excluded]
                ).where(Review.id == review_id)
            ).fetchone()
            logger.info(
                "<Review(id=%s)> citation_status counts = %s", review_id, status_counts
            )
            n_included, n_excluded = status_counts
            # if at least 25 citations have been included AND excluded
            # and only once every 25 included citations
            # (re-)compute the suggested keyterms
            if n_included >= 25 and n_excluded >= 25 and n_included % 25 == 0:
                from .tasks import suggest_keyterms

                sample_size = min(n_included, n_excluded)
                suggest_keyterms.apply_async(args=[review_id, sample_size])
            # if at least 100 citations have been included AND excluded
            # and only once ever 50 included citations
            # (re-)train a citation ranking model
            if n_included >= 100 and n_excluded >= 100 and n_included % 50 == 0:
                from .tasks import train_citation_ranking_model

                train_citation_ranking_model.apply_async(args=[review_id])


@event.listens_for(FulltextScreening, "after_insert")
@event.listens_for(FulltextScreening, "after_delete")
@event.listens_for(FulltextScreening, "after_update")
def update_fulltext_status(mapper, connection, target):
    fulltext_id = target.fulltext_id
    review_id = target.review_id
    fulltext = target.fulltext
    # TODO(burton): you added this so that conftest populate_db func would work
    # for reasons unknown, the target here didn't have a loaded fulltext object
    # but this is _probably_ a bad thing, and you should find a way to fix it
    if fulltext is None:
        fulltext = Fulltext.query.where(Fulltext.id == fulltext_id).one_or_none()
    # get the current (soon to be *old*) citation_status of the study
    with connection.begin():
        old_status = connection.execute(
            db.select([Study.fulltext_status]).where(Study.id == fulltext_id)
        ).fetchone()[0]
    # now compute the new status, and update the study accordingly
    status = assign_status(
        [
            fs.status
            for fs in db.session.query(FulltextScreening).filter_by(
                fulltext_id=fulltext_id
            )
        ],
        fulltext.review.num_fulltext_screening_reviewers,
    )
    with connection.begin():
        connection.execute(
            db.update(Study)
            .where(Study.id == fulltext_id)
            .values(fulltext_status=status)
        )
    logger.info("%s => %s with status = %s", target, fulltext, status)
    # we may have to insert or delete a corresponding data extraction record
    with connection.begin():
        data_extraction = connection.execute(
            db.select([DataExtraction]).where(DataExtraction.id == fulltext_id)
        ).first()
    data_extraction_inserted_or_deleted = False
    if status == "included" and data_extraction is None:
        with connection.begin():
            connection.execute(
                db.insert(DataExtraction).values(id=fulltext_id, review_id=review_id)
            )
        logger.info("inserted <DataExtraction(study_id=%s)>", fulltext_id)
        data_extraction_inserted_or_deleted = True
    elif status != "included" and data_extraction is None:
        with connection.begin():
            connection.execute(
                db.delete(DataExtraction).where(DataExtraction.id == fulltext_id)
            )
        logger.info("deleted <DataExtraction(study_id=%s)>", fulltext_id)
        data_extraction_inserted_or_deleted = True
    # we may have to update our counts for review num_fulltexts_included / excluded
    if old_status != status:
        if old_status == "included":  # decrement num_fulltexts_included
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_fulltexts_included=Review.num_fulltexts_included - 1)
                )
        elif status == "included":  # increment num_fulltexts_included
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_fulltexts_included=Review.num_fulltexts_included + 1)
                )
        elif old_status == "excluded":  # decrement num_fulltexts_excluded
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_fulltexts_included=Review.num_fulltexts_included - 1)
                )
        elif status == "excluded":  # increment num_fulltexts_excluded
            with connection.begin():
                connection.execute(
                    db.update(Review)
                    .where(Review.id == review_id)
                    .values(num_fulltexts_included=Review.num_fulltexts_included + 1)
                )
    # TODO: should we do something now?
    # if data_extraction_inserted_or_deleted is True:
    #     with connection.begin():
    #         status_counts = connection.execute(
    #             db.select([Review.num_fulltexts_included, Review.num_fulltexts_excluded])\
    #             .where(Review.id == review_id)
    #             ).fetchone()
    #         logger.info(
    #             '<Review(id=%s)> fulltext_status counts = %s',
    #             review_id, status_counts)
    #         n_included, n_excluded = status_counts


@event.listens_for(Review, "after_insert")
def insert_review_plan(mapper, connection, target):
    review_plan = ReviewPlan(target.id)
    with connection.begin():
        connection.execute(db.insert(ReviewPlan).values(id=target.id))
    logger.info("inserted %s and %s", target, review_plan)
