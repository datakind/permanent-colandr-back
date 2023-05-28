import argparse
import io
import json
import logging
import os
import random
from pprint import pprint
import sys

from colandr.app import create_app
from colandr.config import configs
from colandr.tasks import suggest_keyterms
import requests

LOGGER = logging.getLogger('repopulate_db')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)

logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)

BASE_URL = 'http://localhost:5001/api/'
session = requests.Session()

USERS = [
    {'name': 'Burton DeWilde', 'email': 'burtondewilde@gmail.com', 'password': 'password'},
    {'name': 'Ray Shah', 'email': 'rayshah@thinkdesign.com', 'password': 'password'},
    {'name': 'Caitlin Augustin', 'email': 'caugustin@rsmas.miami.edu', 'password': 'password'},
    {'name': 'Bob Minnich', 'email': 'rcm2164@columbia.edu', 'password': 'password'},
    {'name': 'Sam Anzaroot', 'email': 'samanzaroot@gmail.com', 'password': 'password'},
    ]

REVIEW = {'name': 'Conservation International Demo',
          'description': 'International policy has sought to emphasize and strengthen the link between the conservation of natural ecosystems and human development. Furthermore, international conservation organizations have broadened their objectives beyond nature-based goals to recognize the contribution of conservation interventions in sustaining ecosystem services upon which human populations are dependent. While many indices have been developed to measure various human well-being domains, the strength of evidence to support the effects, both positive and negative, of conservation interventions on human well-being, is still unclear.\n\nThis protocol describes the methodology for examining the research question: What are the impacts of nature conservation interventions on different domains of human well-being in developing countries? Using systematic mapping, this study will scope and identify studies that measure the impacts of nature conservation interventions on human well-being at local to regional scales. The primary objective of this study is to synthesize the state and distribution of the existing evidence base linking conservation and human well-being. In addition, a theory of change approach will be used to identify and characterize the causal linkages between conservation and human well-being, with attention on those studies that examine the role of ecosystem services. Key trends among the resulting studies will be synthesized and the range of studies organized and presented in a graphical matrix illustrating the relationships between types of interventions and types of outcomes. Results of the study are intended to help conservation and development practitioners and the academic community to improve research studies and conservation practices in developing countries in order to achieve both conservation and human well-being outcomes.'}

