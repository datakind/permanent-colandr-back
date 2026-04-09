"""stop sharing study pkeys

Revision ID: ff8fa67b9273
Revises: 6899968b51c0
Create Date: 2024-04-27 23:44:58.876593

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "ff8fa67b9273"
down_revision = "6899968b51c0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "data_extractions", schema=None, recreate="always"
    ) as batch_op:
        batch_op.add_column(
            sa.Column("study_id", sa.BigInteger(), nullable=True),
            insert_before="review_id",
        )
    op.execute("UPDATE data_extractions SET study_id = id")
    with op.batch_alter_table("data_extractions", schema=None) as batch_op:
        batch_op.alter_column("study_id", existing_type=sa.BigInteger(), nullable=False)
        batch_op.create_index(
            batch_op.f("ix_data_extractions_study_id"), ["study_id"], unique=True
        )
        batch_op.drop_constraint("data_extractions_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "data_extractions_study_id_fkey",
            "studies",
            ["study_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("dedupes", schema=None, recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("study_id", sa.BigInteger(), nullable=True),
            insert_before="review_id",
        )
    op.execute("UPDATE dedupes SET study_id = id")
    with op.batch_alter_table("dedupes", schema=None) as batch_op:
        batch_op.alter_column("study_id", existing_type=sa.BigInteger(), nullable=False)
        batch_op.create_index(
            batch_op.f("ix_dedupes_study_id"), ["study_id"], unique=True
        )
        batch_op.drop_constraint("dedupes_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "dedupes_study_id_fkey", "studies", ["study_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("data_sources", schema=None) as batch_op:
        batch_op.drop_constraint("source_type_source_name_uc", type_="unique")
        batch_op.create_unique_constraint(
            "uq_source_type_name_url",
            ["source_type", "source_name", "source_url"],
            postgresql_nulls_not_distinct=True,
        )


def downgrade():
    with op.batch_alter_table("data_sources", schema=None) as batch_op:
        batch_op.drop_constraint("uq_source_type_name_url", type_="unique")
        batch_op.create_unique_constraint(
            "source_type_source_name_uc", ["source_type", "source_name"]
        )

    op.execute("UPDATE dedupes SET id = study_id")
    with op.batch_alter_table("dedupes", schema=None) as batch_op:
        batch_op.drop_constraint("dedupes_study_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "dedupes_id_fkey", "studies", ["id"], ["id"], ondelete="CASCADE"
        )
        batch_op.drop_index(batch_op.f("ix_dedupes_study_id"))
        batch_op.drop_column("study_id")

    op.execute("UPDATE data_extractions SET id = study_id")
    with op.batch_alter_table("data_extractions", schema=None) as batch_op:
        batch_op.drop_constraint("data_extractions_study_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "data_extractions_id_fkey", "studies", ["id"], ["id"], ondelete="CASCADE"
        )
        batch_op.drop_index(batch_op.f("ix_data_extractions_study_id"))
        batch_op.drop_column("study_id")
