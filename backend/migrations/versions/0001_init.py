from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    op.create_table(
        'documents',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('page_count >= 0'),
    )

    op.create_table(
        'document_pages',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(3072), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('document_id', 'page_number', name='uq_document_pages_document_page')
    )

    op.create_table(
        'document_page_images',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('document_page_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('document_pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('dimensions', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    op.create_table(
        'chat_entries',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    # NOTE: pgvector ANN (ivfflat/hnsw) currently limits dims <= 2000. Our embeddings are 3072-d.
    # For MVP, we skip creating an ANN index and rely on ORDER BY embedding <=> query (brute-force).
    # To enable ANN later: add a reduced-dimension column (e.g., 1536/2000) and index that column.
    op.create_index('idx_document_pages_doc', 'document_pages', ['document_id'], unique=False)

def downgrade():
    op.drop_index('idx_document_pages_doc', table_name='document_pages')
    op.execute('DROP INDEX IF EXISTS idx_document_pages_embedding;')
    op.drop_table('chat_entries')
    op.drop_table('document_page_images')
    op.drop_table('document_pages')
    op.drop_table('documents')
