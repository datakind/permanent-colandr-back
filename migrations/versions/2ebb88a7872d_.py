"""empty message

Revision ID: 2ebb88a7872d
Revises: 642f9119f981
Create Date: 2016-10-01 14:20:10.794442

"""

# revision identifiers, used by Alembic.
revision = '2ebb88a7872d'
down_revision = '642f9119f981'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_confirmed', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('users', sa.Column('is_admin', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'is_admin')
    op.drop_column('users', 'is_confirmed')
    ### end Alembic commands ###