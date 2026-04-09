"""drop review num study count cols

Revision ID: 3143eb18a369
Revises: 78dbca61ed59
Create Date: 2024-05-18 17:17:59.824499

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "3143eb18a369"
down_revision = "78dbca61ed59"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_column("num_citations_included")
        batch_op.drop_column("num_citations_excluded")
        batch_op.drop_column("num_fulltexts_included")
        batch_op.drop_column("num_fulltexts_excluded")


def downgrade():
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "num_citations_included",
                sa.INTEGER(),
                server_default=sa.text("0"),
                autoincrement=False,
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "num_citations_excluded",
                sa.INTEGER(),
                server_default=sa.text("0"),
                autoincrement=False,
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "num_fulltexts_included",
                sa.INTEGER(),
                server_default=sa.text("0"),
                autoincrement=False,
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "num_fulltexts_excluded",
                sa.INTEGER(),
                server_default=sa.text("0"),
                autoincrement=False,
                nullable=False,
            )
        )
    # data migration
    op.execute(
        """
        WITH stage_status_counts AS (
            SELECT
                review_id,
                COUNT(CASE WHEN citation_status = 'included' THEN 1 END) AS num_citations_included,
                COUNT(CASE WHEN citation_status = 'excluded' THEN 1 END) AS num_citations_excluded,
                COUNT(CASE WHEN fulltext_status = 'included' THEN 1 END) AS num_fulltexts_included,
                COUNT(CASE WHEN fulltext_status = 'excluded' THEN 1 END) AS num_fulltexts_excluded
            FROM studies
            WHERE dedupe_status = 'not_duplicate'
            GROUP BY review_id
            ORDER BY review_id
        )
        UPDATE reviews
        SET
            num_citations_included = ssc.num_citations_included,
            num_citations_excluded = ssc.num_citations_excluded,
            num_fulltexts_included = ssc.num_fulltexts_included,
            num_fulltexts_excluded = ssc.num_fulltexts_excluded
        FROM stage_status_counts AS ssc
        WHERE ssc.review_id = reviews.id
        """
    )
