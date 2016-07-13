#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import re
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('plan_review')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def present_review_plan(plan):
    print('\nPROJECT PLAN')
    print('\nObjective: {}'.format(plan.get('objective')))

    if plan.get('research_questions'):
        print('\nResearch Questions:\n{}'.format(
            '\n'.join('{0:>2} {1}'.format(rq['rank'], rq['question'])
                      for rq in plan['research_questions'])))
    else:
        print('Research Questions: {}'.format(None))

    if plan.get('pico'):
        print('\nPICO:\n{}'.format(
            '\n'.join('\t{0:<14}: {1}'.format(key.title(), plan['pico'].get(key))
                      for key in ('population', 'intervention', 'comparator', 'outcome'))))
    else:
        print('PICO: None')

    if plan.get('keyterms'):
        print('\nKeyterms:')
        groups = {kt['group'] for kt in plan['keyterms']}
        for group in groups:
            print('\tGroup: {}'.format(group))
            print('\n'.join('\t{} {}'.format(kt['term'], '(synonyms: {})'.format(kt['synonyms']) if kt.get('synonyms') else '')
                            for kt in plan['keyterms'] if kt['group'] == group))
    else:
        print('Keyterms: None')

    if plan.get('data_sources'):
        print('\nData Sources:\n{}'.format(
            '\n'.join('{} {}'.format(ds['name'], ds['url']) for ds in plan['data_sources'])))
    else:
        print('Data Sources: None')

    print('')


def get_objective():
    objective = input('Objective:\n')
    return objective


def get_research_questions():
    print('Research Questions')
    rqs = []
    rank = 0
    while True:
        question = input('\nQuestion:\n')
        if question:
            rqs.append({'question': question, 'rank': rank})
            rank += 1
        else:
            break
    return rqs


def get_pico():
    print('PICO')
    pico = {}
    for key in ('population', 'intervention', 'comparator', 'outcome'):
        value = input('{}: '.format(key.title()))
        if value:
            pico[key] = value
    return pico


def get_keyterms():
    print('Keyterms')
    keyterms = []
    while True:
        group = input('\nGroup: ')
        if not group:
            break
        while True:
            keyterm = input('Term: ')
            if not keyterm:
                break
            synonyms = input('Synonyms, if any (separate by commas): ')
            if synonyms:
                synonyms = re.split('\s*,\s*', synonyms)
            else:
                synonyms = []
            keyterms.append(
                {'group': group, 'term': keyterm, 'synonyms': synonyms})
    return keyterms


def get_data_sources():
    print('Data Sources')
    data_sources = []
    while True:
        name = input('\nName: ')
        if not name:
            break
        while True:
            url = input('URL: ')
            if url:
                break
            else:
                print('URL is required!')
        notes = input('Notes, if any: ')
        data_sources.append({'name': name, 'url': url, notes: notes})
    return data_sources


def sanitize_and_validate_plan(plan):
    sanitized_plan = cipy.validation.review_plan.sanitize(plan)
    review_plan = cipy.validation.review_plan.ReviewPlan(sanitized_plan)
    try:
        review_plan.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_plan)
        LOGGER.exception(msg)
    return review_plan.to_primitive()


def main():
    parser = argparse.ArgumentParser(
        description='Create a new systematic map review.')
    parser.add_argument(
        '--user_id', type=int, required=True, metavar='user_id',
        help='unique identifier of current user')
    parser.add_argument(
        '--review_id', type=int, required=True, metavar='review_id',
        help='unique identifier of current systematic map review')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='flag to run script without modifying any data or models')
    args = parser.parse_args()

    act = not args.test

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    plans_db = cipy.db.PostgresDB(conn_creds, ddl='review_plans')

    query = "SELECT * FROM review_plans WHERE review_id = %(review_id)s"
    try:
        plan = list(plans_db.run_query(query, {'review_id': args.review_id}))[0]
    except IndexError:
        plan = {}

    present_review_plan(plan)

    print('\nUPDATES:')
    updated_plan = {}
    updated_plan['objective'] = get_objective()
    updated_plan['research_questions'] = get_research_questions()
    updated_plan['pico'] = get_pico()
    updated_plan['keyterms'] = get_keyterms()
    updated_plan['data_sources'] = get_data_sources()

    updated_plan = {key: value for key, value in updated_plan.items() if value}
    plan.update(updated_plan)
    plan['review_id'] = args.review_id

    validated_plan = sanitize_and_validate_plan(plan)
    present_review_plan(validated_plan)


if __name__ == '__main__':
    sys.exit(main())
