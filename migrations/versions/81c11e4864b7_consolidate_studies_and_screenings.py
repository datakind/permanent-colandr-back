"""consolidate studies and screenings

Revision ID: 81c11e4864b7
Revises: afbfc506e91a
Create Date: 2024-04-17 01:55:50.074669

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "81c11e4864b7"
down_revision = "afbfc506e91a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
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
                citation_id as study_id,
                'citation' as stage,
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
                fulltext_id as study_id,
                'fulltext' as stage,
                status,
                exclude_reasons
            FROM fulltext_screenings
        )
        ORDER BY created_at ASC
        """
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

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
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
    # ### end Alembic commands ###