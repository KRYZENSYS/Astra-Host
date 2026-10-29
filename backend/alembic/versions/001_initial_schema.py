"""001_initial_schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_plan', 'users', ['plan'])
    op.create_index('idx_users_created_cursor', 'users', ['created_at', 'id'])

    # 2. nodes table
    op.create_table(
        'nodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='healthy'),
        sa.Column('total_ram_mb', sa.Integer(), nullable=False, server_default='16384'),
        sa.Column('used_ram_mb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cpu_cores', sa.Float(), nullable=False, server_default='8.0'),
        sa.Column('used_cpu_cores', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('max_bots', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('current_bots_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('idx_nodes_status_active', 'nodes', ['status', 'is_active'])

    # 3. bots table
    op.create_table(
        'bots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('node_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('entrypoint', sa.String(length=255), nullable=False, server_default='main.py'),
        sa.Column('requirements_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('container_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='stopped'),
        sa.Column('crash_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_restart_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('backoff_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_crash_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_bots_user_status', 'bots', ['user_id', 'status'])
    op.create_index('idx_bots_node_status', 'bots', ['node_id', 'status'])
    op.create_index('idx_bots_created_cursor', 'bots', ['created_at', 'id'])

    # 4. bot_env_vars table
    op.create_table(
        'bot_env_vars',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('bot_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('encrypted_value', sa.String(length=1000), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bot_env_vars_bot_id', 'bot_env_vars', ['bot_id'])

    # 5. background_jobs table
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('bot_id', sa.String(length=36), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='queued'),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stage_message', sa.String(length=255), nullable=False),
        sa.Column('result_data', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_jobs_user_status', 'background_jobs', ['user_id', 'status'])
    op.create_index('idx_jobs_created', 'background_jobs', ['created_at'])


def downgrade() -> None:
    op.drop_table('background_jobs')
    op.drop_table('bot_env_vars')
    op.drop_table('bots')
    op.drop_table('nodes')
    op.drop_table('users')
