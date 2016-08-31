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
        server_default=text("(CURRENT_TIMESTAMP(0) AT TIME ZONE 'UTC')"))
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
        server_default=text("(CURRENT_TIMESTAMP(0) AT TIME ZONE 'UTC')"))
    name = db.Column(
        db.Unicode(length=500), nullable=False)
    description = db.Column(db.UnicodeText)
    settings = db.Column(
        postgresql.JSONB(none_as_null=True), nullable=False)
    owner_user_id = db.Column(
        db.Integer, ForeignKey('users.id', ondelete='CASCADE'),
        index=True)

    # relationships
    owner_user = db.relationship(
        'User', foreign_keys=[owner_user_id], back_populates='owned_reviews',
        lazy='select')
    users = db.relationship(
        'User', secondary=users_reviews, back_populates='reviews',
        lazy='dynamic')
    review_plan = db.relationship(
        'ReviewPlan', uselist=False, back_populates='review',
        lazy='select')
    citations = db.relationship(
        'Citation', back_populates='review',
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
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        index=True)
    objective = db.Column(db.UnicodeText)
    research_questions = db.Column(postgresql.JSONB(none_as_null=True))
    pico = db.Column(postgresql.JSONB(none_as_null=True))
    keyterms = db.Column(postgresql.JSONB(none_as_null=True))
    selection_criteria = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='review_plan',
        lazy='select')

    def __init__(self, objective, research_questions, pico, keyterms, selection_criteria):
        self.objective = objective
        self.research_questions = research_questions
        self.pico = pico
        self.keyterms = keyterms
        self.selection_criteria = selection_criteria

    def __repr__(self):
        return "<ReviewPlan(review_id='{}')>".format(self.review_id)


class Citation(db.Model, CRUD):

    __tablename__ = 'citations'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        index=True)
    user_id = db.Column(
        db.Integer, ForeignKey('users.id'))
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP(0) AT TIME ZONE 'UTC')"))
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
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='citations',
        lazy='select')
    status = db.relationship(
        'CitationStatus', uselist=False, back_populates='citation',
        lazy='select')

    # TODO: init method
#     def __init__(self, objective, research_questions, pico, keyterms, selection_criteria):
#         self.objective = objective
#         self.research_questions = research_questions
#         self.pico = pico
#         self.keyterms = keyterms
#         self.selection_criteria = selection_criteria

    def __repr__(self):
        return "<Citation(id='{}')>".format(self.id)


class CitationStatus(db.Model, CRUD):

    __tablename__ = 'citation_statuses'

    # columns
    citation_id = db.Column(
        db.BigInteger, ForeignKey('citations.id', ondelete='CASCADE'),
        index=True)
    status = db.Column(
        db.Unicode(length=15), nullable=False, index=True)  # default?
    exclude_reason = db.Column(db.Unicode(length=20))
    deduplication = db.Column(postgresql.JSONB(none_as_null=True))
    citation_screening = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    citation = db.relationship(
        'Citation', foreign_keys=[citation_id], back_populates='status',
        lazy='select')

    def __repr__(self):
        return "<CitationStatus(citation_id='{}')>".format(self.citation_id)
