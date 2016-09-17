import bcrypt

from flask import current_app
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          BadSignature, SignatureExpired)
from sqlalchemy import text, ForeignKey
from sqlalchemy.dialects import postgresql

from . import db


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
        lazy='dynamic', passive_deletes=True)
    reviews = db.relationship(
        'Review', secondary=users_reviews, back_populates='users',
        lazy='dynamic')
    citation_screenings = db.relationship(
        'CitationScreening', back_populates='user',
        lazy='dynamic')
    fulltext_screenings = db.relationship(
        'FulltextScreening', back_populates='user',
        lazy='dynamic')

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = self.hash_password(password).decode('utf8')

    def __repr__(self):
        return "<User(id={})>".format(self.id)

    def generate_auth_token(self, expiration=1800):
        """
        Generate an authentication token for user that automatically expires
        after ``expiration`` seconds.
        """
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    def verify_password(self, plaintext_password):
        if isinstance(plaintext_password, str):
            plaintext_password = plaintext_password.encode('utf8')
        return bcrypt.checkpw(plaintext_password, self.password.encode('utf8'))

    @staticmethod
    def hash_password(plaintext_password):
        if isinstance(plaintext_password, str):
            plaintext_password = plaintext_password.encode('utf8')
        return bcrypt.hashpw(
            plaintext_password,
            bcrypt.gensalt(rounds=current_app.config['BCRYPT_LOG_ROUNDS']))

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except (SignatureExpired, BadSignature):
            return None  # valid token, but expired OR invalid token
        return db.session.query(User).get(data['id'])


class Review(db.Model):

    __tablename__ = 'reviews'

    # columns
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    owner_user_id = db.Column(
        db.Integer, ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False, index=True)
    name = db.Column(
        db.Unicode(length=500), nullable=False)
    description = db.Column(db.UnicodeText)
    status = db.Column(
        db.Unicode(length=25), server_default='active', nullable=False)
    num_citation_screening_reviewers = db.Column(
        db.SmallInteger, server_default=text('1'), nullable=False)
    num_fulltext_screening_reviewers = db.Column(
        db.SmallInteger, server_default=text('1'), nullable=False)

    # relationships
    owner = db.relationship(
        'User', foreign_keys=[owner_user_id], back_populates='owned_reviews',
        lazy='select')
    users = db.relationship(
        'User', secondary=users_reviews, back_populates='reviews',
        lazy='dynamic')
    review_plan = db.relationship(
        'ReviewPlan', uselist=False, back_populates='review',
        lazy='select', passive_deletes=True)
    citations = db.relationship(
        'Citation', back_populates='review',
        lazy='dynamic', passive_deletes=True)
    fulltexts = db.relationship(
        'Fulltext', back_populates='review',
        lazy='dynamic', passive_deletes=True)
    citation_screenings = db.relationship(
        'CitationScreening', back_populates='review',
        lazy='dynamic', passive_deletes=True)
    fulltext_screenings = db.relationship(
        'FulltextScreening', back_populates='review',
        lazy='dynamic', passive_deletes=True)

    def __init__(self, name, owner_user_id, description=None):
        self.name = name
        self.owner_user_id = owner_user_id
        self.description = description

    def __repr__(self):
        return "<Review(id={})>".format(self.id)


class ReviewPlan(db.Model):

    __tablename__ = 'review_plans'

    # columns
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        unique=True, nullable=False, index=True)
    objective = db.Column(db.UnicodeText)
    research_questions = db.Column(
        postgresql.ARRAY(db.Unicode(length=300)), server_default='{}')
    pico = db.Column(
        postgresql.JSONB(none_as_null=True), server_default='{}')
    keyterms = db.Column(
        postgresql.JSONB(none_as_null=True), server_default='{}')
    selection_criteria = db.Column(
        postgresql.JSONB(none_as_null=True), server_default='{}')
    data_extraction_form = db.Column(
        postgresql.JSONB(none_as_null=True), server_default='{}')

    # relationships
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='review_plan',
        lazy='subquery')

    def __init__(self, review_id,
                 objective=None, research_questions=None, pico=None,
                 keyterms=None, selection_criteria=None,
                 data_extraction_form=None):
        self.review_id = review_id
        self.objective = objective
        self.research_questions = research_questions
        self.pico = pico
        self.keyterms = keyterms
        self.selection_criteria = selection_criteria
        self.data_extraction_form = data_extraction_form

    def __repr__(self):
        return "<ReviewPlan(review_id={})>".format(self.review_id)


