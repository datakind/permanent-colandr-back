import hug

import cipy


CONN_CREDS = cipy.db.get_conn_creds('DATABASE_URL')
USERS_DB = cipy.db.PostgresDB(CONN_CREDS, ddl='users')


class APIUser(object):
    def __init__(self, user_id, name, review_ids, owned_review_ids):
        self.user_id = user_id
        self.name = name
        self.review_ids = review_ids
        self.owned_review_ids = owned_review_ids


def verify_user(email, password):
    db_matches = list(USERS_DB.run_query(
        USERS_DB.ddl['templates']['login_user'],
        bindings={'email': email, 'password': password}))
    if not db_matches:
        return False
    assert len(db_matches) == 1
    match = db_matches[0]
    return APIUser(match['user_id'], match['name'],
                   match['review_ids'], match['owned_review_ids'])


AUTH = hug.authentication.basic(verify_user)
