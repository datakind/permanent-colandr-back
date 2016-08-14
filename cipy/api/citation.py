import hug
from psycopg2.extensions import AsIs

import cipy
from cipy.api.auth import AUTH


CONN_CREDS = cipy.db.get_conn_creds('DATABASE_URL')
CITATIONS_DB = cipy.db.PostgresDB(CONN_CREDS, ddl='citations')


@hug.cli()
@hug.get('/', output=hug.output_format.pretty_json,
         requires=AUTH)
def get_citation(review_id: hug.types.InRange(1, 2147483647),
                 citation_id: hug.types.InRange(1, 2147483647),
                 fields: hug.types.DelimitedList(',')=['citation_id', 'authors', 'title', 'abstract', 'publication_year', 'doi']):
    query = """
        SELECT %(fields)s
        FROM citations
        WHERE
            citation_id = %(citation_id)s
            AND review_id = %(review_id)s
        """
    bindings = {'fields': AsIs(','.join(fields)),
                'review_id': review_id,
                'citation_id': citation_id}
    return list(CITATIONS_DB.run_query(query, bindings=bindings))


if __name__ == '__main__':
    get_citation.interface.cli()
