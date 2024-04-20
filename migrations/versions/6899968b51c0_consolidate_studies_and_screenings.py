"""consolidate studies and screenings

Revision ID: 6899968b51c0
Revises: afbfc506e91a
Create Date: 2024-04-19 01:53:48.112143

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "6899968b51c0"
down_revision = "afbfc506e91a"
branch_labels = None
depends_on = None


def upgrade():
    # citation+fulltext screenings => screenings
    op.create_table(
        "screenings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.BigInteger(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "exclude_reasons", postgresql.ARRAY(sa.String(length=64)), nullable=True
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "review_id",
            "study_id",
            "stage",
            name="uq_screenings_user_review_study_stage",
        ),
    )
    with op.batch_alter_table("screenings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_screenings_review_id"), ["review_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_screenings_status"), ["status"], unique=False
        )
        batch_op.create_index(
            "ix_screenings_study_id_stage", ["study_id", "stage"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_screenings_user_id"), ["user_id"], unique=False
        )

    op.execute(
        """
        INSERT INTO screenings (
            created_at,
            updated_at,
            user_id,
            review_id,
            study_id,
            stage,
            status,
            exclude_reasons
        )
        (
            SELECT
                created_at,
                updated_at,
                user_id,
                review_id,
                citation_id AS study_id,
                'citation' AS stage,
                status,
                exclude_reasons
            FROM citation_screenings
        )
        UNION ALL
        (
            SELECT
                created_at,
                updated_at,
                user_id,
                review_id,
                fulltext_id AS study_id,
                'fulltext' AS stage,
                status,
                exclude_reasons
            FROM fulltext_screenings
        )
        ORDER BY created_at ASC
        """
    )

    # citations+fulltexts => studies
    with op.batch_alter_table("studies", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "citation",
                postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "citation_text_content_vector_rep",
                postgresql.ARRAY(sa.Float()),
                server_default="{}",
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "fulltext",
                postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
                nullable=True,
            )
        )

    op.execute(
        """
        UPDATE studies
        SET
            citation = c.citation,
            citation_text_content_vector_rep = c.citation_text_content_vector_rep
        FROM (
            SELECT
                id,
                json_build_object(
                    'type_of_work', type_of_work,
                    'title', title,
                    'secondary_title', secondary_title,
                    'abstract', abstract,
                    'pub_year', pub_year,
                    'pub_month', pub_month,
                    'authors', authors,
                    'keywords', keywords,
                    'type_of_reference', type_of_reference,
                    'journal_name', journal_name,
                    'volume', volume,
                    'issue_number', issue_number,
                    'doi', doi,
                    'issn', issn,
                    'publisher', publisher,
                    'language', "language",
                    'other_fields', other_fields
                ) AS citation,
                text_content_vector_rep AS citation_text_content_vector_rep
            FROM citations
        ) AS c
        WHERE studies.id = c.id
        """
    )
    op.execute(
        """
        UPDATE studies
        SET fulltext = f.fulltext
        FROM (
            SELECT
                id,
                json_build_object(
                    'filename', filename,
                    'original_filename', original_filename,
                    'text_content', text_content,
                    'text_content_vector_rep', text_content_vector_rep
                ) AS fulltext
            FROM fulltexts
        ) AS f
        WHERE studies.id = f.id
        """
    )

    # drop unnecessary tables
    with op.batch_alter_table("citation_screenings", schema=None) as batch_op:
        batch_op.drop_index("ix_citation_screenings_citation_id")
        batch_op.drop_index("ix_citation_screenings_review_id")
        batch_op.drop_index("ix_citation_screenings_status")
        batch_op.drop_index("ix_citation_screenings_user_id")
    op.drop_table("citation_screenings")

    with op.batch_alter_table("fulltext_screenings", schema=None) as batch_op:
        batch_op.drop_index("ix_fulltext_screenings_fulltext_id")
        batch_op.drop_index("ix_fulltext_screenings_review_id")
        batch_op.drop_index("ix_fulltext_screenings_status")
        batch_op.drop_index("ix_fulltext_screenings_user_id")
    op.drop_table("fulltext_screenings")

    with op.batch_alter_table("citations", schema=None) as batch_op:
        batch_op.drop_index("ix_citations_review_id")
    op.drop_table("citations")

    with op.batch_alter_table("fulltexts", schema=None) as batch_op:
        batch_op.drop_index("ix_fulltexts_review_id")
    op.drop_table("fulltexts")


def downgrade():
    # studies => citations+fulltexts
    op.create_table(
        "citations",
        sa.Column("id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("review_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "type_of_work", sa.VARCHAR(length=25), autoincrement=False, nullable=True
        ),
        sa.Column(
            "title",
            sa.VARCHAR(length=300),
            server_default=sa.text("'untitled'::character varying"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "secondary_title",
            sa.VARCHAR(length=300),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("abstract", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("pub_year", sa.SMALLINT(), autoincrement=False, nullable=True),
        sa.Column("pub_month", sa.SMALLINT(), autoincrement=False, nullable=True),
        sa.Column(
            "authors",
            postgresql.ARRAY(sa.VARCHAR(length=100)),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.VARCHAR(length=100)),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "type_of_reference",
            sa.VARCHAR(length=50),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "journal_name", sa.VARCHAR(length=100), autoincrement=False, nullable=True
        ),
        sa.Column("volume", sa.VARCHAR(length=20), autoincrement=False, nullable=True),
        sa.Column(
            "issue_number", sa.VARCHAR(length=20), autoincrement=False, nullable=True
        ),
        sa.Column("doi", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.Column("issn", sa.VARCHAR(length=20), autoincrement=False, nullable=True),
        sa.Column(
            "publisher", sa.VARCHAR(length=100), autoincrement=False, nullable=True
        ),
        sa.Column(
            "language", sa.VARCHAR(length=50), autoincrement=False, nullable=True
        ),
        sa.Column(
            "other_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "text_content_vector_rep",
            postgresql.ARRAY(sa.DOUBLE_PRECISION(precision=53)),
            server_default=sa.text("'{}'::double precision[]"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["id"], ["studies.id"], name="citations_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name="citations_review_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="citations_pkey"),
        postgresql_ignore_search_path=False,
    )
    with op.batch_alter_table("citations", schema=None) as batch_op:
        batch_op.create_index("ix_citations_review_id", ["review_id"], unique=False)

    op.create_table(
        "fulltexts",
        sa.Column("id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("review_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "filename", sa.VARCHAR(length=30), autoincrement=False, nullable=True
        ),
        sa.Column(
            "original_filename", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
        sa.Column("text_content", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "text_content_vector_rep",
            postgresql.ARRAY(sa.DOUBLE_PRECISION(precision=53)),
            server_default=sa.text("'{}'::double precision[]"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["id"], ["studies.id"], name="fulltexts_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name="fulltexts_review_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="fulltexts_pkey"),
        sa.UniqueConstraint("filename", name="fulltexts_filename_key"),
    )
    with op.batch_alter_table("fulltexts", schema=None) as batch_op:
        batch_op.create_index("ix_fulltexts_review_id", ["review_id"], unique=False)

    op.execute(
        """
        INSERT INTO citations (
            id,
            created_at,
            updated_at,
            review_id,
            type_of_work,
            title,
            secondary_title,
            abstract,
            pub_year,
            pub_month,
            authors,
            keywords,
            type_of_reference,
            journal_name,
            volume,
            issue_number,
            doi,
            issn,
            publisher,
            "language",
            other_fields,
            text_content_vector_rep
        )
        SELECT
            id,
            created_at,
            updated_at,
            review_id,
            citation ->> 'type_of_work' AS type_of_work,
            citation ->> 'title' AS title,
            citation ->> 'secondary_title' AS secondary_title,
            citation ->> 'abstract' AS abstract,
            citation ->> 'pub_year' AS pub_year,
            citation ->> 'pub_month' AS pub_month,
            citation ->> 'authors' AS authors,
            citation ->> 'keywords' AS keywords,
            citation ->> 'type_of_reference' AS type_of_reference,
            citation ->> 'journal_name' AS journal_name,
            citation ->> 'volume' AS volume,
            citation ->> 'issue_number' AS issue_number,
            citation ->> 'doi' AS doi,
            citation ->> 'issn' AS issn,
            citation ->> 'publisher' AS publisher,
            citation ->> 'language' AS language,
            citation ->> 'other_fields' AS other_fields,
            text_content_vector_rep
        FROM studies
        ORDER BY created_at ASC
        """
    )

    op.execute(
        """
        INSERT INTO fulltexts (
            id,
            created_at,
            updated_at,
            review_id,
            filename,
            original_filename,
            text_content,
            text_content_vector_rep
        )
        SELECT
            id,
            created_at,
            updated_at,
            review_id,
            fulltext ->> 'filename' AS filename,
            fulltext ->> 'original_filename' AS original_filename,
            fulltext ->> 'text_content' AS text_content,
            fulltext ->> 'text_content_vector_rep' AS text_content_vector_rep
        FROM studies
        ORDER BY created_at ASC
        """
    )

    # screenings => citation+fulltext screenings
    op.create_table(
        "citation_screenings",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("review_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("citation_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column("status", sa.VARCHAR(length=20), autoincrement=False, nullable=False),
        sa.Column(
            "exclude_reasons",
            postgresql.ARRAY(sa.VARCHAR(length=64)),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["citation_id"],
            ["citations.id"],
            name="citation_screenings_citation_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name="citation_screenings_review_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="citation_screenings_user_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="citation_screenings_pkey"),
        sa.UniqueConstraint(
            "review_id", "user_id", "citation_id", name="review_user_citation_uc"
        ),
    )
    with op.batch_alter_table("citation_screenings", schema=None) as batch_op:
        batch_op.create_index(
            "ix_citation_screenings_user_id", ["user_id"], unique=False
        )
        batch_op.create_index("ix_citation_screenings_status", ["status"], unique=False)
        batch_op.create_index(
            "ix_citation_screenings_review_id", ["review_id"], unique=False
        )
        batch_op.create_index(
            "ix_citation_screenings_citation_id", ["citation_id"], unique=False
        )

    op.create_table(
        "fulltext_screenings",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("review_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("fulltext_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column("status", sa.VARCHAR(length=20), autoincrement=False, nullable=False),
        sa.Column(
            "exclude_reasons",
            postgresql.ARRAY(sa.VARCHAR(length=64)),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["fulltext_id"],
            ["fulltexts.id"],
            name="fulltext_screenings_fulltext_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name="fulltext_screenings_review_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fulltext_screenings_user_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="fulltext_screenings_pkey"),
        sa.UniqueConstraint(
            "review_id", "user_id", "fulltext_id", name="review_user_fulltext_uc"
        ),
    )
    with op.batch_alter_table("fulltext_screenings", schema=None) as batch_op:
        batch_op.create_index(
            "ix_fulltext_screenings_user_id", ["user_id"], unique=False
        )
        batch_op.create_index("ix_fulltext_screenings_status", ["status"], unique=False)
        batch_op.create_index(
            "ix_fulltext_screenings_review_id", ["review_id"], unique=False
        )
        batch_op.create_index(
            "ix_fulltext_screenings_fulltext_id", ["fulltext_id"], unique=False
        )

    op.execute(
        """
        INSERT INTO citation_screenings (
            created_at,
            updated_at,
            user_id,
            review_id,
            citation_id,
            status,
            exclude_reasons
        )
        SELECT
            created_at,
            updated_at,
            user_id,
            review_id,
            study_id AS citation_id,
            status,
            exclude_reasons
        FROM screenings
        WHERE stage ='citation'
        ORDER BY created_at ASC
        """
    )
    op.execute(
        """
        INSERT INTO fulltext_screenings (
            created_at,
            updated_at,
            user_id,
            review_id,
            fulltext_id,
            status,
            exclude_reasons
        )
        SELECT
            created_at,
            updated_at,
            user_id,
            review_id,
            study_id AS fulltext_id,
            status,
            exclude_reasons
        FROM screenings
        WHERE stage ='fulltext'
        ORDER BY created_at ASC
        """
    )

    with op.batch_alter_table("studies", schema=None) as batch_op:
        batch_op.drop_column("fulltext")
        batch_op.drop_column("citation_text_content_vector_rep")
        batch_op.drop_column("citation")

    with op.batch_alter_table("screenings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_screenings_user_id"))
        batch_op.drop_index("ix_screenings_study_id_stage")
        batch_op.drop_index(batch_op.f("ix_screenings_status"))
        batch_op.drop_index(batch_op.f("ix_screenings_review_id"))
    op.drop_table("screenings")
