# import logging
import itertools
import os
from time import sleep

import arrow
from celery.utils.log import get_task_logger
from flask import current_app
from flask_mail import Message
import redis
import redis_lock
from sqlalchemy import create_engine, func, types as sqltypes
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm.session import Session
from sqlalchemy.sql import case, delete, exists, select, text, update

import numpy as np
from sklearn.externals import joblib
from sklearn.linear_model import SGDClassifier
import textacy

from . import celery, mail
from .api.schemas import ReviewPlanSuggestedKeyterms
from .lib.constants import CITATION_RANKING_MODEL_FNAME
from .lib.utils import get_console_logger, load_dedupe_model, make_record_immutable
from .models import (db, Citation, Dedupe, DedupeBlockingMap, DedupeCoveredBlocks,
                     DedupePluralBlock, DedupePluralKey, DedupeSmallerCoverage,
                     Fulltext, ReviewPlan, Study, User)


REDIS_CONN = redis.StrictRedis()

logger = get_task_logger(__name__)
console_logger = get_console_logger('colandr_celery_tasks')


def wait_for_lock(name, expire=60):
    lock = redis_lock.Lock(REDIS_CONN, name, expire=expire, auto_renewal=True)
    while True:
        if lock.acquire() is False:
            console_logger.info('waiting on existing %s job...', name)
            sleep(10)
        else:
            console_logger.info('starting new %s job...', name)
            break
    return lock


@celery.task
def send_email(recipients, subject, text_body, html_body):
    msg = Message(current_app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)


@celery.task
def remove_unconfirmed_user(email):
    user = db.session.query(User).filter_by(email=email).one_or_none()
    if user and user.is_confirmed is False:
        db.session.delete(user)
        db.session.commit()


def _get_candidate_dupes(results):
    block_id = None
    records = []
    for row in results:
        if row.block_id != block_id:
            if records:
                yield records
            block_id = row.block_id
            records = []
        smaller_ids = frozenset(row.smaller_ids)
        records.append((row.citation_id,
                        make_record_immutable(dict(row)),
                        smaller_ids))
    if records:
        yield records


