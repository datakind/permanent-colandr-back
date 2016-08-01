import hug

from . import citation
from . import user


router = hug.route.API(__name__)
# router.get('/citation')(citation.get_citation)
# router.get('/user')(user.get_user)
@hug.extend_api()
def foo():
    return [citation, user]
