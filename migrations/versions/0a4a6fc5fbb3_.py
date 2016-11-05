"""empty message

Revision ID: 0a4a6fc5fbb3
Revises: 2d476c030c28
Create Date: 2016-10-30 19:11:43.072631

"""

# revision identifiers, used by Alembic.
revision = '0a4a6fc5fbb3'
down_revision = '2d476c030c28'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_citations_status', table_name='citations')
    op.drop_column('citations', 'status')
    op.drop_index('ix_data_extractions_status', table_name='data_extractions')
    op.drop_column('data_extractions', 'status')
    op.drop_index('ix_dedupes_status', table_name='dedupes')
    op.drop_column('dedupes', 'status')
    op.drop_index('ix_fulltexts_status', table_name='fulltexts')
    op.drop_column('fulltexts', 'status')
    op.add_column('studies', sa.Column('citation_status', sa.Unicode(length=20), server_default='not_screened', nullable=True))
    op.add_column('studies', sa.Column('data_extraction_status', sa.Unicode(length=20), server_default='not_started', nullable=True))
    op.add_column('studies', sa.Column('dedupe_status', sa.Unicode(length=20), nullable=True))
    op.add_column('studies', sa.Column('fulltext_status', sa.Unicode(length=20), server_default='not_screened', nullable=True))
    op.create_index(op.f('ix_studies_citation_status'), 'studies', ['citation_status'], unique=False)
    op.create_index(op.f('ix_studies_data_extraction_status'), 'studies', ['data_extraction_status'], unique=False)
    op.create_index(op.f('ix_studies_dedupe_status'), 'studies', ['dedupe_status'], unique=False)
    op.create_index(op.f('ix_studies_fulltext_status'), 'studies', ['fulltext_status'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_studies_fulltext_status'), table_name='studies')
    op.drop_index(op.f('ix_studies_dedupe_status'), table_name='studies')
    op.drop_index(op.f('ix_studies_data_extraction_status'), table_name='studies')
    op.drop_index(op.f('ix_studies_citation_status'), table_name='studies')
    op.drop_column('studies', 'fulltext_status')
    op.drop_column('studies', 'dedupe_status')
    op.drop_column('studies', 'data_extraction_status')
    op.drop_column('studies', 'citation_status')
    op.add_column('fulltexts', sa.Column('status', sa.VARCHAR(length=20), server_default=sa.text("'not_screened'::character varying"), autoincrement=False, nullable=False))
    op.create_index('ix_fulltexts_status', 'fulltexts', ['status'], unique=False)
    op.add_column('dedupes', sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=False))
    op.create_index('ix_dedupes_status', 'dedupes', ['status'], unique=False)
    op.add_column('data_extractions', sa.Column('status', sa.VARCHAR(length=20), server_default=sa.text("'not_started'::character varying"), autoincrement=False, nullable=False))
    op.create_index('ix_data_extractions_status', 'data_extractions', ['status'], unique=False)
    op.add_column('citations', sa.Column('status', sa.VARCHAR(length=20), server_default=sa.text("'not_screened'::character varying"), autoincrement=False, nullable=False))
    op.create_index('ix_citations_status', 'citations', ['status'], unique=False)
    ### end Alembic commands ###