@celery.task
def deduplicate_citations(review_id):

    lock = wait_for_lock('deduplicate_citations_review_id={}'.format(review_id), expire=60)

    deduper = load_dedupe_model(
        os.path.join(current_app.config['DEDUPE_MODELS_FOLDER'],
                     'dedupe_citations_settings'))
    engine = create_engine(
        current_app.config['SQLALCHEMY_DATABASE_URI'],
        server_side_cursors=True, echo=False)

    with engine.connect() as conn:

        # wait until no more review citations have been created in 60+ seconds
        stmt = select([func.max(Citation.created_at)])\
            .where(Citation.review_id == review_id)
        while True:
            max_created_at = conn.execute(stmt).fetchone()[0]
            elapsed_time = (arrow.utcnow().naive - max_created_at).total_seconds()
            if elapsed_time < 60:
                logger.debug(
                    'citation last created %s seconds ago, sleeping...', elapsed_time)
                sleep(10)
            else:
                break

        # if studies have been deduped since most recent import, cancel
        # stmt = select(
        #     [exists().where(Study.review_id == review_id).where(Study.dedupe_status == None)])
        stmt = select([func.max(Dedupe.created_at)])\
            .where(Dedupe.review_id == review_id)
        most_recent_dedupe = conn.execute(stmt).fetchone()[0]
        if most_recent_dedupe and most_recent_dedupe > max_created_at:
            logger.info('<Review(id=%s)>: all studies already deduped!', review_id)
            lock.release()
            return

        # remove rows for this review
        # which we'll add back with the latest citations included
        for table in [Dedupe, DedupeBlockingMap, DedupePluralKey, DedupePluralBlock,
                      DedupeCoveredBlocks, DedupeSmallerCoverage]:
            stmt = delete(table).where(getattr(table, 'review_id') == review_id)
            result = conn.execute(stmt)
            rows_deleted = result.rowcount
            logger.debug(
                '<Review(id=%s)>: deleted %s rows from %s',
                review_id, rows_deleted, table.__tablename__)

        # if deduper learned an Index Predicate
        # we have to take a pass through the data and create indices
        for field in deduper.blocker.index_fields:
            col_type = getattr(Citation, field).property.columns[0].type
            # print('index predicate: {} {}'.format(field, col_type))
            logger.debug(
                '<Review(id=%s)>: index predicate: %s %s', review_id, field, col_type)
            stmt = select([getattr(Citation, field)])\
                .where(Citation.review_id == review_id)\
                .distinct()
            results = conn.execute(stmt)
            if isinstance(col_type, sqltypes.ARRAY):
                field_data = (tuple(row[0]) for row in results)
            else:
                field_data = (row[0] for row in results)
            deduper.blocker.index(field_data, field)

        # now we're ready to write our blocking map table by creating a generator
        # that yields unique (block_key, citation_id, review_id) tuples
        stmt = select([Citation.id, Citation.title, Citation.authors,
                       Citation.pub_year.label('publication_year'),  # HACK: trained model expects this field
                       Citation.abstract, Citation.doi])\
            .where(Citation.review_id == review_id)
        results = conn.execute(stmt)
        data = ((row[0], make_record_immutable(dict(row)))
                for row in results)
        b_data = ((citation_id, review_id, block_key)
                  for block_key, citation_id in deduper.blocker(data))
        conn.execute(
            DedupeBlockingMap.__table__.insert(),
            [{'citation_id': row[0], 'review_id': row[1], 'block_key': row[2]}
             for row in b_data])

        # now fill review rows back in
        stmt = select([DedupeBlockingMap.review_id, DedupeBlockingMap.block_key])\
            .where(DedupeBlockingMap.review_id == review_id)\
            .group_by(DedupeBlockingMap.review_id, DedupeBlockingMap.block_key)\
            .having(func.count(1) > 1)
        conn.execute(
            DedupePluralKey.__table__.insert()\
                .from_select(['review_id', 'block_key'], stmt))

        stmt = select([DedupePluralKey.block_id,
                       DedupeBlockingMap.citation_id,
                       DedupeBlockingMap.review_id])\
            .where(DedupePluralKey.block_key == DedupeBlockingMap.block_key)\
            .where(DedupeBlockingMap.review_id == review_id)
        conn.execute(
            DedupePluralBlock.__table__.insert()\
                .from_select(['block_id', 'citation_id', 'review_id'], stmt))

        # To use Kolb, et. al's Redundant Free Comparison scheme, we need to
        # keep track of all the block_ids that are associated with particular
        # citation records
        stmt = select([DedupePluralBlock.citation_id,
                       DedupePluralBlock.review_id,
                       func.array_agg(aggregate_order_by(DedupePluralBlock.block_id,
                                                         DedupePluralBlock.block_id.desc()),
                                      type_=sqltypes.ARRAY(sqltypes.BigInteger)).label('sorted_ids')])\
            .where(DedupePluralBlock.review_id == review_id)\
            .group_by(DedupePluralBlock.citation_id, DedupePluralBlock.review_id)
        conn.execute(
            DedupeCoveredBlocks.__table__.insert()\
                .from_select(['citation_id', 'review_id', 'sorted_ids'], stmt))

        # for every block of records, we need to keep track of a citation records's
        # associated block_ids that are SMALLER than the current block's id
        ugh = 'dedupe_covered_blocks.sorted_ids[0: array_position(dedupe_covered_blocks.sorted_ids, dedupe_plural_block.block_id) - 1] AS smaller_ids'
        stmt = select([DedupePluralBlock.citation_id,
                       DedupePluralBlock.review_id,
                       DedupePluralBlock.block_id,
                       text(ugh)])\
            .where(DedupePluralBlock.citation_id == DedupeCoveredBlocks.citation_id)\
            .where(DedupePluralBlock.review_id == review_id)
        conn.execute(
            DedupeSmallerCoverage.__table__.insert()\
                .from_select(['citation_id', 'review_id', 'block_id', 'smaller_ids'], stmt))

        # set dedupe model similarity threshold from the data
        stmt = select([Citation.id, Citation.title, Citation.authors,
                       Citation.pub_year.label('publication_year'),  # HACK: trained model expects this field
                       Citation.abstract, Citation.doi])\
            .where(Citation.review_id == review_id)\
            .order_by(func.random())\
            .limit(20000)
        results = conn.execute(stmt)
        dupe_threshold = deduper.threshold(
            {row.id: make_record_immutable(dict(row)) for row in results},
            recall_weight=0.5)

        # apply dedupe model to get clusters of duplicate records
        stmt = select([Citation.id.label('citation_id'), Citation.title, Citation.authors,
                       Citation.pub_year.label('publication_year'),  # HACK: trained model expects this field
                       Citation.abstract, Citation.doi,
                       DedupeSmallerCoverage.block_id, DedupeSmallerCoverage.smaller_ids])\
            .where(Citation.id == DedupeSmallerCoverage.citation_id)\
            .where(Citation.review_id == review_id)\
            .order_by(DedupeSmallerCoverage.block_id)
        results = conn.execute(stmt)

        clustered_dupes = deduper.matchBlocks(
            _get_candidate_dupes(results),
            threshold=dupe_threshold)
        logger.info(
            '<Review(id=%s)>: found %s duplicate clusters',
            review_id, len(clustered_dupes))

        # get *all* citation ids for this review
        stmt = select([Citation.id]).where(Citation.review_id == review_id)
        all_cids = {result[0] for result in conn.execute(stmt).fetchall()}
        duplicate_cids = set()

        studies_to_update = []
        dedupes_to_insert = []
        for cids, scores in clustered_dupes:
            cid_scores = {int(cid): float(score) for cid, score in zip(cids, scores)}
            stmt = select([Citation.id,
                           (case([(Citation.title == None, 1)]) +
                            case([(Citation.abstract == None, 1)]) +
                            case([(Citation.pub_year == None, 1)]) +
                            case([(Citation.pub_month == None, 1)]) +
                            case([(Citation.authors == {}, 1)]) +
                            case([(Citation.keywords == {}, 1)]) +
                            case([(Citation.type_of_reference == None, 1)]) +
                            case([(Citation.journal_name == None, 1)]) +
                            case([(Citation.issue_number == None, 1)]) +
                            case([(Citation.doi == None, 1)]) +
                            case([(Citation.issn == None, 1)]) +
                            case([(Citation.publisher == None, 1)]) +
                            case([(Citation.language == None, 1)])
                            ).label('n_null_cols')])\
                .where(Citation.review_id == review_id)\
                .where(Citation.id.in_([int(cid) for cid in cids]))\
                .order_by(text('n_null_cols ASC'))\
                .limit(1)
            result = conn.execute(stmt).fetchone()
            canonical_citation_id = result.id
            for cid, score in cid_scores.items():
                if cid != canonical_citation_id:
                    duplicate_cids.add(cid)
                    studies_to_update.append(
                        {'id': cid,
                         'dedupe_status': 'duplicate'})
                    dedupes_to_insert.append(
                        {'id': cid,
                         'review_id': review_id,
                         'duplicate_of': canonical_citation_id,
                         'duplicate_score': score})
        non_duplicate_cids = all_cids - duplicate_cids
        studies_to_update.extend(
            {'id': cid, 'dedupe_status': 'not_duplicate'}
            for cid in non_duplicate_cids)
        session = Session(bind=conn)
        session.bulk_update_mappings(Study, studies_to_update)
        session.bulk_insert_mappings(Dedupe, dedupes_to_insert)
        session.commit()
        logger.info(
            '<Review(id=%s)>: found %s duplicate and %s non-duplicate citations',
            review_id, len(duplicate_cids), len(non_duplicate_cids))

    lock.release()


