"""baseline do schema atual

Revision ID: 369ad7576909
Revises: 
Create Date: 2026-05-20 11:08:46.404458

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '369ad7576909'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('senha_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'perfil',
            sa.Enum('aluno', 'monitor', 'professor', 'admin', name='perfil_usuario'),
            nullable=False,
        ),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)

    op.create_table(
        'disciplinas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('codigo', sa.String(length=30), nullable=False),
        sa.Column('professor_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['professor_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_disciplinas_codigo'), 'disciplinas', ['codigo'], unique=True)

    op.create_table(
        'monitorias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('disciplina_id', sa.Integer(), nullable=False),
        sa.Column('monitor_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['disciplina_id'], ['disciplinas.id']),
        sa.ForeignKeyConstraint(['monitor_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'horarios_monitoria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('hora_inicio', sa.Time(), nullable=False),
        sa.Column('hora_fim', sa.Time(), nullable=False),
        sa.Column('capacidade', sa.Integer(), nullable=False),
        sa.Column('monitoria_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['monitoria_id'], ['monitorias.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'atendimentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('descricao_duvida', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('Agendado', 'Cancelado', 'Realizado', name='status_atendimento'),
            nullable=False,
        ),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('horario_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['horario_id'], ['horarios_monitoria.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aluno_id', 'horario_id', name='uq_aluno_horario'),
    )


def downgrade():
    op.drop_table('atendimentos')
    op.drop_table('horarios_monitoria')
    op.drop_table('monitorias')
    op.drop_index(op.f('ix_disciplinas_codigo'), table_name='disciplinas')
    op.drop_table('disciplinas')
    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')

    status_atendimento = sa.Enum(
        'Agendado',
        'Cancelado',
        'Realizado',
        name='status_atendimento',
    )
    status_atendimento.drop(op.get_bind(), checkfirst=True)

    perfil_usuario = sa.Enum(
        'aluno',
        'monitor',
        'professor',
        'admin',
        name='perfil_usuario',
    )
    perfil_usuario.drop(op.get_bind(), checkfirst=True)
