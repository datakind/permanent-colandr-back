import argparse
import io
import logging
import os
import random
from pprint import pprint
import sys

import requests

LOGGER = logging.getLogger('repopulate_db')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)

BASE_URL = 'http://localhost:5000/'

USERS = [
    {'name': 'Burton DeWilde', 'email': 'burtdewilde@gmail.com', 'password': 'password'},
    {'name': 'Ray Shah', 'email': 'rayshah@thinkdesign.com', 'password': 'password'},
    {'name': 'Caitlin Augustin', 'email': 'caugustin@rsmas.miami.edu', 'password': 'password'},
    {'name': 'Bob Minnich', 'email': 'rcm2164@columbia.edu', 'password': 'password'},
    {'name': 'Sam Anzaroot', 'email': 'samanzaroot@gmail.com', 'password': 'password'},
    ]

REVIEWS = [
    {'name': 'Conservation International Demo',
     'description': 'International policy has sought to emphasize and strengthen the link between the conservation of natural ecosystems and human development. Furthermore, international conservation organizations have broadened their objectives beyond nature-based goals to recognize the contribution of conservation interventions in sustaining ecosystem services upon which human populations are dependent. While many indices have been developed to measure various human well-being domains, the strength of evidence to support the effects, both positive and negative, of conservation interventions on human well-being, is still unclear.\n\nThis protocol describes the methodology for examining the research question: What are the impacts of nature conservation interventions on different domains of human well-being in developing countries? Using systematic mapping, this study will scope and identify studies that measure the impacts of nature conservation interventions on human well-being at local to regional scales. The primary objective of this study is to synthesize the state and distribution of the existing evidence base linking conservation and human well-being. In addition, a theory of change approach will be used to identify and characterize the causal linkages between conservation and human well-being, with attention on those studies that examine the role of ecosystem services. Key trends among the resulting studies will be synthesized and the range of studies organized and presented in a graphical matrix illustrating the relationships between types of interventions and types of outcomes. Results of the study are intended to help conservation and development practitioners and the academic community to improve research studies and conservation practices in developing countries in order to achieve both conservation and human well-being outcomes.'},
    ]

REVIEW_PLANS = [
    {'review_id': 1,
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
              "comparator": "No use of nature conservation interventions either between sites or groups, or over time series (before/after)",
              "outcome": "Positive or negative effects on the multi-dimensional well-being status of human populations"
              },
     'keyterms': [{"term": "wellbeing", "group": "outcome", "synonyms": ["well-being", "well being"]},
                  {"term": "ecosystem service", "group": "outcome", "synonyms": ["ecosystem services"]},
                  {"term": "nutrition", "group": "outcome"},
                  {"term": "skill", "group": "outcome", "synonyms": ["skills"]},
                  {"term": "empower", "group": "outcome", "synonyms": ["empowering"]},
                  {"term": "clean water", "group": "outcome", "synonyms": ["livelihood"]},
                  {"term": "livelihoods", "group": "outcome", "synonyms": ["food security"]},
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
                  {"term": "train", "group": "intervention", "synonyms": ["tarins", "training"]},
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
     }
    ]

CITATIONS = {1: ['../conservation-intl/data/raw/citation_files/ci-full-collection-group1.ris',
                 '../conservation-intl/data/raw/citation_files/ci-full-collection-group2.ris']
             }

FULLTEXTS = {1: ['../conservation-intl/references/Bottrill_et al_2014_systematic protocol.pdf']}