@celery.task
def get_citations_text_content_vectors(review_id):

    lock = wait_for_lock(
        'get_citations_text_content_vectors_review_id={}'.format(review_id), expire=60)

    en_nlp = textacy.load_spacy(
        'en', tagger=False, parser=False, entity=False, matcher=False)
    engine = create_engine(
        current_app.config['SQLALCHEMY_DATABASE_URI'],
        server_side_cursors=True, echo=False)

    with engine.connect() as conn:

        # wait until no more review citations have been created in 60+ seconds
        stmt = select([func.max(Citation.created_at)])\
            .where(Citation.review_id == review_id)
        while True:
            max_created_at = conn.execute(stmt).fetchone()[0]
            if not max_created_at:
                logger.warning('<Review(id=%s)>: no citations found', review_id)
                lock.release()
                return
            elapsed_time = (arrow.utcnow().naive - max_created_at).total_seconds()
            if elapsed_time < 60:
                logger.debug(
                    '<Review(id=%s)>: citation last created %s seconds ago, sleeping...',
                    review_id, elapsed_time)
                sleep(10)
            else:
                break

        stmt = select([Citation.id, Citation.text_content])\
            .where(Citation.review_id == review_id)\
            .where(Citation.text_content_vector_rep == [])\
            .order_by(Citation.id)
        results = conn.execute(stmt)
        citations_to_update = []
        for id_, text_content in results:
            lang = textacy.text_utils.detect_language(text_content)
            if lang == 'en':
                try:
                    spacy_doc = en_nlp(text_content)
                except Exception as e:
                    logger.exception(
                        'unable to tokenize text content for <Citation(study_id=%s)>', id_)
                    continue
                citations_to_update.append(
                    {'id': id_, 'text_content_vector_rep': spacy_doc.vector.tolist()})
            else:
                logger.warning(
                    'lang "%s" detected for <Citation(study_id=%s)>', lang, id_)

        # TODO: collect (id, lang) pairs for those that aren't lang == 'en'
        # filter to those that can be tokenized and word2vec-torized
        # group by lang, then load the necessary models to do this for groups

        if not citations_to_update:
            logger.warning(
                '<Review(id=%s)>: no citation text_content_vector_reps to update',
                review_id)
            lock.release()
            return

        session = Session(bind=conn)
        session.bulk_update_mappings(Citation, citations_to_update)
        session.commit()
        logger.info(
            '<Review(id=%s)>: %s citation text_content_vector_reps updated',
            review_id, len(citations_to_update))

    lock.release()


