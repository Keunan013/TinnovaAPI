"""Added initial tables

Revision ID: 9222d63c2d4f
Revises: 
Create Date: 2026-02-15 21:29:55.173337

"""
import sqlalchemy as sa

from typing import Sequence, Union
from alembic import op


# Revision identifiers, used by Alembic.
revision: str = '9222d63c2d4f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('senha_hash', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('veiculos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('placa', sa.String(), nullable=False),
    sa.Column('marca', sa.String(), nullable=False),
    sa.Column('modelo', sa.String(), nullable=False),
    sa.Column('ano', sa.Integer(), nullable=False),
    sa.Column('cor', sa.String(), nullable=False),
    sa.Column('preco_usd', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_veiculos_ano'), 'veiculos', ['ano'], unique=False)
    op.create_index(op.f('ix_veiculos_ativo'), 'veiculos', ['ativo'], unique=False)
    op.create_index(op.f('ix_veiculos_id'), 'veiculos', ['id'], unique=False)
    op.create_index(op.f('ix_veiculos_marca'), 'veiculos', ['marca'], unique=False)
    op.create_index(op.f('ix_veiculos_placa'), 'veiculos', ['placa'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_veiculos_placa'), table_name='veiculos')
    op.drop_index(op.f('ix_veiculos_marca'), table_name='veiculos')
    op.drop_index(op.f('ix_veiculos_id'), table_name='veiculos')
    op.drop_index(op.f('ix_veiculos_ativo'), table_name='veiculos')
    op.drop_index(op.f('ix_veiculos_ano'), table_name='veiculos')
    op.drop_table('veiculos')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