REVIEW_PLAN = {
    'objective': 'To assess and characterize the current state and distribution of the existing evidence base around the causal linkages between both positive and negative effects of nature conservation and human well-being.',
    'research_questions': ["What are the impacts of nature conservation interventions on different domains of human well-being in developing countries?",
                           "What is the current state and distribution of evidence?",
                           "What types of impacts from conservation interventions on human well-being are measured?",
                           "What types of ecosystem services are explicitly associated with the impacts of conservation interventions on human well-being?",
                           "What populations are affected by conservation and/ or focus of studies?",
                           "How does the evidence base align with major priorities and investments of implementing agencies?",
                           ],
    'pico': {"population": "Human populations, including individuals, households, communities or nation states in non-OECD countries",
             "intervention": "Adoption or implementation of nature conservation interventions",
             "comparison": "No use of nature conservation interventions either between sites or groups, or over time series (before/after)",
             "outcome": "Positive or negative effects on the multi-dimensional well-being status of human populations"
             },
    'keyterms': [{"term": "wellbeing", "group": "outcome", "synonyms": ["well-being", "well being"]},
                 {"term": "ecosystem service", "group": "outcome", "synonyms": ["ecosystem services"]},
                 {"term": "nutrition", "group": "outcome"},
                 {"term": "skill", "group": "outcome", "synonyms": ["skills"]},
                 {"term": "empower", "group": "outcome", "synonyms": ["empowering"]},
                 {"term": "clean water", "group": "outcome", "synonyms": ["food security"]},
                 {"term": "livelihoods", "group": "outcome", "synonyms": ["livelihood"]},
                 {"term": "resilience", "group": "outcome", "synonyms": ["vulnerability"]},
                 {"term": "capital", "group": "outcome", "synonyms": ["social capital"]},
                 {"term": "attitude", "group": "outcome", "synonyms": ["attitudes"]},
                 {"term": "perception", "group": "outcome", "synonyms": ["perceptions"]},
                 {"term": "health", "group": "outcome", "synonyms": ["human health"]},
                 {"term": "human capital", "group": "outcome", "synonyms": ["knowledge"]},
                 {"term": "traditional knowledge", "group": "outcome"},
                 {"term": "marine", "group": "intervention qualifiers", "synonyms": ["freshwater"]},
                 {"term": "coastal", "group": "intervention qualifiers"},
                 {"term": "forest", "group": "intervention qualifiers", "synonyms": ["forests", "forestry"]},
                 {"term": "ecosystem", "group": "intervention qualifiers", "synonyms": ["ecosystems"]},
                 {"term": "species", "group": "intervention qualifiers"},
                 {"term": "habitat", "group": "intervention qualifiers", "synonyms": ["habitats"]},
                 {"term": "biodiversity", "group": "intervention qualifiers"},
                 {"term": "sustainable", "group": "intervention qualifiers", "synonyms": ["sustainability"]},
                 {"term": "ecology", "group": "intervention qualifiers", "synonyms": ["ecological"]},
                 {"term": "integrated", "group": "intervention qualifiers"},
                 {"term": "landscape", "group": "intervention qualifiers"},
                 {"term": "seascape", "group": "intervention qualifiers"},
                 {"term": "coral reef", "group": "intervention qualifiers", "synonyms": ["coral reefs"]},
                 {"term": "natural resources", "group": "intervention qualifiers", "synonyms": ["natural resource"]},
                 {"term": "human", "group": "outcome qualifiers", "synonyms": ["humans", "humanity"]},
                 {"term": "people", "group": "outcome qualifiers"},
                 {"term": "person", "group": "outcome qualifiers", "synonyms": ["persons"]},
                 {"term": "community", "group": "outcome qualifiers", "synonyms": ["communities"]},
                 {"term": "household", "group": "outcome qualifiers", "synonyms": ["households"]},
                 {"term": "fishermen", "group": "outcome qualifiers", "synonyms": ["fisherman"]},
                 {"term": "collaborative", "group": "outcome qualifiers"},
                 {"term": "conservation", "group": "intervention"},
                 {"term": "conserve", "group": "intervention"},
                 {"term": "conservancy", "group": "intervention"},
                 {"term": "protect", "group": "intervention", "synonyms": ["protects", "protection"]},
                 {"term": "management", "group": "intervention"},
                 {"term": "awareness", "group": "intervention"},
                 {"term": "law", "group": "intervention", "synonyms": ["laws"]},
                 {"term": "policy", "group": "intervention", "synonyms": ["policy-making"]},
                 {"term": "reserve", "group": "intervention"},
                 {"term": "govern", "group": "intervention", "synonyms": ["governs", "government"]},
                 {"term": "capacity-build", "group": "intervention", "synonyms": ["capacity-building", "capacity building"]},
                 {"term": "train", "group": "intervention", "synonyms": ["trains", "training"]},
                 {"term": "PES", "group": "intervention"},
                 {"term": "ecotourism", "group": "intervention", "synonyms": ["eco-tourism"]},
                 {"term": "sustainable use", "group": "intervention"}
                 ],
    'selection_criteria': [{"label": "location",
                            "description": "individuals, households, or communities must be in non-OECD countries"},
                           {"label": "undefined pop.",
                            "description": "studies must include discrete populations and not undefined groups or populations"},
                           {"label": "intervention type",
                            "description": "study must document or measure people's specific and discrete external interventions, not daily use"},
                           {"label": "in-situ",
                            "description": "study must focus on establishment, adoption, or implementation of regulation, protection, or management of natural ecosystems through in-situ activities"},
                           {"label": "outcome",
                            "explanation": "studies must measure or describe human well-being outcomes, and can't only focus on biophysical outcomes of conservation"}
                           ],
    'data_extraction_form': [{'label': 'biblio',
                              'description': 'bibliographic information',
                              'field_type': 'str'},
                             {'label': 'intervention_type',
                              'description': 'basic information about type of conservation intervention',
                              'field_type': 'select_many',
                              'allowed_values': ['area management',
                                                 'area protection',
                                                 'awareness and communications',
                                                 'compliance and enforcement',
                                                 'conservation finance',
                                                 'formal education',
                                                 'institutional and civil society development',
                                                 'legislation',
                                                 'enterprises and livelihood alternatives',
                                                 'market forces',
                                                 'non-monetary values',
                                                 'other',
                                                 'partnership and alliance development',
                                                 'policies and regulations',
                                                 'private sector standards and codes',
                                                 'resource protection and management',
                                                 'restoration',
                                                 'species control',
                                                 'species management',
                                                 'species recovery',
                                                 'species re-introduction',
                                                 'substitution',
                                                 'sustainable use',
                                                 'training']},
                             {'label': 'outcome_type',
                              'description': 'human well-being outcomes',
                              'field_type': 'select_many',
                              'allowed_values': ['economic living standards',
                                                 'material living standards',
                                                 'health',
                                                 'education',
                                                 'social relations',
                                                 'security and safety',
                                                 'governance and empowerment',
                                                 'subjective well-being',
                                                 'cultural and spiritual',
                                                 'freedom of choice/action',
                                                 'other']},
                             {'label': 'study_design',
                              'description': 'basic information on study design and subjects',
                              'field_type': 'select_many',
                              'allowed_values': ['before/after, control/intervention',
                                                 'before/after',
                                                 'change over time',
                                                 'comparison group',
                                                 'before/after, comparison group',
                                                 'comparison group, control/intervention',
                                                 'no comparator']},
                             {'label': 'biome',
                              'description': 'type of ecosystem',
                              'field_type': 'select_many',
                              'allowed_values': ['marine',
                                                 'freshwater',
                                                 'forest',
                                                 'grassland',
                                                 'desert',
                                                 'tundra',
                                                 'mangrove']}
                             ]
    }

