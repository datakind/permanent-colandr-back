#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
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
    if plan.get('objective'):
        print('\nObjective:\n{}'.format(plan.get('objective')))
    else:
        print('\nObjective: None')

    if plan.get('research_questions'):
        print('\nResearch Questions:\n{}'.format(
            '\n'.join('{0:>2} {1}'.format(rq['rank'], rq['question'])
                      for rq in plan['research_questions'])))
    else:
        print('Research Questions: None')

    if plan.get('pico'):
        print('\nPICO:\n{}'.format(
            '\n'.join('- {0:<14}: {1}'.format(key.title(), plan['pico'].get(key))
                      for key in ('population', 'intervention', 'comparator', 'outcome'))))
    else:
        print('PICO: None')

    if plan.get('keyterms'):
        print('\nKeyterms:')
        groups = {kt['group'] for kt in plan['keyterms']}
        for group in groups:
            print('- Group: {}'.format(group))
            print('\n'.join('    - {} {}'.format(kt['term'], '(synonyms: {})'.format(kt['synonyms']) if kt.get('synonyms') else '')
                            for kt in plan['keyterms'] if kt['group'] == group))
    else:
        print('Keyterms: None')

    if plan.get('selection_criteria'):
        print('\nSelection Criteria:\n{}'.format(
            '\n'.join('- {}: {}'.format(sc['label'], sc['explanation'])
                      for sc in plan['selection_criteria'])))
    else:
        print('Selection Criteria: None')

    print('')


def get_objective():
    objective = input('Objective:\n')
    return objective


def get_research_questions():
    print('\nResearch Questions')
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
    print('\nPICO')
    pico = {}
    for key in ('population', 'intervention', 'comparator', 'outcome'):
        value = input('{}:\n'.format(key.title()))
        if value:
            pico[key] = value
    return pico


def get_keyterms():
    print('\nKeyterms')
    keyterms = []
    while True:
        group = input('\nGroup name: ')
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


def get_selection_criteria():
    print('\nSelection Criteria')
    criteria = []
    while True:
        label = input('\nCriterion label: ')
        if not label:
            break
        while True:
            explanation = input('"{}" explanation:\n'.format(label))
            if explanation:
                break
            else:
                sure = input('No explanation — are you sure (y/n)? ')
                if sure == 'y':
                    break
        criteria.append({'label': label, 'explanation': explanation})
    return criteria


def sanitize_and_validate_plan(plan):
    sanitized_plan = cipy.validation.review_plan.sanitize(plan)
    review_plan = cipy.validation.review_plan.ReviewPlan(sanitized_plan)
    try:
        review_plan.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_plan)
        LOGGER.exception(msg)
    return review_plan.to_primitive()


def dump_json_fields_to_str(validated_plan):
    list_keys = {'research_questions', 'pico', 'keyterms', 'selection_criteria'}
    for key in list_keys:
        if validated_plan.get(key):
            validated_plan[key] = json.dumps(validated_plan[key])
    return validated_plan


def main():
    parser = argparse.ArgumentParser(
        description='Plan out a systematic review.')
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
    plans_db.create_table()

    query = "SELECT * FROM review_plans WHERE review_id = %(review_id)s"
    try:
        plan = list(plans_db.run_query(query, {'review_id': args.review_id}))[0]
    except IndexError:
        plan = {}

    present_review_plan(plan)

    print('\nUPDATES:')
    updated_plan = {'review_id': args.review_id}
    updated_plan['objective'] = get_objective()
    updated_plan['research_questions'] = get_research_questions()
    updated_plan['pico'] = get_pico()
    updated_plan['keyterms'] = get_keyterms()
    updated_plan['selection_criteria'] = get_selection_criteria()

    updated_plan = {key: value for key, value in updated_plan.items() if value}
    plan.update(updated_plan)

    validated_plan = sanitize_and_validate_plan(plan)
    present_review_plan(validated_plan)
    validated_plan = dump_json_fields_to_str(validated_plan)

    plans_db.execute(
        plans_db.ddl['templates']['upsert_values'], validated_plan, act=act)
    msg = 'valid record: review_id={} with {}, {}'.format(
        validated_plan['review_id'],
        {k for k, v in validated_plan.items() if k != 'review_id' and v},
        '' if act is True else '(TEST)')
    LOGGER.info(msg)


if __name__ == '__main__':
    sys.exit(main())
