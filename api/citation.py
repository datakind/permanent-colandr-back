import hug
from psycopg2.extensions import AsIs

import cipy


LOGGER = cipy.utils.get_logger('citation_api')
CONN_CREDS = cipy.db.get_conn_creds('DATABASE_URL')
CITATIONS_DB = cipy.db.PostgresDB(CONN_CREDS, ddl='citations')


@hug.cli()
@hug.get('/citation', output=hug.output_format.pretty_json)
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


@hug.request_middleware()
def process_data(request, response):
    response.set_header('Content-Type', 'application/vnd.api+json')


if __name__ == '__main__':
    get_citation.interface.cli()
