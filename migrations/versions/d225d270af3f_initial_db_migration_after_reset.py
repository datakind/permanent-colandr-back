"""Initial db migration after reset

Revision ID: d225d270af3f
Revises:
Create Date: 2023-07-06 23:41:24.988169

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d225d270af3f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "data_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("source_type", sa.Unicode(length=20), nullable=False),
        sa.Column("source_name", sa.Unicode(length=100), nullable=True),
        sa.Column("source_url", sa.Unicode(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_name", name="source_type_source_name_uc"
        ),
    )
    with op.batch_alter_table("data_sources", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_data_sources_source_name"), ["source_name"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_data_sources_source_type"), ["source_type"], unique=False
        )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("name", sa.Unicode(length=200), nullable=False),
        sa.Column("email", sa.Unicode(length=200), nullable=False),
        sa.Column("password", sa.Unicode(length=60), nullable=False),
        sa.Column(
            "is_confirmed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=500), nullable=False),
        sa.Column("description", sa.UnicodeText(), nullable=True),
        sa.Column(
            "status", sa.Unicode(length=25), server_default="active", nullable=False
        ),
        sa.Column(
            "num_citation_screening_reviewers",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "num_fulltext_screening_reviewers",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "num_citations_included", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "num_citations_excluded", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "num_fulltexts_included", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "num_fulltexts_excluded", sa.Integer(), server_default="0", nullable=False
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reviews_owner_user_id"), ["owner_user_id"], unique=False
        )

    op.create_table(
        "dedupe_covered_blocks",
        sa.Column("citation_id", sa.BigInteger(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column(
            "sorted_ids",
            postgresql.ARRAY(sa.BigInteger()),
            server_default="{}",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("citation_id"),
    )
    with op.batch_alter_table("dedupe_covered_blocks", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dedupe_covered_blocks_citation_id"),
            ["citation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_dedupe_covered_blocks_review_id"),
            ["review_id"],
            unique=False,
        )

    op.create_table(
        "dedupe_plural_block",
        sa.Column("block_id", sa.BigInteger(), nullable=False),
        sa.Column("citation_id", sa.BigInteger(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("block_id", "citation_id"),
    )
    with op.batch_alter_table("dedupe_plural_block", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dedupe_plural_block_citation_id"),
            ["citation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_dedupe_plural_block_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "dedupe_plural_key",
        sa.Column("block_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("block_key", sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("block_id"),
        sa.UniqueConstraint("review_id", "block_key", name="review_id_block_key_uc"),
    )
    with op.batch_alter_table("dedupe_plural_key", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dedupe_plural_key_block_key"), ["block_key"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_dedupe_plural_key_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "dedupe_smaller_coverage",
        sa.Column("citation_id", sa.BigInteger(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "smaller_ids",
            postgresql.ARRAY(sa.BigInteger()),
            server_default="{}",
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("citation_id", "block_id"),
    )
    with op.batch_alter_table("dedupe_smaller_coverage", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dedupe_smaller_coverage_citation_id"),
            ["citation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_dedupe_smaller_coverage_review_id"),
            ["review_id"],
            unique=False,
        )

    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data_source_id", sa.BigInteger(), nullable=False),
        sa.Column("record_type", sa.Unicode(length=10), nullable=False),
        sa.Column("num_records", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Unicode(length=20),
            server_default="not_screened",
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"], ["data_sources.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("imports", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_imports_review_id"), ["review_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_imports_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "review_plans",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("objective", sa.UnicodeText(), nullable=True),
        sa.Column(
            "research_questions",
            postgresql.ARRAY(sa.Unicode(length=300)),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "pico",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "keyterms",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "selection_criteria",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "data_extraction_form",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "suggested_keyterms",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "studies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Unicode(length=25)),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("data_source_id", sa.Integer(), nullable=False),
        sa.Column(
            "dedupe_status",
            sa.Unicode(length=20),
            server_default="not_duplicate",
            nullable=True,
        ),
        sa.Column(
            "citation_status",
            sa.Unicode(length=20),
            server_default="not_screened",
            nullable=False,
        ),
        sa.Column(
            "fulltext_status",
            sa.Unicode(length=20),
            server_default="not_screened",
            nullable=False,
        ),
        sa.Column(
            "data_extraction_status",
            sa.Unicode(length=20),
            server_default="not_started",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"], ["data_sources.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("studies", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_studies_citation_status"), ["citation_status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_studies_data_extraction_status"),
            ["data_extraction_status"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_studies_data_source_id"), ["data_source_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_studies_dedupe_status"), ["dedupe_status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_studies_fulltext_status"), ["fulltext_status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_studies_review_id"), ["review_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_studies_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "users_to_reviews",
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("review_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
    )
    with op.batch_alter_table("users_to_reviews", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_users_to_reviews_review_id"), ["review_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_users_to_reviews_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "citations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("type_of_work", sa.Unicode(length=25), nullable=True),
        sa.Column(
            "title", sa.Unicode(length=300), server_default="untitled", nullable=False
        ),
        sa.Column("secondary_title", sa.Unicode(length=300), nullable=True),
        sa.Column("abstract", sa.UnicodeText(), nullable=True),
        sa.Column("pub_year", sa.SmallInteger(), nullable=True),
        sa.Column("pub_month", sa.SmallInteger(), nullable=True),
        sa.Column("authors", postgresql.ARRAY(sa.Unicode(length=100)), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.Unicode(length=100)), nullable=True),
        sa.Column("type_of_reference", sa.Unicode(length=50), nullable=True),
        sa.Column("journal_name", sa.Unicode(length=100), nullable=True),
        sa.Column("volume", sa.Unicode(length=20), nullable=True),
        sa.Column("issue_number", sa.Unicode(length=20), nullable=True),
        sa.Column("doi", sa.Unicode(length=100), nullable=True),
        sa.Column("issn", sa.Unicode(length=20), nullable=True),
        sa.Column("publisher", sa.Unicode(length=100), nullable=True),
        sa.Column("language", sa.Unicode(length=50), nullable=True),
        sa.Column(
            "other_fields",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "text_content_vector_rep",
            postgresql.ARRAY(sa.Float()),
            server_default="{}",
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("citations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_citations_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "data_extractions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column(
            "extracted_items",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("data_extractions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_data_extractions_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "dedupes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("duplicate_of", sa.BigInteger(), nullable=True),
        sa.Column("duplicate_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("dedupes", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dedupes_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "fulltexts",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Unicode(length=30), nullable=True),
        sa.Column("original_filename", sa.Unicode(), nullable=True),
        sa.Column("text_content", sa.UnicodeText(), nullable=True),
        sa.Column(
            "text_content_vector_rep",
            postgresql.ARRAY(sa.Float()),
            server_default="{}",
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filename"),
    )
    with op.batch_alter_table("fulltexts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_fulltexts_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "citation_screenings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("citation_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Unicode(length=20), nullable=False),
        sa.Column(
            "exclude_reasons", postgresql.ARRAY(sa.Unicode(length=25)), nullable=True
        ),
        sa.ForeignKeyConstraint(["citation_id"], ["citations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_id", "user_id", "citation_id", name="review_user_citation_uc"
        ),
    )
    with op.batch_alter_table("citation_screenings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_citation_screenings_citation_id"),
            ["citation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_citation_screenings_review_id"), ["review_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_citation_screenings_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_citation_screenings_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "dedupe_blocking_map",
        sa.Column("citation_id", sa.BigInteger(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("block_key", sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(["citation_id"], ["citations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("citation_id", "review_id", "block_key"),
    )
    with op.batch_alter_table("dedupe_blocking_map", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dedupe_blocking_map_block_key"), ["block_key"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_dedupe_blocking_map_citation_id"),
            ["citation_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_dedupe_blocking_map_review_id"), ["review_id"], unique=False
        )

    op.create_table(
        "fulltext_screenings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fulltext_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Unicode(length=20), nullable=False),
        sa.Column(
            "exclude_reasons", postgresql.ARRAY(sa.Unicode(length=25)), nullable=True
        ),
        sa.ForeignKeyConstraint(["fulltext_id"], ["fulltexts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_id", "user_id", "fulltext_id", name="review_user_fulltext_uc"
        ),
    )
    with op.batch_alter_table("fulltext_screenings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_fulltext_screenings_fulltext_id"),
            ["fulltext_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_fulltext_screenings_review_id"), ["review_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_fulltext_screenings_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_fulltext_screenings_user_id"), ["user_id"], unique=False
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("fulltext_screenings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fulltext_screenings_user_id"))
        batch_op.drop_index(batch_op.f("ix_fulltext_screenings_status"))
        batch_op.drop_index(batch_op.f("ix_fulltext_screenings_review_id"))
        batch_op.drop_index(batch_op.f("ix_fulltext_screenings_fulltext_id"))

    op.drop_table("fulltext_screenings")
    with op.batch_alter_table("dedupe_blocking_map", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dedupe_blocking_map_review_id"))
        batch_op.drop_index(batch_op.f("ix_dedupe_blocking_map_citation_id"))
        batch_op.drop_index(batch_op.f("ix_dedupe_blocking_map_block_key"))

    op.drop_table("dedupe_blocking_map")
    with op.batch_alter_table("citation_screenings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_citation_screenings_user_id"))
        batch_op.drop_index(batch_op.f("ix_citation_screenings_status"))
        batch_op.drop_index(batch_op.f("ix_citation_screenings_review_id"))
        batch_op.drop_index(batch_op.f("ix_citation_screenings_citation_id"))

    op.drop_table("citation_screenings")
    with op.batch_alter_table("fulltexts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fulltexts_review_id"))

    op.drop_table("fulltexts")
    with op.batch_alter_table("dedupes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dedupes_review_id"))

    op.drop_table("dedupes")
    with op.batch_alter_table("data_extractions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_data_extractions_review_id"))

    op.drop_table("data_extractions")
    with op.batch_alter_table("citations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_citations_review_id"))

    op.drop_table("citations")
    with op.batch_alter_table("users_to_reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_to_reviews_user_id"))
        batch_op.drop_index(batch_op.f("ix_users_to_reviews_review_id"))

    op.drop_table("users_to_reviews")
    with op.batch_alter_table("studies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_studies_user_id"))
        batch_op.drop_index(batch_op.f("ix_studies_review_id"))
        batch_op.drop_index(batch_op.f("ix_studies_fulltext_status"))
        batch_op.drop_index(batch_op.f("ix_studies_dedupe_status"))
        batch_op.drop_index(batch_op.f("ix_studies_data_source_id"))
        batch_op.drop_index(batch_op.f("ix_studies_data_extraction_status"))
        batch_op.drop_index(batch_op.f("ix_studies_citation_status"))

    op.drop_table("studies")
    op.drop_table("review_plans")
    with op.batch_alter_table("imports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_imports_user_id"))
        batch_op.drop_index(batch_op.f("ix_imports_review_id"))

    op.drop_table("imports")
    with op.batch_alter_table("dedupe_smaller_coverage", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dedupe_smaller_coverage_review_id"))
        batch_op.drop_index(batch_op.f("ix_dedupe_smaller_coverage_citation_id"))

    op.drop_table("dedupe_smaller_coverage")
    with op.batch_alter_table("dedupe_plural_key", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dedupe_plural_key_review_id"))
        batch_op.drop_index(batch_op.f("ix_dedupe_plural_key_block_key"))

    op.drop_table("dedupe_plural_key")
    with op.batch_alter_table("dedupe_plural_block", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dedupe_plural_block_review_id"))
        batch_op.drop_index(batch_op.f("ix_dedupe_plural_block_citation_id"))

    op.drop_table("dedupe_plural_block")
    with op.batch_alter_table("dedupe_covered_blocks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dedupe_covered_blocks_review_id"))
        batch_op.drop_index(batch_op.f("ix_dedupe_covered_blocks_citation_id"))

    op.drop_table("dedupe_covered_blocks")
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reviews_owner_user_id"))

    op.drop_table("reviews")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))

    op.drop_table("users")
    with op.batch_alter_table("data_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_data_sources_source_type"))
        batch_op.drop_index(batch_op.f("ix_data_sources_source_name"))

    op.drop_table("data_sources")
    # ### end Alembic commands ###