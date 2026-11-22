"""enforce enum values and json array defaults

Revision ID: 35bb9df00132
Revises: 9c67b9d5e01e
Create Date: 2026-11-22 18:44:52.605418

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "35bb9df00132"
down_revision = "9c67b9d5e01e"
branch_labels = None
depends_on = None


# (table, column, check constraint name, allowed values)
ENUM_COLUMNS = (
    (
        "review_user_assoc",
        "user_role",
        "ck_review_user_assoc_user_role",
        ("owner", "member"),
    ),
    ("screenings", "stage", "ck_screenings_stage", ("citation", "fulltext")),
    ("screenings", "status", "ck_screenings_status", ("included", "excluded")),
)

# (table, column) for jsonb columns that should hold an array
JSONB_COLUMNS = (
    ("review_plans", "keyterms"),
    ("review_plans", "selection_criteria"),
    ("review_plans", "data_extraction_form"),
    ("data_extractions", "extracted_items"),
)


def _audit_enum_columns(connection: sa.Connection) -> None:
    """Raise before any DDL if a column holds a value outside its vocabulary."""
    offenders = {}
    for table, column, _, allowed in ENUM_COLUMNS:
        values = ", ".join(f"'{value}'" for value in allowed)
        rows = connection.execute(
            sa.text(
                f"SELECT {column}, count(*) FROM {table} "
                f"WHERE {column} NOT IN ({values}) "
                f"GROUP BY {column} ORDER BY 2 DESC"
            )
        ).all()
        if rows:
            offenders[f"{table}.{column}"] = [tuple(row) for row in rows]
    if offenders:
        raise RuntimeError(
            f"{offenders} are outside their allowed vocabularies; fix them by hand, "
            "then re-run this migration"
        )


def _audit_jsonb_columns(connection: sa.Connection) -> None:
    """Raise if a jsonb column holds anything other than an array (or null)."""
    offenders = {}
    for table, column in JSONB_COLUMNS:
        rows = connection.execute(
            sa.text(
                f"SELECT jsonb_typeof({column}), count(*) FROM {table} "
                f"WHERE {column} IS NOT NULL AND jsonb_typeof({column}) != 'array' "
                f"GROUP BY 1"
            )
        ).all()
        if rows:
            offenders[f"{table}.{column}"] = [tuple(row) for row in rows]
    if offenders:
        raise RuntimeError(
            f"{offenders} are not jsonb arrays; fix them by hand, "
            "then re-run this migration"
        )


def _constraint_exists(connection: sa.Connection, table: str, name: str) -> bool:
    """Whether a constraint is already on the table -- for safe re-runs.

    `ADD CONSTRAINT ... NOT VALID` and `VALIDATE CONSTRAINT` are separated by a
    transaction boundary, so a failure between them leaves the constraint in
    place with the revision unstamped.
    """
    return (
        connection.execute(
            sa.text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = :name AND conrelid = to_regclass(:table)"
            ),
            {"name": name, "table": table},
        ).scalar()
        is not None
    )


def upgrade():
    connection = op.get_bind()
    # fail fast rather than queue behind traffic on a locked table
    connection.execute(sa.text("SET LOCAL lock_timeout = '5s'"))

    _audit_enum_columns(connection)

    # empty objects and nulls become empty arrays; non-empty objects are left as-is
    # for the audit below to report
    for table, column in JSONB_COLUMNS:
        connection.execute(
            sa.text(
                f"UPDATE {table} SET {column} = '[]'::jsonb "
                f"WHERE {column} IS NULL OR {column} = '{{}}'::jsonb"
            )
        )
    _audit_jsonb_columns(connection)

    for table, column in JSONB_COLUMNS:
        op.alter_column(
            table,
            column,
            server_default=sa.text("'[]'::jsonb"),
            existing_nullable=True,
            nullable=False,
        )

    op.alter_column(
        "review_user_assoc",
        "user_role",
        type_=sa.String(length=16),
        existing_type=sa.Text(),
        existing_nullable=False,
    )

    # add unvalidated first: takes ACCESS EXCLUSIVE only for the catalog update
    # and rejects new bad rows before validation runs
    for table, column, name, allowed in ENUM_COLUMNS:
        if _constraint_exists(connection, table, name):
            continue
        values = ", ".join(f"'{value}'" for value in allowed)
        op.create_check_constraint(
            name, table, sa.text(f"{column} IN ({values})"), postgresql_not_valid=True
        )

    # validate in its own transactions: SHARE UPDATE EXCLUSIVE, which doesn't block reads/writes
    for table, _, name, _ in ENUM_COLUMNS:
        with op.get_context().autocommit_block():
            try:
                op.execute("SET lock_timeout = '60s'")
                op.execute(f"ALTER TABLE {table} VALIDATE CONSTRAINT {name}")
            finally:
                op.execute("RESET lock_timeout")


def downgrade():
    for table, _, name, _ in ENUM_COLUMNS:
        op.drop_constraint(name, table, type_="check")

    op.alter_column(
        "review_user_assoc",
        "user_role",
        type_=sa.Text(),
        existing_type=sa.String(length=16),
        existing_nullable=False,
    )

    for table, column in JSONB_COLUMNS:
        op.alter_column(
            table,
            column,
            server_default=sa.text("'{}'::jsonb"),
            existing_nullable=False,
            nullable=True,
        )
