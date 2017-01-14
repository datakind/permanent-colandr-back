"""empty message

Revision ID: 8189c2d935cc
Revises: c620f8df8b1c
Create Date: 2017-01-14 17:05:56.139394

"""

# revision identifiers, used by Alembic.
revision = '8189c2d935cc'
down_revision = 'c620f8df8b1c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('fulltexts', sa.Column('text_content_vector_rep', postgresql.ARRAY(sa.Float()), server_default='{}', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('fulltexts', 'text_content_vector_rep')
    # ### end Alembic commands ###