CITATIONS = ['ci-full-collection-group1.ris', 'ci-full-collection-group2.ris']

FULLTEXTS = [
    'references/Bottrill_et al_2014_systematic protocol.pdf',
    'references/OMara_2015_Text_mining_and_SRs.pdf'
    ]

TAGS = ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']


def get_auth_token(email, password):
    """For your convenience."""
    response = session.get(BASE_URL + 'authtoken', auth=(email, password))
    response.raise_for_status()
    return (response.json()['token'], '')


def get_user_password(email):
    try:
        return [USER['password'] for USER in USERS
                if USER['email'] == email][0]
    except IndexError:
        LOGGER.exception('no user password found for user email "{}"'.format(email))
        raise


def main():

    parser = argparse.ArgumentParser(
        description='Repopulate the colandr database from scratch.')
    parser.add_argument(
        '-e', '--email', dest='email', type=str, required=True,
        help='valid email address for an existing admin user')
    parser.add_argument(
        '-p', '--password', dest='password', type=str, required=True,
        help='valid password for an existing admin user')
    parser.add_argument(
        '-c', '--config', dest='config_name', type=str,
        choices=sorted(configs.keys()),
        default=os.getenv('COLANDR_FLASK_CONFIG', 'default'))
    parser.add_argument(
        '--last', type=str, default='',
        help='last table to populate; subsequent tables will not be filled',
        choices=['users', 'reviews', 'review_plans', 'citations',
                 'citation_screenings', 'fulltexts', 'fulltext_screenings'])

    args = vars(parser.parse_args())
    app = create_app(args['config_name'])
    admin_auth = get_auth_token(args['email'], args['password'])

    print('\n\n')
    LOGGER.info('adding users to db...')
    current_user = None
    for i, USER in enumerate(USERS):
        response = session.request(
            'POST', BASE_URL + 'users', auth=admin_auth, json=USER)
        print('POST:', response.url)
        user = response.json()
        pprint(user, width=120)
        if i == 0:
            current_user = user

    if args['last'] == 'users':
        LOGGER.warning('stopping db repopulation at "users"')
        return
    LOGGER.info('current user: <User(id={})>'.format(current_user['id']))

    # let's get an authentication token for our current user
    auth = get_auth_token(
        current_user['email'], get_user_password(current_user['email']))

    print('\n\n')
    LOGGER.info('adding review to db...')
    response = session.request(
        'POST', BASE_URL + 'reviews', json=REVIEW, auth=auth)
    print('POST:', response.url)
    review = response.json()
    review_id = review['id']
    pprint(review, width=120)

    print('\n\n')
    LOGGER.info('modifying review settings in db...')
    settings = {'num_citation_screening_reviewers': 2,
                'num_fulltext_screening_reviewers': 2}
    response = session.request(
        'PUT', BASE_URL + 'reviews/{}'.format(review_id),
        json=settings, auth=auth)
    print('PUT:', response.url)
    pprint(response.json(), width=120)

    print('\n\n')
    LOGGER.info('adding collaborators to review in db...')
    for USER in USERS:
        if USER['email'] == current_user['email']:
            continue
        response = session.request(
            'GET', BASE_URL + 'users', params={'email': USER['email']}, auth=auth)
        print('GET:', response.url)
        user = response.json()
        response = session.request(
            'PUT', BASE_URL + 'reviews/{}/team'.format(review_id),
            json={'user_id': user['id'], 'action': 'add'}, auth=auth)
        print('PUT:', response.url)
        team = response.json()
    pprint(team)

    if args['last'] == 'reviews':
        LOGGER.warning('stopping db repopulation at "reviews"')
        return

    print('\n\n')
    LOGGER.info('updating review plan in db...')
    review_plan = REVIEW_PLAN.copy()
    review_plan['fields'] = ','.join(REVIEW_PLAN.keys())
    response = session.request(
        'PUT', BASE_URL + 'reviews/{}/plan'.format(review_id),
        json=review_plan, auth=auth)
    response.raise_for_status()
    print('PUT:', response.url)
    review_plan = response.json()
    pprint(review_plan, width=120)

    if args['last'] == 'review_plans':
        LOGGER.warning('stopping db repopulation at "review_plans"')
        return

    print('\n\n')
    LOGGER.info('importing citations...')
    source_names = ['scopus', 'web of science', 'pubmed']
    for filename in CITATIONS:
        citations_file = os.path.join(
            app.config['CITATIONS_DIR'], filename)
        if not os.path.isfile(citations_file):
            raise OSError()
        response = session.request(
            'POST', BASE_URL + 'citations/imports',
            data={'review_id': review_id,
                  'source_type': 'database',
                  'source_name': random.choice(source_names)},
            files={'uploaded_file': (filename, io.open(citations_file, mode='rb'))},
            auth=auth)
        print('POST:', citations_file, '=>', response.url)

    # add tags to a small random sample of studies
    results = session.request(
        'GET', BASE_URL + 'studies', auth=auth,
        params={'fields': 'id',
                'review_id': 1,
                'order_by': 'recency',
                'per_page': 5000})
    for result in random.sample([result['id'] for result in results.json()], 100):
        response = session.request(
            'PUT', BASE_URL + 'studies/{}'.format(result), auth=auth,
            json={'tags': random.sample(TAGS, random.randint(1, 3))})

    if args['last'] == 'citations':
        LOGGER.warning('stopping db repopulation at "citations"')
        return

    print('\n\n')
    LOGGER.info('adding citation screenings to db...')
    response = session.request(
        'GET', BASE_URL + 'reviews/{}/plan'.format(review_id),
        params={'fields': 'selection_criteria'},
        auth=auth)
    print('GET:', response.url)
    exclude_reasons = [
        criterion['label']
        for criterion in response.json().get('selection_criteria', [])]
    if not exclude_reasons:
        exclude_reasons = ['criterion #1', 'criterion #2']

    # get citation ids
    all_citation_ids = []
    page = 0
    while True:
        response = session.request(
            'GET', BASE_URL + 'studies',
            params={'review_id': review_id, 'fields': 'id',
                    'citation_status': 'pending',
                    'order_by': 'recency', 'order_dir': 'ASC',
                    'per_page': 5000, 'page': page},
            auth=auth)
        print('GET:', response.url)
        citation_ids = [result['id'] for result in response.json()]
        if not citation_ids:
            break
        else:
            all_citation_ids.extend(citation_ids)
            page += 1
    print('# citations to screen = {}'.format(len(all_citation_ids)))

    # load known statuses
    with io.open('./colandr_data/citations/known_statuses.json', mode='r') as f:
        known_statuses = json.load(f)
    included_citation_ids = {
        record['id'] for record in known_statuses
        if record['status'] == 'included'}

    response = session.request(
        'GET', BASE_URL + 'users', params={'review_id': review_id}, auth=auth)
    print('GET:', response.url)
    users = response.json()
    for user in users[:2]:
        print('<USER(id={})>'.format(user['id']))
        # auth = get_auth_token(
        #     user['email'], get_user_password(user['email']))

        user_id = user['id']
        screenings = []
        for citation_id in all_citation_ids:
            if citation_id in included_citation_ids:
                screenings.append(
                    {'citation_id': citation_id, 'status': 'included'})
                continue
            # only exclude a random sample of 75% of citations
            if random.random() < 0.25:
                continue
            screenings.append(
                {'citation_id': citation_id,
                 'status': 'excluded',
                 'exclude_reasons': random.sample(exclude_reasons, random.randint(1, 2))}
                )

        # re-authenticate then POST data as admin
        admin_auth = get_auth_token(args['email'], args['password'])
        response = session.request(
            'POST', BASE_URL + 'citations/screenings', auth=admin_auth,
            params={'review_id': review_id, 'user_id': user_id},
            json=screenings)
        response.raise_for_status()
        print('POST:', response.url)

    # run async task to suggest keyterms based on included/excluded citations
    suggest_keyterms.apply_async(args=[review_id, 500])

    if args['last'] == 'citation_screenings':
        LOGGER.warning('stopping db repopulation at "citation_screenings"')
        return

    # let's get an authentication token for our current user, again
    auth = get_auth_token(
        current_user['email'], get_user_password(current_user['email']))

    print('\n\n')
    LOGGER.info('uploading fulltexts to server disk...')

    # get fulltext ids
    all_fulltext_ids = []
    page = 0
    while True:
        response = session.request(
            'GET', BASE_URL + 'studies',
            params={'review_id': review_id, 'fields': 'id',
                    'fulltext_status': 'pending',
                    'order_by': 'recency', 'order_dir': 'ASC',
                    'per_page': 5000, 'page': page},
            auth=auth)
        print('GET:', response.url)
        fulltext_ids = [result['id'] for result in response.json()]
        if not fulltext_ids:
            break
        else:
            all_fulltext_ids.extend(fulltext_ids)
            page += 1
    print('# fulltexts to upload = {}'.format(len(all_fulltext_ids)))

    for fulltext_id in all_fulltext_ids[:10]:  # only upload 10
        fulltext_file = random.choice(FULLTEXTS)
        filename = os.path.split(fulltext_file)[-1]
        response = session.request(
            'POST', BASE_URL + 'fulltexts/{}/upload'.format(fulltext_id),
            files={'uploaded_file': (filename, io.open(fulltext_file, mode='rb'))},
            auth=auth)
        print('POST:', response.url)
        fulltext = response.json()
        print('uploaded file {} for <Fulltext(id={})>'.format(
            fulltext['filename'], fulltext_id))

    if args['last'] == 'fulltexts':
        LOGGER.warning('stopping db repopulation at "fulltexts"')
        return

    print('\n\n')
    LOGGER.info('adding fulltext screenings to db...')
    response = session.request(
        'GET', BASE_URL + 'reviews/{}/plan'.format(review_id),
        params={'fields': 'selection_criteria'},
        auth=auth)
    print('GET:', response.url)
    exclude_reasons = [
        criterion['label']
        for criterion in response.json().get('selection_criteria', [])]
    if not exclude_reasons:
        exclude_reasons = ['criterion #1', 'criterion #2']

    # get fulltext ids
    all_fulltext_ids = []
    page = 0
    while True:
        response = session.request(
            'GET', BASE_URL + 'studies',
            params={'review_id': review_id, 'fields': 'id',
                    'fulltext_status': 'pending',
                    'order_by': 'recency', 'order_dir': 'ASC',
                    'per_page': 5000, 'page': page},
            auth=auth)
        print('GET:', response.url)
        fulltext_ids = [result['id'] for result in response.json()]
        if not fulltext_ids:
            break
        else:
            all_fulltext_ids.extend(fulltext_ids)
            page += 1
    print('# fulltexts to screen = {}'.format(len(all_fulltext_ids)))

    response = session.request(
        'GET', BASE_URL + 'users', params={'review_id': review_id}, auth=auth)
    print('GET:', response.url)
    users = response.json()
    for user in users[:2]:
        print('<USER(id={})>'.format(user['id']))
        # auth = get_auth_token(
        #     user['email'], get_user_password(user['email']))

        user_id = user['id']
        screenings = []
        for fulltext_id in all_fulltext_ids:
            # only screen a random sample of 75% of fulltexts
            if random.random() < 0.25:
                continue
            # exclude a random sample of 95% of citations
            if random.random() < 0.5:
                screenings.append(
                    {'fulltext_id': fulltext_id,
                     'status': 'excluded',
                     'exclude_reasons': random.sample(exclude_reasons, random.randint(1, 2))}
                    )
            else:
                screenings.append(
                    {'fulltext_id': fulltext_id, 'status': 'included'})

        admin_auth = get_auth_token(args['email'], args['password'])
        response = session.request(
            'POST', BASE_URL + 'fulltexts/screenings', auth=admin_auth,
            params={'review_id': review_id, 'user_id': user_id},
            json=screenings)
        response.raise_for_status()
        print('POST:', response.url)

    if args['last'] == 'fulltext_screenings':
        LOGGER.warning('stopping db repopulation at "fulltext_screenings"')
        return

    # TODO: data extraction stuff

    # let's get an authentication token for our current user, again again
    auth = get_auth_token(
        current_user['email'], get_user_password(current_user['email']))

    print('\n\n')
    LOGGER.info('getting review progress...')
    response = session.request(
        'GET', BASE_URL + 'reviews/{}/progress'.format(review_id),
        params={'step': 'all', 'user_view': False},
        auth=auth)
    print('GET:', response.url)
    pprint(response.json())

    print('')
    response = session.request(
        'GET', BASE_URL + 'reviews/{}/progress'.format(review_id),
        params={'step': 'all', 'user_view': True},
        auth=auth)
    print('GET:', response.url)
    pprint(response.json())


if __name__ == '__main__':
    sys.exit(main())
