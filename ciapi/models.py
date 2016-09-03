from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import text, ForeignKey
from sqlalchemy.dialects import postgresql


db = SQLAlchemy()


class CRUD(object):
    """
    Class to add, update and delete data via SQLALchemy session.
    """

    def add(self, resource):
        db.session.add(resource)
        return db.session.commit()

    def update(self):
        return db.session.commit()

    def delete(self, resource):
        db.session.delete(resource)
        return db.session.commit()


# association table for users-reviews many-to-many relationship
users_reviews = db.Table(
    'users_to_reviews',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    db.Column('review_id', db.Integer, db.ForeignKey('reviews.id'), index=True)
    )


class User(db.Model, CRUD):

    __tablename__ = 'users'

    # columns
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    name = db.Column(
        db.Unicode(length=200), nullable=False)
    email = db.Column(
        db.Unicode(length=200), unique=True, nullable=False,
        index=True)
    password = db.Column(
        db.Unicode, nullable=False)

    # relationships
    owned_reviews = db.relationship(
        'Review', back_populates='owner_user',
        lazy='dynamic')
    reviews = db.relationship(
        'Review', secondary=users_reviews, back_populates='users',
        lazy='dynamic')

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

    def __repr__(self):
        return "<User(id='{}')>".format(self.id)


class Review(db.Model, CRUD):

    __tablename__ = 'reviews'

    # columns
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    name = db.Column(
        db.Unicode(length=500), nullable=False)
    description = db.Column(db.UnicodeText)
    settings = db.Column(
        postgresql.JSONB(none_as_null=True), nullable=False,
        server_default='{}')
    owner_user_id = db.Column(
        db.Integer, ForeignKey('users.id', ondelete='CASCADE'),
        index=True)

    # relationships
    owner_user = db.relationship(
        'User', foreign_keys=[owner_user_id], back_populates='owned_reviews',
        lazy='select')
    users = db.relationship(
        'User', secondary=users_reviews, back_populates='reviews',
        lazy='select')
    review_plan = db.relationship(
        'ReviewPlan', uselist=False, back_populates='review',
        lazy='select')
    studies = db.relationship(
        'Study', back_populates='review',
        lazy='dynamic')

    def __init__(self, name, description, settings, user_ids, owner_user_id):
        self.name = name
        self.description = description
        self.settings = settings
        self.user_ids = user_ids
        self.owner_user_id = owner_user_id

    def __repr__(self):
        return "<Review(id='{}')>".format(self.id)


class ReviewPlan(db.Model, CRUD):

    __tablename__ = 'review_plans'

    # columns
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        index=True)
    objective = db.Column(db.UnicodeText)
    research_questions = db.Column(postgresql.JSONB(none_as_null=True))
    pico = db.Column(postgresql.JSONB(none_as_null=True))
    keyterms = db.Column(postgresql.JSONB(none_as_null=True))
    selection_criteria = db.Column(postgresql.JSONB(none_as_null=True))
    extraction_form = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='review_plan',
        lazy='select')

    def __init__(self, objective, research_questions, pico, keyterms,
                 selection_criteria, extraction_form):
        self.objective = objective
        self.research_questions = research_questions
        self.pico = pico
        self.keyterms = keyterms
        self.selection_criteria = selection_criteria
        self.extraction_form = extraction_form

    def __repr__(self):
        return "<ReviewPlan(review_id='{}')>".format(self.review_id)


class Study(db.Model, CRUD):

    __tablename__ = 'studies'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        index=True)
    citation_id = db.Column(
        db.BigInteger, ForeignKey('citations.id'),
        index=True)
    fulltext_id = db.Column(
        db.BigInteger, ForeignKey('fulltexts.id'),
        index=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    title = db.Column(
        db.Unicode(length=250), nullable=False,
        server_default='untitled')
    status = db.Column(
        db.Unicode(length=20), nullable=False, server_default='pending',
        index=True)
    exclude_reason = db.Column(db.Unicode(length=20))
    tags = db.Column(postgresql.ARRAY(db.Unicode(length=25)))
    duplication = db.Column(postgresql.JSONB(none_as_null=True))
    citation_screening = db.Column(postgresql.JSONB(none_as_null=True))
    fulltext_screening = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='studies',
        lazy='select')
    citation = db.relationship(
        'Citation', uselist=False, back_populates='study',
        lazy='select')
    fulltext = db.relationship(
        'Fulltext', uselist=False, back_populates='study',
        lazy='select')

    def __init__(self, review_id, citation_id, title=None):
        self.review_id = review_id
        self.citation_id = citation_id
        if title is not None:
            self.title = title

    def __repr__(self):
        return "<Study(id='{}')>".format(self.id)


class Citation(db.Model, CRUD):

    __tablename__ = 'citations'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    study_id = db.Column(
        db.BigInteger, ForeignKey('studies.id', ondelete='CASCADE'),
        index=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    type_of_work = db.Column(db.Unicode(length=25))
    title = db.Column(db.Unicode(length=250))
    secondary_title = db.Column(db.Unicode(length=250))
    pub_year = db.Column(db.SmallInteger)
    pub_month = db.Column(db.SmallInteger)
    authors = db.Column(
        postgresql.ARRAY(db.Unicode(length=100)))
    abstract = db.Column(db.UnicodeText)
    keywords = db.Column(
        postgresql.ARRAY(db.Unicode(length=100)))
    type_of_reference = db.Column(db.Unicode(length=50))
    journal_name = db.Column(db.Unicode(length=100))
    volume = db.Column(db.Unicode(length=20))
    issue_number = db.Column(db.Unicode(length=20))
    doi = db.Column(db.Unicode(length=100))
    issn = db.Column(db.Unicode(length=20))
    publisher = db.Column(db.Unicode(length=100))
    language = db.Column(db.Unicode(length=50))
    other_fields = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    study = db.relationship(
        'Study', foreign_keys=[study_id], back_populates='citation',
        lazy='select')

    def __init__(self):
        return  # TODO

    def __repr__(self):
        return "<Citation(study_id='{}')>".format(self.study_id)


class Fulltext(db.Model, CRUD):

    __tablename__ = 'fulltexts'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    study_id = db.Column(
        db.BigInteger, ForeignKey('studies.id', ondelete='CASCADE'),
        index=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    filename = db.Column(db.UnicodeText())
    content = db.Column(db.UnicodeText())
    extracted_info = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    study = db.relationship(
        'Study', foreign_keys=[study_id], back_populates='fulltext',
        lazy='select')

    def __init__(self):
        return  # TODO

    def __repr__(self):
        return "<Fulltext(study_id='{}')>".format(self.study_id)
