import bcrypt
import os

from flask_sqlalchemy import SQLAlchemy
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          BadSignature, SignatureExpired)
from sqlalchemy import text, ForeignKey
from sqlalchemy.dialects import postgresql


db = SQLAlchemy()


# association table for users-reviews many-to-many relationship
users_reviews = db.Table(
    'users_to_reviews',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    db.Column('review_id', db.Integer, db.ForeignKey('reviews.id'), index=True)
    )


class User(db.Model):

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
        db.Unicode(length=60), nullable=False)

    # relationships
    owned_reviews = db.relationship(
        'Review', back_populates='owner',
        lazy='dynamic')
    reviews = db.relationship(
        'Review', secondary=users_reviews, back_populates='collaborators',
        lazy='dynamic')

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = self.hash_password(password).decode('utf8')

    def __repr__(self):
        return "<User(id='{}')>".format(self.id)

    def generate_auth_token(self, expiration=1800):
        """
        Generate an authentication token for user that automatically expires
        after ``expiration`` seconds.
        """
        s = Serializer(os.environ['COLANDR_SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    def verify_password(self, plaintext_password):
        if isinstance(plaintext_password, str):
            plaintext_password = plaintext_password.encode('utf8')
        return bcrypt.checkpw(plaintext_password, self.password.encode('utf8'))

    @staticmethod
    def hash_password(plaintext_password, rounds=12):
        if isinstance(plaintext_password, str):
            plaintext_password = plaintext_password.encode('utf8')
        return bcrypt.hashpw(plaintext_password, bcrypt.gensalt(rounds=rounds))

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(os.environ['COLANDR_SECRET_KEY'])
        try:
            data = s.loads(token)
        except (SignatureExpired, BadSignature):
            return None  # valid token, but expired OR invalid token
        user = User.query.get(data['id'])
        return user


class Review(db.Model):

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
    status = db.Column(
        db.Unicode(length=25), server_default='active', nullable=False)
    owner_user_id = db.Column(
        db.Integer, ForeignKey('users.id', ondelete='CASCADE'),
        index=True)
    num_citation_screening_reviewers = db.Column(
        db.SmallInteger, server_default=text('1'), nullable=False)
    num_fulltext_screening_reviewers = db.Column(
        db.SmallInteger, server_default=text('1'), nullable=False)

    # relationships
    owner = db.relationship(
        'User', foreign_keys=[owner_user_id], back_populates='owned_reviews',
        lazy='select')
    collaborators = db.relationship(
        'User', secondary=users_reviews, back_populates='reviews',
        lazy='dynamic')
    review_plan = db.relationship(
        'ReviewPlan', uselist=False, back_populates='review',
        lazy='select')
    studies = db.relationship(
        'Study', back_populates='review',
        lazy='dynamic')

    def __init__(self, name, description=None, status=None, owner_user_id=None,
                 num_citation_screening_reviewers=None,
                 num_fulltext_screening_reviewers=None):
        self.name = name
        self.description = description
        self.status = status
        self.owner_user_id = owner_user_id
        self.num_citation_screening_reviewers = num_citation_screening_reviewers
        self.num_fulltext_screening_reviewers = num_fulltext_screening_reviewers

    def __repr__(self):
        return "<Review(id='{}')>".format(self.id)


class ReviewPlan(db.Model):

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
    data_extraction_form = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='review_plan',
        lazy='select')

    def __init__(self, objective, research_questions, pico, keyterms,
                 selection_criteria, data_extraction_form):
        self.objective = objective
        self.research_questions = research_questions
        self.pico = pico
        self.keyterms = keyterms
        self.selection_criteria = selection_criteria
        self.data_extraction_form = data_extraction_form

    def __repr__(self):
        return "<ReviewPlan(review_id='{}')>".format(self.review_id)


class Study(db.Model):

    __tablename__ = 'studies'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        index=True)
    title = db.Column(
        db.Unicode(length=250), nullable=False,
        server_default='untitled')
    tags = db.Column(
        postgresql.ARRAY(db.Unicode(length=25)), server_default='{}',
        index=True)
    status = db.Column(
        db.Unicode(length=20), nullable=False, server_default='pending',
        index=True)
    deduplication = db.Column(postgresql.JSONB(none_as_null=True))
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

    def __init__(self, review_id, title=None):
        self.review_id = review_id
        if title is not None:
            self.title = title

    def __repr__(self):
        return "<Study(id='{}')>".format(self.id)


class Citation(db.Model):

    __tablename__ = 'citations'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    study_id = db.Column(
        db.BigInteger, ForeignKey('studies.id', ondelete='CASCADE'),
        index=True)
    type_of_work = db.Column(db.Unicode(length=25))
    title = db.Column(db.Unicode(length=250))
    secondary_title = db.Column(db.Unicode(length=250))
    abstract = db.Column(db.UnicodeText)
    pub_year = db.Column(db.SmallInteger)
    pub_month = db.Column(db.SmallInteger)
    authors = db.Column(
        postgresql.ARRAY(db.Unicode(length=100)))
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

    def __init__(self, study_id,
                 type_of_work=None, title=None, secondary_title=None, abstract=None,
                 pub_year=None, pub_month=None, authors=None, keywords=None,
                 type_of_reference=None, journal_name=None, volume=None,
                 issue_number=None, doi=None, issn=None, publisher=None,
                 language=None, other_fields=None):
        self.study_id = study_id
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
        return "<Citation(study_id='{}')>".format(self.study_id)


class Fulltext(db.Model):

    __tablename__ = 'fulltexts'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    study_id = db.Column(
        db.BigInteger, ForeignKey('studies.id', ondelete='CASCADE'),
        index=True)
    content = db.Column(
        db.UnicodeText, nullable=False)
    filename = db.Column(db.UnicodeText)
    extracted_info = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    study = db.relationship(
        'Study', foreign_keys=[study_id], back_populates='fulltext',
        lazy='select')

    def __init__(self, content, filename=None, extracted_info=None):
        self.content = content
        self.filename = filename
        self.extracted_info = extracted_info

    def __repr__(self):
        return "<Fulltext(study_id='{}')>".format(self.study_id)
