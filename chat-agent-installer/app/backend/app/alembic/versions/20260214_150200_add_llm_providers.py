"""Add LLM providers table

Revision ID: llm_providers_001
Revises: 
Create Date: 2026-02-14T15:02:00.785020

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'llm_providers_001'
down_revision = None  # Update this to the latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create llm_providers table
    op.create_table(
        'llm_providers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=True),  # Encrypted
        sa.Column('api_base', sa.String(), nullable=True),
        sa.Column('models', sa.JSON(), nullable=True),
        sa.Column('extra_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on provider_type
    op.create_index('ix_llm_providers_type', 'llm_providers', ['provider_type'])
    op.create_index('ix_llm_providers_active', 'llm_providers', ['is_active'])
    op.create_index('ix_llm_providers_default', 'llm_providers', ['is_default'])
    
    # Add llm_provider_id to messages table (if exists)
    try:
        op.add_column('messages', sa.Column('llm_provider_id', sa.String(), nullable=True))
        op.create_foreign_key(
            'fk_messages_llm_provider',
            'messages', 'llm_providers',
            ['llm_provider_id'], ['id'],
            ondelete='SET NULL'
        )
    except Exception as e:
        print(f"Note: Could not add llm_provider_id to messages table: {e}")


def downgrade() -> None:
    # Remove foreign key and column from messages
    try:
        op.drop_constraint('fk_messages_llm_provider', 'messages', type_='foreignkey')
        op.drop_column('messages', 'llm_provider_id')
    except Exception:
        pass
    
    # Drop indexes
    op.drop_index('ix_llm_providers_default', table_name='llm_providers')
    op.drop_index('ix_llm_providers_active', table_name='llm_providers')
    op.drop_index('ix_llm_providers_type', table_name='llm_providers')
    
    # Drop table
    op.drop_table('llm_providers')
