"""add_missing_message_columns

Revision ID: 59737e37e48d
Revises: 
Create Date: 2025-11-21 01:47:55.806092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '59737e37e48d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to messages table."""
    # Add edited_at column
    op.add_column('messages', 
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add is_deleted column
    op.add_column('messages', 
        sa.Column('is_deleted', sa.String(10), nullable=False, server_default='false')
    )
    
    # Add delivered_at column
    op.add_column('messages', 
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add read_at column
    op.add_column('messages', 
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add read_by_user_id column with foreign key
    op.add_column('messages', 
        sa.Column('read_by_user_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_messages_read_by_user_id',
        'messages', 'users',
        ['read_by_user_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index on read_by_user_id for better query performance
    op.create_index(
        'idx_messages_read_by_user_id',
        'messages',
        ['read_by_user_id']
    )


def downgrade() -> None:
    """Remove added columns from messages table."""
    # Drop index
    op.drop_index('idx_messages_read_by_user_id', table_name='messages')
    
    # Drop foreign key
    op.drop_constraint('fk_messages_read_by_user_id', 'messages', type_='foreignkey')
    
    # Drop columns in reverse order
    op.drop_column('messages', 'read_by_user_id')
    op.drop_column('messages', 'read_at')
    op.drop_column('messages', 'delivered_at')
    op.drop_column('messages', 'is_deleted')
    op.drop_column('messages', 'edited_at')
