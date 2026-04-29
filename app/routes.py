from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user

from app.models import Usuario, Disciplina, Monitoria, HorarioMonitoria, Atendimento
from app.extensions import db

main = Blueprint("main", __name__)


def perfil_requerido(*perfis):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.perfil not in perfis:
                flash("Você não tem permissão para acessar esta página.")
                return redirect(url_for("main.dashboard"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash("Já existe um usuário com esse e-mail.")
            return redirect(url_for("main.cadastro"))

        usuario = Usuario(nome=nome, email=email, perfil="aluno")
        usuario.set_senha(senha)

        db.session.add(usuario)
        db.session.commit()

        flash("Usuário cadastrado com sucesso!")
        return redirect(url_for("main.login"))

    return render_template("cadastro.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.check_senha(senha):
            login_user(usuario)
            return redirect(url_for("main.dashboard"))

        flash("E-mail ou senha inválidos.")

    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", usuario=current_user)


@main.route("/admin/usuarios", methods=["GET", "POST"])
@login_required
@perfil_requerido("admin")
def gerenciar_usuarios():
    usuarios = Usuario.query.all()

    if request.method == "POST":
        user_id = request.form["user_id"]
        novo_perfil = request.form["perfil"]

        usuario = Usuario.query.get(user_id)

        if usuario:
            usuario.perfil = novo_perfil
            db.session.commit()
            flash("Perfil atualizado com sucesso!")
        else:
            flash("Usuário não encontrado.")

        return redirect(url_for("main.gerenciar_usuarios"))

    return render_template("admin_usuarios.html", usuarios=usuarios)


@main.route("/disciplinas")
@login_required
def listar_disciplinas():
    disciplinas = Disciplina.query.all()
    return render_template("disciplinas.html", disciplinas=disciplinas)


@main.route("/disciplinas/nova", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor", "admin")
def nova_disciplina():
    professores = Usuario.query.filter(
        Usuario.perfil.in_(["professor", "admin"])
    ).all()

    if request.method == "POST":
        nome = request.form["nome"]
        codigo = request.form["codigo"]
        professor_id = request.form["professor_id"]

        disciplina_existente = Disciplina.query.filter_by(codigo=codigo).first()
        if disciplina_existente:
            flash("Já existe uma disciplina com esse código.")
            return redirect(url_for("main.nova_disciplina"))

        disciplina = Disciplina(
            nome=nome,
            codigo=codigo,
            professor_id=professor_id
        )

        db.session.add(disciplina)
        db.session.commit()

        flash("Disciplina cadastrada com sucesso!")
        return redirect(url_for("main.listar_disciplinas"))

    return render_template("nova_disciplina.html", professores=professores)


@main.route("/monitorias")
@login_required
def listar_monitorias():
    monitorias = Monitoria.query.all()
    return render_template("monitorias.html", monitorias=monitorias)


@main.route("/monitorias/nova", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor", "admin")
def nova_monitoria():
    disciplinas = Disciplina.query.all()
    usuarios = Usuario.query.filter(Usuario.perfil.in_(["monitor", "admin"])).all()

    if request.method == "POST":
        descricao = request.form["descricao"]
        disciplina_id = request.form["disciplina"]
        monitor_id = request.form["monitor"]

        monitoria = Monitoria(
            descricao=descricao,
            disciplina_id=disciplina_id,
            monitor_id=monitor_id
        )

        db.session.add(monitoria)
        db.session.commit()

        flash("Monitoria criada com sucesso!")
        return redirect(url_for("main.listar_monitorias"))

    return render_template(
        "nova_monitoria.html",
        disciplinas=disciplinas,
        usuarios=usuarios
    )


@main.route("/horarios")
@login_required
def listar_horarios():
    horarios = HorarioMonitoria.query.all()
    return render_template("horarios.html", horarios=horarios)


@main.route("/horarios/novo", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor", "admin")
def novo_horario():
    monitorias = Monitoria.query.all()

    if request.method == "POST":
        dia_semana = request.form["dia_semana"]
        hora_inicio = request.form["hora_inicio"]
        hora_fim = request.form["hora_fim"]
        monitoria_id = request.form["monitoria"]

        horario = HorarioMonitoria(
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            monitoria_id=monitoria_id
        )

        db.session.add(horario)
        db.session.commit()

        flash("Horário cadastrado com sucesso!")
        return redirect(url_for("main.listar_horarios"))

    return render_template("novo_horario.html", monitorias=monitorias)


@main.route("/aluno/horarios")
@login_required
@perfil_requerido("aluno")
def aluno_horarios():
    horarios = HorarioMonitoria.query.all()
    return render_template("aluno_horarios.html", horarios=horarios)


@main.route("/aluno/agendar/<int:horario_id>", methods=["GET", "POST"])
@login_required
@perfil_requerido("aluno")
def agendar_atendimento(horario_id):
    horario = HorarioMonitoria.query.get_or_404(horario_id)

    if request.method == "POST":
        descricao_duvida = request.form["descricao_duvida"]

        existe = Atendimento.query.filter_by(
            aluno_id=current_user.id,
            horario_id=horario.id
        ).first()

        if existe:
            flash("Você já está inscrito neste horário.")
            return redirect(url_for("main.aluno_horarios"))

        total = Atendimento.query.filter_by(horario_id=horario.id).count()

        if total >= horario.capacidade:
            flash("Este horário já está lotado.")
            return redirect(url_for("main.aluno_horarios"))

        atendimento = Atendimento(
            descricao_duvida=descricao_duvida,
            aluno_id=current_user.id,
            horario_id=horario.id,
            status="Agendado"
        )

        db.session.add(atendimento)
        db.session.commit()

        flash("Atendimento agendado com sucesso!")
        return redirect(url_for("main.meus_agendamentos"))

    return render_template("agendar_atendimento.html", horario=horario)


@main.route("/aluno/agendamentos")
@login_required
@perfil_requerido("aluno")
def meus_agendamentos():
    atendimentos = Atendimento.query.filter_by(aluno_id=current_user.id).all()
    return render_template("meus_agendamentos.html", atendimentos=atendimentos)


@main.route("/monitor/atendimentos")
@login_required
@perfil_requerido("monitor", "admin")
def monitor_atendimentos():
    atendimentos = Atendimento.query.join(HorarioMonitoria).join(Monitoria).filter(
        Monitoria.monitor_id == current_user.id
    ).all()

    return render_template("monitor_atendimentos.html", atendimentos=atendimentos)


@main.route("/monitor/atendimentos/<int:atendimento_id>/concluir")
@login_required
@perfil_requerido("monitor", "admin")
def concluir_atendimento(atendimento_id):
    atendimento = Atendimento.query.get_or_404(atendimento_id)

    if atendimento.horario.monitoria.monitor_id != current_user.id and current_user.perfil != "admin":
        flash("Você não tem permissão para concluir este atendimento.")
        return redirect(url_for("main.dashboard"))

    atendimento.status = "Realizado"
    db.session.commit()

    flash("Atendimento marcado como realizado.")
    return redirect(url_for("main.monitor_atendimentos"))


@main.route("/professor/atendimentos")
@login_required
@perfil_requerido("professor", "admin")
def professor_atendimentos():
    if current_user.perfil == "admin":
        atendimentos = Atendimento.query.all()
    else:
        atendimentos = Atendimento.query.join(HorarioMonitoria).join(Monitoria).join(Disciplina).filter(
            Disciplina.professor_id == current_user.id
        ).all()

    return render_template("professor_atendimentos.html", atendimentos=atendimentos)