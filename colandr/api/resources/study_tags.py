import itertools

from flask import g
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ...lib import constants, utils
from ...models import db, Review, Study
from ..errors import no_data_found, unauthorized
from ..authentication import auth


logger = utils.get_console_logger(__name__)


class StudyTagsResource(Resource):

    method_decorators = [auth.login_required]

    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        })
    def get(self, review_id):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get study tags for this review'.format(g.current_user))
        studies = review.studies\
            .filter(Study.tags != [])\
            .with_entities(Study.tags)
        return sorted(set(itertools.chain.from_iterable(study[0] for study in studies)))
