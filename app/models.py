from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="aluno")

    disciplinas = db.relationship("Disciplina", backref="professor", lazy=True)
    monitorias_monitor = db.relationship("Monitoria", backref="monitor", lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Disciplina(db.Model):
    __tablename__ = "disciplinas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=True)

    professor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    monitorias = db.relationship("Monitoria", backref="disciplina", lazy=True)


class Monitoria(db.Model):
    __tablename__ = "monitorias"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)

    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    monitor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    horarios = db.relationship("HorarioMonitoria", backref="monitoria", lazy=True)


class HorarioMonitoria(db.Model):
    __tablename__ = "horarios_monitoria"

    id = db.Column(db.Integer, primary_key=True)
    dia_semana = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.String(5), nullable=False)
    hora_fim = db.Column(db.String(5), nullable=False)
    capacidade = db.Column(db.Integer, default=15)
    monitoria_id = db.Column(db.Integer, db.ForeignKey("monitorias.id"), nullable=False)


class Atendimento(db.Model):
    __tablename__ = "atendimentos"

    id = db.Column(db.Integer, primary_key=True)
    descricao_duvida = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Agendado")

    aluno_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    horario_id = db.Column(db.Integer, db.ForeignKey("horarios_monitoria.id"), nullable=False)

    aluno = db.relationship("Usuario", backref="atendimentos")
    horario = db.relationship("HorarioMonitoria", backref="atendimentos")


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))