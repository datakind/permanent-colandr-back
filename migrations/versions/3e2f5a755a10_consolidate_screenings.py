"""consolidate screenings

Revision ID: 3e2f5a755a10
Revises: afbfc506e91a
Create Date: 2024-04-18 00:37:03.632771

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "3e2f5a755a10"
down_revision = "afbfc506e91a"
branch_labels = None
depends_on = None


def upgrade():
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

    # ### end Alembic commands ###


def downgrade():
    op.execute("DELETE FROM citation_screenings")
    op.execute("DELETE FROM fulltext_screenings")
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

    with op.batch_alter_table("screenings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_screenings_user_id"))
        batch_op.drop_index("ix_screenings_study_id_stage")
        batch_op.drop_index(batch_op.f("ix_screenings_status"))
        batch_op.drop_index(batch_op.f("ix_screenings_review_id"))

    op.drop_table("screenings")
    # ### end Alembic commands ###
