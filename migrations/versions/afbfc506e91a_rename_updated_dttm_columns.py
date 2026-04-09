"""rename updated dttm columns

Revision ID: afbfc506e91a
Revises: 258981e39afd
Create Date: 2023-12-19 23:21:42.858916

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "afbfc506e91a"
down_revision = "258981e39afd"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", column_name="last_updated", new_column_name="updated_at")
    op.alter_column("reviews", column_name="last_updated", new_column_name="updated_at")
    op.alter_column(
        "review_plans", column_name="last_updated", new_column_name="updated_at"
    )
    op.alter_column("studies", column_name="last_updated", new_column_name="updated_at")
    op.alter_column(
        "citations", column_name="last_updated", new_column_name="updated_at"
    )
    op.alter_column(
        "fulltexts", column_name="last_updated", new_column_name="updated_at"
    )
    op.alter_column(
        "citation_screenings", column_name="last_updated", new_column_name="updated_at"
    )
    op.alter_column(
        "fulltext_screenings", column_name="last_updated", new_column_name="updated_at"
    )
    op.alter_column(
        "data_extractions", column_name="last_updated", new_column_name="updated_at"
    )

    # ### end Alembic commands ###


def downgrade():
    op.alter_column("users", column_name="updated_at", new_column_name="last_updated")
    op.alter_column("reviews", column_name="updated_at", new_column_name="last_updated")
    op.alter_column(
        "review_plans", column_name="updated_at", new_column_name="last_updated"
    )
    op.alter_column("studies", column_name="updated_at", new_column_name="last_updated")
    op.alter_column(
        "citations", column_name="updated_at", new_column_name="last_updated"
    )
    op.alter_column(
        "fulltexts", column_name="updated_at", new_column_name="last_updated"
    )
    op.alter_column(
        "citation_screenings", column_name="updated_at", new_column_name="last_updated"
    )
    op.alter_column(
        "fulltext_screenings", column_name="updated_at", new_column_name="last_updated"
    )
    op.alter_column(
        "data_extractions", column_name="updated_at", new_column_name="last_updated"
    )

    # ### end Alembic commands ###