def get_auth_token(email, password):
    """For your convenience."""
    response = requests.get(BASE_URL + 'authtoken', auth=(email, password))
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
    parser.add_argument('--email', type=str, required=True)
    parser.add_argument(
        '--last', type=str, default='',
        help='last table to populate; subsequent tables will not be filled',
        choices=['users', 'reviews', 'review_plans', 'citations',
                 'citation_screenings', 'fulltexts', 'fulltext_screenings'])

    args = vars(parser.parse_args())

    print('\n\n')
    LOGGER.info('adding users to db...')
    current_user = None
    for USER in USERS:
        response = requests.request(
            'POST', BASE_URL + 'users', json=USER)
        print('POST:', response.url)
        user = response.json()
        pprint(user, width=120)
        if user['email'] == args['email']:
            current_user = user

    if args['last'] == 'users':
        LOGGER.warning('stopping db repopulation at "users"')
        return
    if current_user:
        LOGGER.info('current user: <User(id={})>'.format(user['id']))
    else:
        logging.error('user email not found in list of users to insert into db')
        return

    # let's get an authentication token for our current user
    auth = get_auth_token(
        current_user['email'], get_user_password(current_user['email']))

    print('\n\n')
    LOGGER.info('adding reviews to db...')
    review_ids = []
    for REVIEW in REVIEWS:
        response = requests.request(
            'POST', BASE_URL + 'reviews', json=REVIEW, auth=auth)
        print('POST:', response.url)
        review = response.json()
        review_ids.append(review['id'])
        pprint(review, width=120)

    print('\n\n')
    LOGGER.info('modifying review settings in db...')
    settings = {'num_citation_screening_reviewers': 2,
                'num_fulltext_screening_reviewers': 2}
    for review_id in review_ids:
        response = requests.request(
            'PUT', BASE_URL + 'reviews/{}'.format(review_id),
            json=settings, auth=auth)
        print('PUT:', response.url)
        pprint(response.json(), width=120)

    print('\n\n')
    LOGGER.info('adding collaborators to review in db...')
    for review_id in review_ids:
        for USER in USERS:
            if USER['email'] == current_user['email']:
                continue
            response = requests.request(
                'GET', BASE_URL + 'users', params={'email': USER['email']}, auth=auth)
            print('GET:', response.url)
            user = response.json()
            response = requests.request(
                'PUT', BASE_URL + 'reviews/{}/team'.format(review_id),
                json={'user_id': user['id'], 'action': 'add'}, auth=auth)
            print('PUT:', response.url)
            team = response.json()
            pprint(team)
            break

    if args['last'] == 'reviews':
        LOGGER.warning('stopping db repopulation at "reviews"')
        return

    print('\n\n')
    LOGGER.info('adding review plans to db...')
    for REVIEW_PLAN in REVIEW_PLANS:
        response = requests.request(
            'POST', BASE_URL + 'reviews/{}/plan'.format(REVIEW_PLAN['review_id']),
            json=REVIEW_PLAN, auth=auth)
        response.raise_for_status()
        print('POST:', response.url)
        review_plan = response.json()
        pprint(review_plan, width=120)

    if args['last'] == 'review_plans':
        LOGGER.warning('stopping db repopulation at "review_plans"')
        return

    print('\n\n')
    LOGGER.info('uploading citations to db...')
    for review_id in review_ids:
        print('<REVIEW(id={})>'.format(review_id))
        citations_files = CITATIONS.get(review_id, [])
        for citations_file in citations_files:
            if not os.path.isfile(citations_file):
                raise OSError()
            filename = os.path.split(citations_file)[-1]
            response = requests.request(
                'POST', BASE_URL + 'citations',
                data={'review_id': review_id},
                files={'uploaded_file': (filename, io.open(citations_file, mode='rb'))},
                auth=auth)
            print('POST:', filename, '=>', response.url)

    if args['last'] == 'citations':
        LOGGER.warning('stopping db repopulation at "citations"')
        return

    print('\n\n')
    LOGGER.info('adding citation screenings to db...')
    for review_id in review_ids:
        print('<REVIEW(id={})>'.format(review_id))
        response = requests.request(
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
            response = requests.request(
                'GET', BASE_URL + 'citations',
                params={'review_id': review_id, 'fields': 'id',
                        'order_dir': 'ASC', 'per_page': 5000, 'page': page},
                auth=auth)
            print('GET:', response.url)
            citation_ids = [result['id'] for result in response.json()]
            if not citation_ids:
                break
            else:
                all_citation_ids.extend(citation_ids)
                page += 1
        print('# citations to screen = {}'.format(len(all_citation_ids)))

        response = requests.request(
            'GET', BASE_URL + 'users', params={'review_id': review_id}, auth=auth)
        print('GET:', response.url)
        users = response.json()
        for user in users:
            print('<USER(id={})>'.format(user['id']))
            auth = get_auth_token(
                user['email'], get_user_password(user['email']))

            screenings = []
            for citation_id in all_citation_ids:
                # only screen a random sample of 75% of citations
                if random.random() < 0.25:
                    continue
                # exclude a random sample of 95% of citations
                if random.random() < 0.95:
                    screenings.append(
                        {'citation_id': citation_id,
                         'status': 'excluded',
                         'exclude_reasons': random.sample(exclude_reasons, random.randint(1, 2))}
                        )
                else:
                    screenings.append(
                        {'citation_id': citation_id, 'status': 'included'})

            response = requests.request(
                'POST', BASE_URL + 'citations/screenings',
                json=screenings, params={'review_id': review_id},
                auth=auth)
            print('POST:', response.url)

    if args['last'] == 'citation_screenings':
        LOGGER.warning('stopping db repopulation at "citation_screenings"')
        return

    # let's get an authentication token for our current user, again
    auth = get_auth_token(
        current_user['email'], get_user_password(current_user['email']))

    print('\n\n')
    LOGGER.info('uploading fulltexts to server disk...')
    for review_id in review_ids:
        print('<REVIEW(id={})>'.format(review_id))
        fulltext_files = FULLTEXTS.get(review_id, [])
        if not fulltext_files:
            raise Exception('no fulltext files found...')

        # get fulltext ids
        all_fulltext_ids = []
        page = 0
        while True:
            response = requests.request(
                'GET', BASE_URL + 'fulltexts',
                params={'review_id': review_id, 'fields': 'id',
                        'order_dir': 'ASC', 'per_page': 1000, 'page': page},
                auth=auth)
            print('GET:', response.url)
            fulltext_ids = [result['id'] for result in response.json()]
            if not fulltext_ids:
                break
            else:
                all_fulltext_ids.extend(fulltext_ids)
                page += 1
        print('# fulltexts to upload = {}'.format(len(all_fulltext_ids)))

        for fulltext_id in all_fulltext_ids:
            fulltext_file = random.choice(fulltext_files)
            filename = os.path.split(fulltext_file)[-1]
            response = requests.request(
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
    for review_id in review_ids:
        print('<REVIEW(id={})>'.format(review_id))
        response = requests.request(
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
            response = requests.request(
                'GET', BASE_URL + 'fulltexts',
                params={'review_id': review_id, 'fields': 'id',
                        'order_dir': 'ASC', 'per_page': 1000, 'page': page},
                auth=auth)
            print('GET:', response.url)
            fulltext_ids = [result['id'] for result in response.json()]
            if not fulltext_ids:
                break
            else:
                all_fulltext_ids.extend(fulltext_ids)
                page += 1
        print('# fulltexts to screen = {}'.format(len(all_fulltext_ids)))

        response = requests.request(
            'GET', BASE_URL + 'users', params={'review_id': review_id}, auth=auth)
        print('GET:', response.url)
        users = response.json()
        for user in users:
            print('<USER(id={})>'.format(user['id']))
            auth = get_auth_token(
                user['email'], get_user_password(user['email']))

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

            response = requests.request(
                'POST', BASE_URL + 'fulltexts/screenings',
                json=screenings, params={'review_id': review_id},
                auth=auth)
            print('POST:', response.url)

    if args['last'] == 'fulltext_screenings':
        LOGGER.warning('stopping db repopulation at "fulltext_screenings"')
        return

    # let's get an authentication token for our current user, again again
    auth = get_auth_token(
        current_user['email'], get_user_password(current_user['email']))

    print('\n\n')
    LOGGER.info('getting review progress...')
    for review_id in review_ids:
        print('<REVIEW(id={})>'.format(review_id))

        response = requests.request(
            'GET', BASE_URL + 'reviews/{}/progress'.format(review_id),
            params={'step': 'all', 'user_view': False},
            auth=auth)
        print('GET:', response.url)
        pprint(response.json())

        print('')
        response = requests.request(
            'GET', BASE_URL + 'reviews/{}/progress'.format(review_id),
            params={'step': 'all', 'user_view': True},
            auth=auth)
        print('GET:', response.url)
        pprint(response.json())


if __name__ == '__main__':
    sys.exit(main())