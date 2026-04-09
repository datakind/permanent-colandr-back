"""allow dynamic num study reviewers

Revision ID: 78dbca61ed59
Revises: ff8fa67b9273
Create Date: 2024-05-07 02:47:03.793366

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "78dbca61ed59"
down_revision = "ff8fa67b9273"
branch_labels = None
depends_on = None


def upgrade():
    # add new num reviewer cols on studies
    with op.batch_alter_table("studies", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "num_citation_reviewers",
                sa.SmallInteger(),
                server_default="1",
                nullable=False,
            ),
        )
        batch_op.add_column(
            sa.Column(
                "num_fulltext_reviewers",
                sa.SmallInteger(),
                server_default="1",
                nullable=False,
            )
        )
    # data migration
    op.execute(
        """
        UPDATE studies
        SET
            num_citation_reviewers = reviews.num_citation_screening_reviewers,
            num_fulltext_reviewers = reviews.num_fulltext_screening_reviewers
        FROM reviews
        WHERE studies.review_id = reviews.id
        """
    )

    # add new num/pct cols
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "citation_reviewer_num_pcts",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text('\'[{"num": 1, "pct": 100}]\'::json'),
                nullable=False,
            ),
        )
        batch_op.add_column(
            sa.Column(
                "fulltext_reviewer_num_pcts",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text('\'[{"num": 1, "pct": 100}]\'::json'),
                nullable=False,
            ),
        )
    # adapt num reviewer cols values to num/pct equivalents
    op.execute(
        """
        UPDATE reviews
        SET
            citation_reviewer_num_pcts = json_build_array(json_build_object('num', num_citation_screening_reviewers, 'pct', 100)),
            fulltext_reviewer_num_pcts = json_build_array(json_build_object('num', num_fulltext_screening_reviewers, 'pct', 100))
        """
    )
    # delete old num reviewer cols
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_column("num_fulltext_screening_reviewers")
        batch_op.drop_column("num_citation_screening_reviewers")


def downgrade():
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "num_citation_screening_reviewers",
                sa.SMALLINT(),
                server_default=sa.text("'1'::smallint"),
                autoincrement=False,
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "num_fulltext_screening_reviewers",
                sa.SMALLINT(),
                server_default=sa.text("'1'::smallint"),
                autoincrement=False,
                nullable=False,
            )
        )
    # data de-migration
    op.execute(
        """
        UPDATE reviews
        SET
            num_citation_screening_reviewers = (citation_reviewer_num_pcts #>> '{0, num}')::smallint,
            num_fulltext_screening_reviewers = (fulltext_reviewer_num_pcts #>> '{0, num}')::smallint
        """
    )

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_column("fulltext_reviewer_num_pcts")
        batch_op.drop_column("citation_reviewer_num_pcts")

    with op.batch_alter_table("studies", schema=None) as batch_op:
        batch_op.drop_column("num_fulltext_reviewers")
        batch_op.drop_column("num_citation_reviewers")
