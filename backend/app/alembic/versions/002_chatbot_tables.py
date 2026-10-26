"""create chatbot tables

Revision ID: 002_chatbot_tables
Revises: 001_initial
Create Date: 2026-10-23 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_chatbot_tables'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Chat Sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_sessions_id'), 'chat_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_user_id'), 'chat_sessions', ['user_id'], unique=False)

    # 2. Chat Messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('info_badge', sa.String(length=50), nullable=False, server_default='general'),
        sa.Column('citations', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('metadata_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)

    # 3. Chat Feedbacks
    op.create_table(
        'chat_feedbacks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.String(length=20), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_feedbacks_id'), 'chat_feedbacks', ['id'], unique=False)
    op.create_index(op.f('ix_chat_feedbacks_message_id'), 'chat_feedbacks', ['message_id'], unique=False)

    # 4. Knowledge Document Chunks
    op.create_table(
        'knowledge_document_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('doc_id', sa.String(length=100), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('section', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('doc_type', sa.String(length=50), nullable=False),
        sa.Column('trust_level', sa.String(length=50), nullable=False, server_default='official'),
        sa.Column('source_url', sa.String(length=255), nullable=True),
        sa.Column('last_updated', sa.String(length=50), nullable=False),
        sa.Column('embedding_json', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_knowledge_document_chunks_id'), 'knowledge_document_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_document_chunks_doc_id'), 'knowledge_document_chunks', ['doc_id'], unique=False)
    op.create_index(op.f('ix_knowledge_document_chunks_doc_type'), 'knowledge_document_chunks', ['doc_type'], unique=False)


def downgrade():
    op.drop_table('knowledge_document_chunks')
    op.drop_table('chat_feedbacks')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
