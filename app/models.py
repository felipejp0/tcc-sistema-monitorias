import hashlib
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(120), unique=True, nullable=True, index=True)
    foto_url = db.Column(db.String(500), nullable=True)
    auth_provider = db.Column(db.String(30), nullable=False, default="local")

    perfil = db.Column(
        db.Enum("aluno", "monitor", "professor", "admin", name="perfil_usuario"),
        nullable=False,
        default="aluno"
    )

    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    disciplinas = db.relationship("Disciplina", backref="professor", lazy=True)
    monitorias_monitor = db.relationship("Monitoria", backref="monitor", lazy=True)
    atendimentos = db.relationship("Atendimento", backref="aluno", lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        if not self.senha_hash:
            return False
        return check_password_hash(self.senha_hash, senha)

    @property
    def avatar_url(self):
        if self.foto_url:
            return self.foto_url

        email_normalizado = (self.email or "").strip().lower()
        email_hash = hashlib.md5(email_normalizado.encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s=220&d=identicon"


class Disciplina(db.Model):
    __tablename__ = "disciplinas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(30), nullable=False, unique=True, index=True)

    professor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    monitorias = db.relationship("Monitoria", backref="disciplina", lazy=True)


class Monitoria(db.Model):
    __tablename__ = "monitorias"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)

    disciplina_id = db.Column(
        db.Integer,
        db.ForeignKey("disciplinas.id"),
        nullable=False
    )

    monitor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    horarios = db.relationship("HorarioMonitoria", backref="monitoria", lazy=True)


class HorarioMonitoria(db.Model):
    __tablename__ = "horarios_monitoria"

    id = db.Column(db.Integer, primary_key=True)

    data = db.Column(db.Date, nullable=False)

    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)

    capacidade = db.Column(db.Integer, nullable=False, default=15)

    monitoria_id = db.Column(
        db.Integer,
        db.ForeignKey("monitorias.id"),
        nullable=False
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    atendimentos = db.relationship("Atendimento", backref="horario", lazy=True)

    @property
    def dia_semana(self):
        return self.data.weekday()


class Atendimento(db.Model):
    __tablename__ = "atendimentos"

    id = db.Column(db.Integer, primary_key=True)

    descricao_duvida = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.Enum("Agendado", "Cancelado", "Realizado", name="status_atendimento"),
        nullable=False,
        default="Agendado"
    )

    aluno_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    horario_id = db.Column(
        db.Integer,
        db.ForeignKey("horarios_monitoria.id"),
        nullable=False
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    atualizado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "aluno_id",
            "horario_id",
            name="uq_aluno_horario"
        ),
    )


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))
