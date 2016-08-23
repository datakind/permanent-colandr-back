import hug
from psycopg2.extensions import AsIs

from ciapi import hug_api
from ciapi.hug_api.auth import AUTH


@hug.get('/',
         output=hug.output_format.pretty_json,
         requires=AUTH)
def get_citations(
        user: hug.directives.user,
        review_id: hug.types.InRange(1, 2147483647, convert=hug.types.number),
        fields: hug.types.DelimitedList(',')=['citation_id', 'authors', 'title', 'abstract', 'publication_year', 'doi'],
        order_dir: hug.types.OneOf({'ASC', 'DESC'})='ASC',
        per_page: hug.types.InRange(10, 50)=10,
        page: hug.types.GreaterThan(-1, convert=hug.types.number)=0):
    query = """
        SELECT %(fields)s
        FROM citations
        WHERE review_id = %(review_id)s
        ORDER BY citation_id %(order_dir)s
        LIMIT %(limit)s
        OFFSET %(offset)s
        """
    bindings = {'fields': AsIs(','.join(fields)),
                'review_id': review_id,
                'order_dir': AsIs(order_dir),
                'limit': per_page,
                'offset': page * per_page}
    return list(hug_api.PGDB.run_query(query, bindings=bindings))


@hug.post('/load')
def load_citations():
    return
