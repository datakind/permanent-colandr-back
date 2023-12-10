"""add new review users association table

Revision ID: 9a941c4cd94e
Revises: 10e30b838ff6
Create Date: 2023-12-05 02:29:15.656167

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9a941c4cd94e"
down_revision = "10e30b838ff6"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "review_user_assoc",
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "user_role", sa.Text(), server_default=sa.text("'member'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id", "user_id"),
    )

    op.execute(
        "INSERT INTO review_user_assoc "
        "SELECT review_id, user_id FROM users_to_reviews"
    )
    op.execute(
        """
        MERGE INTO review_user_assoc AS rua
        USING reviews AS r
        ON rua.review_id = r.id AND rua.user_id = r.owner_user_id
        WHEN MATCHED THEN
            UPDATE SET user_role = 'owner'
        WHEN NOT MATCHED THEN
            INSERT (review_id, user_id)
            VALUES (r.id, r.owner_user_id)
        """
    )

    with op.batch_alter_table("users_to_reviews", schema=None) as batch_op:
        batch_op.drop_index("ix_users_to_reviews_review_id")
        batch_op.drop_index("ix_users_to_reviews_user_id")
    op.drop_table("users_to_reviews")

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_index("ix_reviews_owner_user_id")
        batch_op.drop_constraint("reviews_owner_user_id_fkey", type_="foreignkey")
        batch_op.drop_column("owner_user_id")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_user_id",
                sa.INTEGER(),
                autoincrement=False,
                # temporarily allow this to be nullable
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "reviews_owner_user_id_fkey",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_reviews_owner_user_id", ["owner_user_id"], unique=False
        )

    op.create_table(
        "users_to_reviews",
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("review_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.id"], name="users_to_reviews_review_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="users_to_reviews_user_id_fkey"
        ),
    )
    with op.batch_alter_table("users_to_reviews", schema=None) as batch_op:
        batch_op.create_index("ix_users_to_reviews_user_id", ["user_id"], unique=False)
        batch_op.create_index(
            "ix_users_to_reviews_review_id", ["review_id"], unique=False
        )

    op.execute(
        """
        INSERT INTO users_to_reviews
        SELECT user_id, review_id FROM review_user_assoc
        """
    )
    op.execute(
        """
        UPDATE reviews AS r
        SET owner_user_id = rua.user_id
        FROM review_user_assoc AS rua
        WHERE
            r.id = rua.review_id
            AND rua.user_role = 'owner'
        """
    )

    op.drop_table("review_user_assoc")

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.alter_column("owner_user_id", nullable=False)

    # ### end Alembic commands ###