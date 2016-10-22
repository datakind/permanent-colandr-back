"""empty message

Revision ID: 8d98ed15b29e
Revises: 5392808c47f6
Create Date: 2016-10-16 18:35:30.027236

"""

# revision identifiers, used by Alembic.
revision = '8d98ed15b29e'
down_revision = '5392808c47f6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('imports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"), nullable=True),
    sa.Column('review_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('record_type', sa.Unicode(length=10), nullable=False),
    sa.Column('num_records', sa.Integer(), nullable=False),
    sa.Column('status', sa.Unicode(length=20), server_default='not_screened', nullable=True),
    sa.Column('data_source', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), server_default='{}', nullable=True),
    sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_imports_review_id'), 'imports', ['review_id'], unique=False)
    op.create_index(op.f('ix_imports_user_id'), 'imports', ['user_id'], unique=False)
    op.add_column('citations', sa.Column('data_source', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), server_default='{}', nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('citations', 'data_source')
    op.drop_index(op.f('ix_imports_user_id'), table_name='imports')
    op.drop_index(op.f('ix_imports_review_id'), table_name='imports')
    op.drop_table('imports')
    ### end Alembic commands ###