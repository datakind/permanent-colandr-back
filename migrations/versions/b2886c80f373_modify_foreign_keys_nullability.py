"""modify foreign keys nullability

Revision ID: b2886c80f373
Revises: 1c023402f9d8
Create Date: 2023-07-18 01:44:48.462861

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "b2886c80f373"
down_revision = "1c023402f9d8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("studies") as batch_op:
        batch_op.alter_column("user_id", existing_nullable=False, nullable=True)
        batch_op.alter_column("data_source_id", existing_nullable=False, nullable=True)

    with op.batch_alter_table("imports") as batch_op:
        batch_op.alter_column("user_id", existing_nullable=False, nullable=True)
        batch_op.alter_column("data_source_id", existing_nullable=False, nullable=True)

    op.alter_column(
        "citation_screenings", "user_id", existing_nullable=False, nullable=True
    )
    op.alter_column(
        "fulltext_screenings", "user_id", existing_nullable=False, nullable=True
    )

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table("studies") as batch_op:
        batch_op.alter_column("user_id", existing_nullable=True, nullable=False)
        batch_op.alter_column("data_source_id", existing_nullable=True, nullable=False)

    with op.batch_alter_table("imports") as batch_op:
        batch_op.alter_column("user_id", existing_nullable=True, nullable=False)
        batch_op.alter_column("data_source_id", existing_nullable=True, nullable=False)

    op.alter_column(
        "citation_screenings", "user_id", existing_nullable=True, nullable=False
    )
    op.alter_column(
        "fulltext_screenings", "user_id", existing_nullable=True, nullable=False
    )

    # ### end Alembic commands ###
