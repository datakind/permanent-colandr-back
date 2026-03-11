"""fix-borked-bigserial-cols-if-needed

Revision ID: 9c67b9d5e01e
Revises: 3143eb18a369
Create Date: 2026-03-11 13:07:30.838743

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "9c67b9d5e01e"
down_revision = "3143eb18a369"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # data_extractions pkey: int8 => bigserial (?)
    column_default = conn.execute(
        sa.text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'data_extractions' AND column_name = 'id'"
        )
    ).scalar()
    # column_default is null or missing "nextval" if it's plain int8 w/o a sequence default
    if column_default is None or "nextval" not in column_default:
        conn.execute(
            sa.text(
                "CREATE SEQUENCE IF NOT EXISTS data_extractions_id_seq "
                "AS bigint OWNED BY data_extractions.id"
            )
        )
        conn.execute(
            sa.text(
                "SELECT setval('data_extractions_id_seq', "
                "(SELECT COALESCE(MAX(id), 1) FROM data_extractions))"
            )
        )
        conn.execute(
            sa.text(
                "ALTER TABLE data_extractions "
                "ALTER COLUMN id SET DEFAULT nextval('data_extractions_id_seq')"
            )
        )

    # dedupes pkey: int8 => bigserial (?)
    column_default = conn.execute(
        sa.text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'dedupes' AND column_name = 'id'"
        )
    ).scalar()
    # column_default is null or missing "nextval" if it's plain int8 w/o a sequence default
    if column_default is None or "nextval" not in column_default:
        conn.execute(
            sa.text(
                "CREATE SEQUENCE IF NOT EXISTS dedupes_id_seq "
                "AS bigint OWNED BY dedupes.id"
            )
        )
        conn.execute(
            sa.text(
                "SELECT setval('dedupes_id_seq', "
                "(SELECT COALESCE(MAX(id), 1) FROM dedupes))"
            )
        )
        conn.execute(
            sa.text(
                "ALTER TABLE dedupes "
                "ALTER COLUMN id SET DEFAULT nextval('dedupes_id_seq')"
            )
        )


def downgrade():
    # restoring a plain int8 is probably not desirable;
    # leave downgrade as a no-op or implement as needed
    pass
