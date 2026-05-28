"""adiciona login com google

Revision ID: 8f3b6a4d2c10
Revises: 369ad7576909
Create Date: 2026-05-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f3b6a4d2c10'
down_revision = '369ad7576909'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('usuarios', sa.Column('google_id', sa.String(length=120), nullable=True))
    op.add_column('usuarios', sa.Column('foto_url', sa.String(length=500), nullable=True))
    op.add_column(
        'usuarios',
        sa.Column('auth_provider', sa.String(length=30), server_default='local', nullable=False),
    )
    op.alter_column('usuarios', 'senha_hash', existing_type=sa.String(length=255), nullable=True)
    op.create_index(op.f('ix_usuarios_google_id'), 'usuarios', ['google_id'], unique=True)
    op.alter_column('usuarios', 'auth_provider', server_default=None)


def downgrade():
    op.drop_index(op.f('ix_usuarios_google_id'), table_name='usuarios')
    op.alter_column('usuarios', 'senha_hash', existing_type=sa.String(length=255), nullable=False)
    op.drop_column('usuarios', 'auth_provider')
    op.drop_column('usuarios', 'foto_url')
    op.drop_column('usuarios', 'google_id')
