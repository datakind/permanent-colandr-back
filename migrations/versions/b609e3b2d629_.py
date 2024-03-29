"""empty message

Revision ID: b609e3b2d629
Revises: 0a4a6fc5fbb3
Create Date: 2016-10-31 22:00:08.872086

"""

# revision identifiers, used by Alembic.
revision = 'b609e3b2d629'
down_revision = '0a4a6fc5fbb3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('fulltexts', sa.Column('original_filename', sa.Unicode(), nullable=True))
    op.alter_column('studies', 'citation_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False,
               existing_server_default=sa.text("'not_screened'::character varying"))
    op.alter_column('studies', 'data_extraction_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False,
               existing_server_default=sa.text("'not_started'::character varying"))
    op.alter_column('studies', 'fulltext_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False,
               existing_server_default=sa.text("'not_screened'::character varying"))
    op.drop_index('ix_studies_tags', table_name='studies')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_index('ix_studies_tags', 'studies', ['tags'], unique=False)
    op.alter_column('studies', 'fulltext_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True,
               existing_server_default=sa.text("'not_screened'::character varying"))
    op.alter_column('studies', 'data_extraction_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True,
               existing_server_default=sa.text("'not_started'::character varying"))
    op.alter_column('studies', 'citation_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True,
               existing_server_default=sa.text("'not_screened'::character varying"))
    op.drop_column('fulltexts', 'original_filename')
    ### end Alembic commands ###
