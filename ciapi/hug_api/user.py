import hug
from psycopg2.extensions import AsIs

import cipy
from ciapi import hug_api
from ciapi.hug_api.auth import AUTH

USERS_DDL = cipy.db.db_utils.get_ddl('users')


@hug.get('/',
         output=hug.output_format.pretty_json,
         requires=AUTH)
def get_user(
        user: hug.directives.user,
        user_id: hug.types.InRange(1, 2147483647),
        fields: hug.types.DelimitedList(',')=['user_id', 'name', 'email', 'review_ids', 'owned_review_ids']):
    query = """
        SELECT %(fields)s
        FROM users
        WHERE user_id = %(user_id)s
        """
    bindings = {'fields': AsIs(','.join(fields)),
                'user_id': user_id}
    results = list(hug_api.PGDB.run_query(query, bindings=bindings))
    if not results:
        raise Exception()
    return results[0]


def sanitize_and_validate_user_info(user_info):
    sanitized_user_info = cipy.validation.user.sanitize(user_info)
    user = cipy.validation.user.User(sanitized_user_info)
    user.validate()
    return user.to_primitive()


# NOTE: a unique column constraint was added to users table...
# def check_if_email_exists(email):
#     check = list(cipy.api.PGDB.run_query(
#         USERS_DDL['templates']['check_email_exists'],
#         bindings={'email': email}))
#     if check:
#         msg = 'user with email "{}" already exists'.format(email)
#         raise ValueError(msg)


@hug.post('/create')
def create_user(
        name: hug.types.Length(6, 200, convert=hug.types.text),
        email: hug.types.Length(6, 200, convert=hug.types.text),
        password: hug.types.text,
        act: hug.types.SmartBoolean=True):
    user = {'name': name, 'email': email, 'password': password}
    valid_user = sanitize_and_validate_user_info(user)
    # check_if_email_exists(valid_user['email'])
    created_user_id = list(cipy.api.PGDB.run_query(
        USERS_DDL['templates']['create_user'],
        bindings=valid_user,
        act=act))[0]['user_id']
    return created_user_id
