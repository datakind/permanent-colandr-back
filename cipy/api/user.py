import hug
from psycopg2.extensions import AsIs

import cipy
from cipy.api.auth import AUTH


CONN_CREDS = cipy.db.get_conn_creds('DATABASE_URL')
USERS_DB = cipy.db.PostgresDB(CONN_CREDS, ddl='users')


@hug.cli()
@hug.get('/', output=hug.output_format.pretty_json,
         requires=AUTH)
def get_user(user_id: hug.types.InRange(1, 2147483647),
             fields: hug.types.DelimitedList(',')=['user_id', 'name', 'email', 'review_ids', 'owned_review_ids']):
    query = """
        SELECT %(fields)s
        FROM users
        WHERE user_id = %(user_id)s
        """
    bindings = {'fields': AsIs(','.join(fields)),
                'user_id': user_id}
    return list(USERS_DB.run_query(query, bindings=bindings))


if __name__ == '__main__':
    get_user.interface.cli()