@celery.task
def get_fulltext_text_content_vector(review_id, fulltext_id):

    # HACK: let's skip this for now, actually
    return

    lock = wait_for_lock(
        'get_fulltext_text_content_vector_review_id={}'.format(review_id), expire=60)

    engine = create_engine(
        current_app.config['SQLALCHEMY_DATABASE_URI'],
        server_side_cursors=True, echo=False)

    with engine.connect() as conn:

        # wait until no more review citations have been created in 60+ seconds
        stmt = select([Fulltext.text_content]).where(Fulltext.id == fulltext_id)
        text_content = conn.execute(stmt).fetchone()
        if not text_content:
            logger.warning(
                'no fulltext text content found for <Fulltext(study_id=%s)>',
                fulltext_id)
            lock.release()
            return
        else:
            text_content = text_content[0]

        lang = textacy.text_utils.detect_language(text_content)
        try:
            nlp = textacy.load_spacy(
                lang, tagger=False, parser=False, entity=False, matcher=False)
        except RuntimeError:
            logger.warning(
                'unable to load spacy lang "%s" for <Fulltext(study_id=%s)>',
                lang, fulltext_id)
            lock.release()
            return
        spacy_doc = nlp(text_content)
        try:
            text_content_vector_rep = spacy_doc.vector.tolist()
        except ValueError:
            logger.warning(
                'unable to get lang "%s" word vectors for <Fulltext(study_id=%s)>',
                lang, fulltext_id)
            lock.release()
            return

        stmt = update(Fulltext)\
            .where(Fulltext.id == fulltext_id)\
            .values(text_content_vector_rep=text_content_vector_rep)
        conn.execute(stmt)

        lock.release()


