import itertools
import os
import time

import arrow
import redis
import redis.client
import redis.lock
import sqlalchemy as sa
from celery import current_app as current_celery_app
from celery import shared_task
from celery.utils.log import get_task_logger
from flask import current_app
from flask_mail import Message

from .apis.schemas import ReviewPlanSuggestedKeyterms
from .extensions import db, mail
from .lib.models import Deduper, Ranker
from .lib.nlp import hack
from .lib.nlp import utils as nlp_utils
from .models import Citation, Dedupe, Fulltext, ReviewPlan, Study, User


LOGGER = get_task_logger(__name__)


def _get_redis_lock(lock_id: str, timeout: int = 120) -> redis.lock.Lock:
    redis_conn = _get_redis_conn()
    return redis_conn.lock(lock_id, timeout=timeout, sleep=1.0, blocking=True)


def _get_redis_conn() -> redis.client.Redis:
    redis_conn = current_celery_app.backend.client
    assert isinstance(redis_conn, redis.client.Redis)  # type guard
    return redis_conn


@shared_task
def send_email(recipients, subject, text_body, html_body):
    msg = Message(
        current_app.config["MAIL_SUBJECT_PREFIX"] + " " + subject,
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=recipients,
    )
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)


@shared_task
def remove_unconfirmed_user(email):
    user = db.session.execute(
        sa.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    if user and user.is_confirmed is False:
        db.session.delete(user)
        db.session.commit()


@shared_task
def deduplicate_citations(review_id):
    lock = _get_redis_lock(f"deduplicate_ciations__review-{review_id}")
    lock.acquire()

    stmt = sa.select(sa.func.max(Citation.created_at)).where(
        Citation.review_id == review_id
    )
    max_created_at = db.session.execute(stmt).scalar()
    # no citations? cancel dedupe
    if max_created_at is None:
        LOGGER.warning(
            "<Review(id=%s)>: no citations found; skipping dedupe ...", review_id
        )
        lock.release()
        return

    stmt = sa.select(sa.func.max(Dedupe.created_at)).where(
        Dedupe.review_id == review_id
    )
    most_recent_dedupe = db.session.execute(stmt).scalar()
    # no citations added since most recent dedupe? cancel dedupe
    if most_recent_dedupe and most_recent_dedupe > max_created_at:
        LOGGER.info(
            "<Review(id=%s)>: all citations already deduped; skipping dedupe ...",
            review_id,
        )
        lock.release()
        return

    dir_path = os.path.join(
        current_app.config["COLANDR_APP_DIR"], "colandr_data", "dedupe-v2", "model"
    )
    deduper = Deduper.load(dir_path, num_cores=1, in_memory=False)

    # remove dedupe rows for this review
    # which we'll add back with the latest citations included
    stmt = sa.delete(Dedupe).where(Dedupe.review_id == review_id)
    result = db.session.execute(stmt)
    rows_deleted = result.rowcount
    LOGGER.debug(
        "<Review(id=%s)>: deleted %s rows from %s",
        review_id,
        rows_deleted,
        Dedupe.__tablename__,
    )

    stmt = sa.select(
        Citation.id,
        Citation.type_of_reference,
        Citation.title,
        Citation.pub_year,
        Citation.authors,
        Citation.abstract,
        Citation.doi,
    ).where(Citation.review_id == review_id)
    # results = db.session.execute(stmt).mappings() instead ?
    results = (row._asdict() for row in db.session.execute(stmt))
    preproc_data = deduper.preprocess_data(results, id_key="id")

    # TODO: decide on suitable value for threshold; higher => higher precision
    clustered_dupes = deduper.model.partition(preproc_data, threshold=0.5)
    try:
        LOGGER.info(
            "<Review(id=%s)>: found %s duplicate clusters",
            review_id,
            len(clustered_dupes),
        )
    # TODO: figure out if this is ever a generator instead
    except TypeError:
        LOGGER.info("<Review(id=%s)>: found duplicate clusters", review_id)

    # get *all* citation ids for this review, as well as included/excluded
    stmt = sa.select(Citation.id).where(Citation.review_id == review_id)
    all_cids = set(db.session.execute(stmt).scalars().all())
    stmt = (
        sa.select(Study.id)
        .where(Study.review_id == review_id)
        .where(Study.citation_status.in_(["included", "excluded"]))
    )
    incl_excl_cids = set(db.session.execute(stmt).scalars().all())

    duplicate_cids = set()
    studies_to_update = []
    dedupes_to_insert = []
    for cids, scores in clustered_dupes:
        int_cids = [int(cid) for cid in cids]  # convert from numpy.int64
        cid_scores = {cid: float(score) for cid, score in zip(int_cids, scores)}
        # already an in/excluded citation in this dupe cluster?
        # take the first one to be "canonical"
        if any(cid in incl_excl_cids for cid in int_cids):
            canonical_citation_id = sorted(set(int_cids).intersection(incl_excl_cids))[
                0
            ]
        # otherwise, take the "most complete" citation in the cluster as "canonical"
        else:
            stmt = (
                sa.select(
                    Citation.id,
                    (
                        sa.case([(Citation.title == None, 1)])
                        + sa.case([(Citation.abstract == None, 1)])
                        + sa.case([(Citation.pub_year == None, 1)])
                        + sa.case([(Citation.pub_month == None, 1)])
                        + sa.case([(Citation.authors == {}, 1)])
                        + sa.case([(Citation.keywords == {}, 1)])
                        + sa.case([(Citation.type_of_reference == None, 1)])
                        + sa.case([(Citation.journal_name == None, 1)])
                        + sa.case([(Citation.issue_number == None, 1)])
                        + sa.case([(Citation.doi == None, 1)])
                        + sa.case([(Citation.issn == None, 1)])
                        + sa.case([(Citation.publisher == None, 1)])
                        + sa.case([(Citation.language == None, 1)])
                    ).label("n_null_cols"),
                )
                .where(Citation.review_id == review_id)
                .where(Citation.id.in_(int_cids))
                .order_by(sa.text("n_null_cols ASC"))
                .limit(1)
            )
            result = db.session.execute(stmt).first()
            canonical_citation_id = result.id

        for cid, score in cid_scores.items():
            if cid != canonical_citation_id:
                duplicate_cids.add(cid)
                studies_to_update.append({"id": cid, "dedupe_status": "duplicate"})
                dedupes_to_insert.append(
                    {
                        "id": cid,
                        "review_id": review_id,
                        "duplicate_of": canonical_citation_id,
                        "duplicate_score": score,
                    }
                )
    non_duplicate_cids = all_cids - duplicate_cids
    studies_to_update.extend(
        {"id": cid, "dedupe_status": "not_duplicate"} for cid in non_duplicate_cids
    )

    # TODO: update this for sqlalchemy v2
    # ref: https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html#orm-enabled-insert-update-and-delete-statements
    db.session.bulk_update_mappings(Study, studies_to_update)
    db.session.bulk_insert_mappings(Dedupe, dedupes_to_insert)
    db.session.commit()
    LOGGER.info(
        "<Review(id=%s)>: found %s duplicate and %s non-duplicate citations",
        review_id,
        len(duplicate_cids),
        len(non_duplicate_cids),
    )

    lock.release()


@shared_task
def get_citations_text_content_vectors(review_id: int):
    lock = _get_redis_lock(f"get_citations_text_content_vectors__review-{review_id}")
    lock.acquire()

    lang_models = nlp_utils.get_lang_to_models()
    stmt = (
        sa.select(Citation.id, Citation.text_content)
        .where(Citation.review_id == review_id)
        .where(Citation.text_content_vector_rep == [])
        .order_by(Citation.id)
    )
    results = db.session.execute(stmt)
    citation_id_docs = (
        (
            id_,
            nlp_utils.make_spacy_doc_if_possible(
                text, lang_models, disable=("tagger", "parser", "ner")
            ),
        )
        for id_, text in results
    )
    citations_to_update = []
    for id_, spacy_doc in citation_id_docs:
        if spacy_doc is None:
            continue

        try:
            citations_to_update.append(
                {"id": id_, "text_content_vector_rep": spacy_doc.vector.tolist()}
            )
        except Exception:
            pass  # no vector available presumably

    if not citations_to_update:
        LOGGER.warning(
            "<Review(id=%s)>: no citation text_content_vector_reps to update",
            review_id,
        )
        lock.release()
        return

    db.session.bulk_update_mappings(Citation, citations_to_update)
    db.session.commit()
    LOGGER.info(
        "<Review(id=%s)>: %s citation text_content_vector_reps updated",
        review_id,
        len(citations_to_update),
    )

    lock.release()


@shared_task
def get_fulltext_text_content_vector(fulltext_id: int):
    stmt = sa.select(Fulltext.text_content).where(Fulltext.id == fulltext_id)
    text_content = db.session.execute(stmt).scalar_one_or_none()
    if not text_content:
        LOGGER.warning(
            "no fulltext text content found for <Fulltext(study_id=%s)>", fulltext_id
        )
        return

    lang_models = nlp_utils.get_lang_to_models()
    spacy_doc = nlp_utils.make_spacy_doc_if_possible(
        text_content, lang_models, disable=("tagger", "parser", "ner")
    )
    if spacy_doc is None:
        return

    try:
        text_content_vector_rep = spacy_doc.vector.tolist()
    except ValueError:
        LOGGER.warning(
            "unable to get  word vectors for <Fulltext(study_id=%s)>", fulltext_id
        )
        return

    stmt = (
        sa.update(Fulltext)
        .where(Fulltext.id == fulltext_id)
        .values(text_content_vector_rep=text_content_vector_rep)
    )
    db.session.execute(stmt)
    db.session.commit()


@shared_task
def suggest_keyterms(review_id, sample_size):
    lock = _get_redis_lock(f"suggest_keyterms__review-{review_id}")
    lock.acquire()

    LOGGER.info(
        "<Review(id=%s)>: computing keyterms with sample size = %s",
        review_id,
        sample_size,
    )

    # get random sample of included citations
    stmt = (
        sa.select(Study.citation_status, Citation.text_content)
        .where(Study.id == Citation.id)
        .where(Study.review_id == review_id)
        .where(Study.citation_status == "included")
        .order_by(sa.func.random())
        .limit(sample_size)
    )
    included = db.session.execute(stmt).all()
    # get random sample of excluded citations
    stmt = (
        sa.select(Study.citation_status, Citation.text_content)
        .where(Study.id == Citation.id)
        .where(Study.review_id == review_id)
        .where(Study.citation_status == "excluded")
        .order_by(sa.func.random())
        .limit(sample_size)
    )
    excluded = db.session.execute(stmt).all()

    # munge the results into the form needed by textacy
    included_vec = [
        status == "included" for status, _ in itertools.chain(included, excluded)
    ]
    lang_models = nlp_utils.get_lang_to_models()
    docs = (
        nlp_utils.make_spacy_doc_if_possible(text, lang_models)
        for _, text in itertools.chain(included, excluded)
    )
    terms_lists = (
        doc._.to_terms_list(include_pos={"NOUN", "VERB"}, as_strings=True)
        for doc in docs
        if doc is not None
    )
    # run the analysis!
    incl_keyterms, excl_keyterms = hack.most_discriminating_terms(
        terms_lists, included_vec, top_n_terms=50
    )

    # munge results into form expected by the database, and validate
    suggested_keyterms = {
        "sample_size": sample_size,
        "incl_keyterms": incl_keyterms,
        "excl_keyterms": excl_keyterms,
    }
    errors = ReviewPlanSuggestedKeyterms().validate(suggested_keyterms)
    if errors:
        lock.release()
        raise Exception
    LOGGER.info(
        "<Review(id=%s)>: suggested keyterms: %s", review_id, suggested_keyterms
    )
    # update the review plan
    stmt = (
        sa.update(ReviewPlan)
        .where(ReviewPlan.id == review_id)
        .values(suggested_keyterms=suggested_keyterms)
    )
    db.session.execute(stmt)
    db.session.commit()

    lock.release()


@shared_task
def train_citation_ranking_model(review_id):
    lock = _get_redis_lock(f"train_citations_ranking_model__review-{review_id}")
    lock.acquire()

    LOGGER.info("<Review(id=%s)>: training citation ranking model", review_id)

    # make sure at least some citations have had their text content vectors found
    n_iters = 1
    while True:
        stmt = sa.select(
            sa.exists()
            .where(Citation.review_id == review_id)
            .where(Citation.text_content_vector_rep != [])
        )
        citations_ready = db.session.execute(stmt).scalar_one()
        if citations_ready is True:
            break
        else:
            LOGGER.debug(
                "<Review(id=%s)>: waiting for vectorized text content for, %s",
                review_id,
                n_iters,
            )
            time.sleep(30)
        if n_iters > 6:
            LOGGER.error(
                "<Review(id=%s)>: no citations with vectorized text content found",
                review_id,
            )
            lock.release()
            return
        n_iters += 1

    # TODO: should this be a random sample? i think no, but old comment said yes
    # get included citations
    stmt = (
        sa.select(Citation.text_content_vector_rep, Study.citation_status)
        .where(Study.id == Citation.id)
        .where(Study.review_id == review_id)
        .where(Study.dedupe_status == "not_duplicate")
        .where(Study.citation_status.in_(["included", "excluded"]))
        .where(Citation.text_content_vector_rep != [])
    )
    results = db.session.execute(stmt)
    feature_vecs, labels = zip(*results)
    ranker = Ranker(review_id=review_id)
    ranker.fit(feature_vecs, labels)
    ranker.save(os.path.join(current_app.config["RANKING_MODELS_DIR"], str(review_id)))

    lock.release()
