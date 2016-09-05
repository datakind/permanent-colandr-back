from flask_restful import Resource  # , abort
from flask_restful_swagger import swagger
from sqlalchemy.orm import load_only
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Email, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ciapi.models import db, Review
from ciapi.schemas import ReviewSchema


class ReviewsResource(Resource):

    @swagger.operation()
    @use_args(ReviewSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        review = Review(**args)
        if test is False:
            db.session.add(review)
            db.session.commit()
        return ReviewSchema().dump(review).data


# REVIEWS_DDL = cipy.db.db_utils.get_ddl('reviews')
# USERS_DDL = cipy.db.db_utils.get_ddl('users')
#
#
# class ReviewSettingsSchema(Schema):
#     num_citation_screening_reviewers = fields.Int(
#         required=True, missing=2, validate=Range(min=1, max=3))
#     num_fulltext_screening_reviewers = fields.Int(
#         required=True, missing=2, validate=Range(min=1, max=3))
#     required_citation_screener_id = fields.Int(
#         missing=None, validate=Range(min=0, max=2147483647))
#     required_fulltext_screener_id = fields.Int(
#         missing=None, validate=Range(min=0, max=2147483647))
#
#     class Meta:
#         strict = True
#
#
# class ReviewSchema(Schema):
#     review_id = fields.Int(
#         dump_only=True)
#     created_ts = fields.DateTime(
#         dump_only=True, format='iso', missing=arrow.utcnow().datetime)
#     owner_user_id = fields.Int(
#         required=True, missing=0, validate=Range(min=1, max=2147483647))
#     user_ids = fields.List(
#         fields.Int(validate=Range(min=1, max=2147483647)),
#         required=True, missing=[])
#     name = fields.Str(
#         required=True, validate=Length(max=500))
#     description = fields.Str(
#         missing=None)
#     settings = fields.Nested(
#         ReviewSettingsSchema,
#         required=True, missing=ReviewSettingsSchema().load({}).data)
#
#     class Meta:
#         strict = True
#
#
# class Review(Resource):
#
#     @swagger.operation()
#     @use_kwargs({
#         'review_id': fields.Int(
#             required=True, location='view_args',
#             validate=Range(min=1, max=2147483647)),
#         'fields': DelimitedList(
#             fields.String(), delimiter=',',
#             missing=['review_id', 'created_ts', 'owner_user_id', 'user_ids', 'name', 'description'])
#         })
#     def get(self, review_id, fields):
#         if review_id not in session['user']['review_ids']:
#             # UnauthorizedException
#             raise Exception('user not authorized to get this review')
#         query = """
#             SELECT %(fields)s
#             FROM reviews
#             WHERE review_id = %(review_id)s
#             """
#         bindings = {'fields': AsIs(','.join(fields)),
#                     'review_id': review_id}
#         result = list(PGDB.run_query(query, bindings=bindings))
#         if not result:
#             # MissingDataException
#             raise Exception('no results found')
#         return jsonify(result[0])
#
#     @swagger.operation()
#     @use_args(ReviewSchema(only=['name', 'description', 'settings']))
#     @use_kwargs({'test': fields.Boolean(missing=False)})
#     def post(self, args, test):
#         args['owner_user_id'] = session['user']['user_id']
#         args['user_ids'] = [session['user']['user_id']]
#         args['settings'] = json.dumps(args['settings'])
#         if test is True:
#             list(PGDB.run_query(
#                 REVIEWS_DDL['templates']['create_review'],
#                 bindings=args,
#                 act=False))
#             return args
#         else:
#             created_review_id = list(PGDB.run_query(
#                 REVIEWS_DDL['templates']['create_review'],
#                 bindings=args,
#                 act=True))[0]['review_id']
#             return created_review_id
#
#     @swagger.operation()
#     @use_kwargs({
#         'review_id': fields.Int(
#             required=True, location='view_args',
#             validate=Range(min=1, max=2147483647)),
#         'test': fields.Boolean(missing=False)
#         })
#     def delete(self, review_id, test):
#         if review_id not in session['user']['owned_review_ids']:
#             # UnauthorizedException
#             raise Exception('user not authorized to delete this review')
#         act = not test
#         # delete review from reviews table
#         PGDB.execute(
#             REVIEWS_DDL['templates']['delete_review'],
#             {'review_id': review_id, 'owner_user_id': session['user']['user_id']},
#             act=act)
#         # remove review from associated users in users table
#         updated_users = PGDB.run_query(
#             USERS_DDL['templates']['remove_deleted_review'],
#             {'review_id': review_id},
#             act=act)
#         if act is True:
#             updated_user_ids = [user['user_id'] for user in updated_users]
#             logging.info('review id=%s removed from user ids=%s',
#                          review_id, updated_user_ids)
#         else:
#             logging.info('deleted review id=%s (TEST)', review_id)
#
#
# class Reviews(Resource):
#
#     @swagger.operation()
#     @use_kwargs({
#         'fields': DelimitedList(
#             fields.String(), delimiter=',',
#             missing=['review_id', 'created_ts', 'owner_user_id', 'user_ids', 'name'])
#         })
#     def get(self, fields):
#         query = """
#             SELECT %(fields)s
#             FROM reviews
#             WHERE %(user_id)s = ANY(user_ids)
#             """
#         bindings = {'fields': AsIs(','.join(fields)),
#                     'user_id': session['user']['user_id']}
#         results = list(PGDB.run_query(query, bindings=bindings))
#         if not results:
#             # MissingDataException
#             raise Exception('no results found')
#         return jsonify(results)