@celery.task
def suggest_keyterms(review_id, sample_size):

    lock = wait_for_lock(
        'suggest_keyterms_review_id={}'.format(review_id), expire=60)
    logger.info(
        '<Review(id=%s)>: computing keyterms with sample size = %s',
        review_id, sample_size)

    engine = create_engine(
        current_app.config['SQLALCHEMY_DATABASE_URI'],
        server_side_cursors=True, echo=False)
    with engine.connect() as conn:
        # get random sample of included citations
        stmt = select([Study.citation_status, Citation.text_content])\
            .where(Study.id == Citation.id)\
            .where(Study.review_id == review_id)\
            .where(Study.citation_status == 'included')\
            .order_by(func.random())\
            .limit(sample_size)
        included = conn.execute(stmt).fetchall()
        # get random sample of excluded citations
        stmt = select([Study.citation_status, Citation.text_content])\
            .where(Study.id == Citation.id)\
            .where(Study.review_id == review_id)\
            .where(Study.citation_status == 'excluded')\
            .order_by(func.random())\
            .limit(sample_size)
        excluded = conn.execute(stmt).fetchall()

        # munge the results into the form needed by textacy
        included_vec = [status == 'included' for status, _
                        in itertools.chain(included, excluded)]
        docs = (textacy.Doc(text, lang='en') for _, text
                in itertools.chain(included, excluded))
        terms_lists = (
            doc.to_terms_list(include_pos={'NOUN', 'VERB'}, as_strings=True)
            for doc in docs)

        # run the analysis!
        incl_keyterms, excl_keyterms = textacy.keyterms.most_discriminating_terms(
            terms_lists, included_vec, top_n_terms=50)

        # munge results into form expected by the database, and validate
        suggested_keyterms = {
            'sample_size': sample_size,
            'incl_keyterms': incl_keyterms,
            'excl_keyterms': excl_keyterms}
        errors = ReviewPlanSuggestedKeyterms().validate(suggested_keyterms)
        if errors:
            lock.release()
            raise Exception
        logger.info(
            '<Review(id=%s)>: suggested keyterms: %s', review_id, suggested_keyterms)
        # update the review plan
        stmt = update(ReviewPlan)\
            .where(ReviewPlan.id == review_id)\
            .values(suggested_keyterms=suggested_keyterms)
        conn.execute(stmt)

    lock.release()


@celery.task
def train_citation_ranking_model(review_id):

    lock = wait_for_lock(
        'train_citation_ranking_model_review_id={}'.format(review_id), expire=60)
    logger.info('<Review(id=%s)>: training citation ranking model', review_id)

    engine = create_engine(
        current_app.config['SQLALCHEMY_DATABASE_URI'],
        server_side_cursors=True, echo=False)
    with engine.connect() as conn:

        # make sure at least some citations have had their
        n_iters = 1
        while True:
            stmt = select(
                [exists().where(Citation.review_id == review_id).where(Citation.text_content_vector_rep != [])])
            citations_ready = conn.execute(stmt).fetchone()[0]
            if citations_ready is True:
                break
            else:
                logger.debug(
                    '<Review(id=%s)>: waiting for vectorized text content for, %s',
                    review_id, n_iters)
                sleep(30)
            if n_iters > 6:
                logger.error(
                    '<Review(id=%s)>: no citations with vectorized text content found',
                    review_id)
                lock.release()
                return
            n_iters += 1

        # get random sample of included citations
        stmt = select([Citation.text_content_vector_rep, Study.citation_status])\
            .where(Study.id == Citation.id)\
            .where(Study.review_id == review_id)\
            .where(Study.dedupe_status == 'not_duplicate')\
            .where(Study.citation_status.in_(['included', 'excluded']))\
            .where(Citation.text_content_vector_rep != [])
        results = conn.execute(stmt).fetchall()

    # build features matrix and labels vector
    X = np.vstack(tuple(result[0] for result in results))
    y = np.array(tuple(1 if result[1] == 'included' else 0 for result in results))

    # train the classifier
    clf = SGDClassifier(class_weight='balanced').fit(X, y)

    # save to disk!
    fname = CITATION_RANKING_MODEL_FNAME.format(review_id=review_id)
    filepath = os.path.join(current_app.config['RANKING_MODELS_FOLDER'], fname)
    joblib.dump(clf, filepath)
    logger.info(
        '<Review(id=%s)>: citation ranking model saved to %s', review_id, filepath)

    lock.release()