class Citation(db.Model):

    __tablename__ = 'citations'
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
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        nullable=False, index=True)
    status = db.Column(
        db.Unicode(length=20), nullable=False, server_default='not_screened',
        index=True)
    deduplication = db.Column(
        postgresql.JSONB(none_as_null=True), server_default='{}')
    tags = db.Column(
        postgresql.ARRAY(db.Unicode(length=25)), server_default='{}',
        index=True)
    type_of_work = db.Column(db.Unicode(length=25))
    title = db.Column(
        db.Unicode(length=250), nullable=False,
        server_default='unknown')
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
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='citations',
        lazy='select')
    fulltext = db.relationship(
        'Fulltext', uselist=False, back_populates='citation',
        lazy='select', passive_deletes=True)
    screenings = db.relationship(
        'CitationScreening', back_populates='citation',
        lazy='dynamic', passive_deletes=True)

    def __init__(self, review_id,
                 type_of_work=None, title=None, secondary_title=None, abstract=None,
                 pub_year=None, pub_month=None, authors=None, keywords=None,
                 type_of_reference=None, journal_name=None, volume=None,
                 issue_number=None, doi=None, issn=None, publisher=None,
                 language=None, other_fields=None):
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
        return "<Citation(id={})>".format(self.id)


class Fulltext(db.Model):

    __tablename__ = 'fulltexts'

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        nullable=False, index=True)
    citation_id = db.Column(
        db.BigInteger, ForeignKey('citations.id', ondelete='CASCADE'),
        unique=True, nullable=False, index=True)
    status = db.Column(
        db.Unicode(length=20), nullable=False, server_default='not_screened',
        index=True)
    content = db.Column(
        db.UnicodeText, nullable=False)
    filename = db.Column(
        db.UnicodeText,
        unique=True, nullable=True)
    extracted_info = db.Column(postgresql.JSONB(none_as_null=True))

    # relationships
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='fulltexts',
        lazy='select')
    citation = db.relationship(
        'Citation', foreign_keys=[citation_id], back_populates='fulltext',
        lazy='subquery')
    screenings = db.relationship(
        'FulltextScreening', back_populates='fulltext',
        lazy='dynamic', passive_deletes=True)

    def __init__(self, review_id, citation_id, content, filename=None):
        self.review_id = review_id
        self.citation_id = citation_id
        self.content = content
        self.filename = filename

    def __repr__(self):
        return "<Fulltext(citation_id={})>".format(self.citation_id)


class CitationScreening(db.Model):

    __tablename__ = 'citation_screenings'
    __table_args__ = (
        db.UniqueConstraint('review_id', 'user_id', 'citation_id',
                            name='review_user_citation_uc'),
        )

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        nullable=False, index=True)
    user_id = db.Column(
        db.Integer, ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False, index=True)
    citation_id = db.Column(
        db.BigInteger, ForeignKey('citations.id', ondelete='CASCADE'),
        nullable=False, index=True)
    status = db.Column(
        db.Unicode(length=20),
        nullable=False, index=True)
    exclude_reasons = db.Column(
        postgresql.ARRAY(db.Unicode(length=25)),
        nullable=True)

    # relationships
    user = db.relationship(
        'User', foreign_keys=[user_id], back_populates='citation_screenings',
        lazy='select')
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='citation_screenings',
        lazy='select')
    citation = db.relationship(
        'Citation', foreign_keys=[citation_id], back_populates='screenings',
        lazy='subquery')

    def __init__(self, review_id, user_id, citation_id, status, exclude_reasons):
        self.review_id = review_id
        self.user_id = user_id
        self.citation_id = citation_id
        self.status = status
        self.exclude_reasons = exclude_reasons

    def __repr__(self):
        return "<CitationScreening(citation_id={})>".format(self.citation_id)


class FulltextScreening(db.Model):

    __tablename__ = 'fulltext_screenings'
    __table_args__ = (
        db.UniqueConstraint('review_id', 'user_id', 'fulltext_id',
                            name='review_user_fulltext_uc'),
        )

    # columns
    id = db.Column(
        db.BigInteger, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.TIMESTAMP(timezone=False),
        server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"))
    review_id = db.Column(
        db.Integer, ForeignKey('reviews.id', ondelete='CASCADE'),
        nullable=False, index=True)
    user_id = db.Column(
        db.Integer, ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False, index=True)
    fulltext_id = db.Column(
        db.BigInteger, ForeignKey('fulltexts.id', ondelete='CASCADE'),
        nullable=False, index=True)
    status = db.Column(
        db.Unicode(length=20),
        nullable=False, index=True)
    exclude_reasons = db.Column(
        postgresql.ARRAY(db.Unicode(length=25)),
        nullable=True)

    # relationships
    user = db.relationship(
        'User', foreign_keys=[user_id], back_populates='fulltext_screenings',
        lazy='select')
    review = db.relationship(
        'Review', foreign_keys=[review_id], back_populates='fulltext_screenings',
        lazy='select')
    fulltext = db.relationship(
        'Fulltext', foreign_keys=[fulltext_id], back_populates='screenings',
        lazy='subquery')

    def __init__(self, review_id, user_id, fulltext_id, status, exclude_reasons):
        self.review_id = review_id
        self.user_id = user_id
        self.fulltext_id = fulltext_id
        self.status = status
        self.exclude_reasons = exclude_reasons

    def __repr__(self):
        return "<FulltextScreening(fulltext_id={})>".format(self.fulltext_id)