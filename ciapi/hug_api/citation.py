import hug
from psycopg2.extensions import AsIs

from ciapi import hug_api
from ciapi.hug_api.auth import AUTH


@hug.get('/',
         output=hug.output_format.pretty_json,
         requires=AUTH)
def get_citation(
        user: hug.directives.user,
        citation_id: hug.types.InRange(1, 2147483647, convert=hug.types.number),
        review_id: hug.types.InRange(1, 2147483647, convert=hug.types.number),
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
    result = list(hug_api.PGDB.run_query(query, bindings=bindings))
    if not result:
        raise Exception()
    return result[0]
