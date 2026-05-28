from functools import wraps
from datetime import datetime, date

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import or_

from app.models import Usuario, Disciplina, Monitoria, HorarioMonitoria, Atendimento
from app.extensions import db, oauth

main = Blueprint("main", __name__)

PERFIS_GERENCIAVEIS = {"aluno", "monitor", "professor", "admin"}


def perfil_requerido(*perfis):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Faça login para acessar esta página.")
                return redirect(url_for("main.login"))

            if current_user.perfil not in perfis:
                flash("Você não tem permissão para acessar esta página.")
                return redirect(url_for("main.dashboard"))

            return func(*args, **kwargs)
        return wrapper
    return decorator


def filtro_horarios_nao_encerrados():
    agora = datetime.now()
    hoje = agora.date()
    hora_atual = agora.time()

    return or_(
        HorarioMonitoria.data > hoje,
        (HorarioMonitoria.data == hoje) & (HorarioMonitoria.hora_fim > hora_atual)
    )


def filtro_horarios_agendaveis():
    agora = datetime.now()
    hoje = agora.date()
    hora_atual = agora.time()

    return or_(
        HorarioMonitoria.data > hoje,
        (HorarioMonitoria.data == hoje) & (HorarioMonitoria.hora_inicio > hora_atual)
    )


def horario_ainda_pode_ser_agendado(horario):
    data_hora_inicio = datetime.combine(
        horario.data,
        horario.hora_inicio
    )

    return data_hora_inicio > datetime.now()


def total_atendimentos_ativos(horario_id):
    return Atendimento.query.filter(
        Atendimento.horario_id == horario_id,
        Atendimento.status != "Cancelado"
    ).count()


def calcular_vagas_horario(horario):
    vagas = horario.capacidade - total_atendimentos_ativos(horario.id)
    return max(vagas, 0)


def horario_tem_vaga(horario):
    return calcular_vagas_horario(horario) > 0


def aluno_ja_tem_agendamento_ativo(aluno_id, horario_id):
    return Atendimento.query.filter(
        Atendimento.aluno_id == aluno_id,
        Atendimento.horario_id == horario_id,
        Atendimento.status != "Cancelado"
    ).first()


def professor_responsavel_pela_disciplina(disciplina):
    return (
        current_user.perfil == "admin"
        or disciplina.professor_id == current_user.id
    )


def monitor_responsavel_pelo_atendimento(atendimento):
    return atendimento.horario.monitoria.monitor_id == current_user.id


def professor_responsavel_pelo_atendimento(atendimento):
    return professor_responsavel_pela_disciplina(
        atendimento.horario.monitoria.disciplina
    )


def usuario_pode_acessar_atendimento(atendimento):
    if current_user.perfil == "admin":
        return True

    if current_user.perfil == "aluno":
        return atendimento.aluno_id == current_user.id

    if current_user.perfil == "monitor":
        return monitor_responsavel_pelo_atendimento(atendimento)

    if current_user.perfil == "professor":
        return professor_responsavel_pelo_atendimento(atendimento)

    return False


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
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
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.ativo and usuario.check_senha(senha):
            login_user(usuario)
            return redirect(url_for("main.dashboard"))

        flash("E-mail ou senha inválidos.")

    return render_template("login.html")


@main.route("/login/google")
def login_google():
    if not current_app.config.get("GOOGLE_CLIENT_ID") or not current_app.config.get("GOOGLE_CLIENT_SECRET"):
        flash("Login com Google ainda não está configurado.")
        return redirect(url_for("main.login"))

    redirect_uri = url_for("main.login_google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@main.route("/login/google/callback")
def login_google_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo") or oauth.google.userinfo()
    except Exception:
        flash("Não foi possível concluir o login com Google.")
        return redirect(url_for("main.login"))

    google_id = user_info.get("sub")
    email = user_info.get("email", "").strip().lower()
    nome = user_info.get("name") or email.split("@")[0]
    foto_url = user_info.get("picture")

    if not email:
        flash("Não foi possível obter o e-mail da conta Google.")
        return redirect(url_for("main.login"))

    usuario = Usuario.query.filter_by(email=email).first()

    if usuario:
        if not usuario.ativo:
            flash("Usuário inativo. Entre em contato com a administração.")
            return redirect(url_for("main.login"))

        usuario.google_id = usuario.google_id or google_id
        usuario.foto_url = foto_url or usuario.foto_url
        usuario.auth_provider = usuario.auth_provider or "google"
    else:
        usuario = Usuario(
            nome=nome,
            email=email,
            perfil="aluno",
            ativo=True,
            google_id=google_id,
            foto_url=foto_url,
            auth_provider="google"
        )
        db.session.add(usuario)

    db.session.commit()
    login_user(usuario)

    flash("Login com Google realizado com sucesso.")
    return redirect(url_for("main.dashboard"))


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@main.route("/dashboard")
@login_required
def dashboard():
    total_usuarios = 0
    total_disciplinas = 0
    total_monitorias = 0
    total_horarios = 0
    total_atendimentos = 0

    if current_user.perfil == "aluno":
        meus_atendimentos = Atendimento.query.filter_by(aluno_id=current_user.id).count()
    else:
        meus_atendimentos = 0

    if current_user.perfil == "monitor":
        atendimentos_monitor = Atendimento.query.join(HorarioMonitoria).join(Monitoria).filter(
            Monitoria.monitor_id == current_user.id
        ).count()
    else:
        atendimentos_monitor = 0

    if current_user.perfil == "admin":
        total_usuarios = Usuario.query.count()
        total_disciplinas = Disciplina.query.count()
        total_monitorias = Monitoria.query.count()
        total_horarios = HorarioMonitoria.query.count()
        total_atendimentos = Atendimento.query.count()

    elif current_user.perfil == "professor":
        total_disciplinas = Disciplina.query.filter_by(
            professor_id=current_user.id
        ).count()
        total_monitorias = Monitoria.query.join(Disciplina).filter(
            Disciplina.professor_id == current_user.id
        ).count()
        total_horarios = HorarioMonitoria.query.join(Monitoria).join(Disciplina).filter(
            Disciplina.professor_id == current_user.id
        ).count()
        total_atendimentos = Atendimento.query.join(HorarioMonitoria).join(Monitoria).join(Disciplina).filter(
            Disciplina.professor_id == current_user.id
        ).count()

    return render_template(
        "dashboard.html",
        usuario=current_user,
        total_usuarios=total_usuarios,
        total_disciplinas=total_disciplinas,
        total_monitorias=total_monitorias,
        total_horarios=total_horarios,
        total_atendimentos=total_atendimentos,
        meus_atendimentos=meus_atendimentos,
        atendimentos_monitor=atendimentos_monitor
    )


@main.route("/admin/usuarios", methods=["GET", "POST"])
@login_required
@perfil_requerido("admin")
def gerenciar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nome).all()

    if request.method == "POST":
        user_id = request.form["user_id"]
        novo_perfil = request.form["perfil"]

        if novo_perfil not in PERFIS_GERENCIAVEIS:
            flash("Perfil inválido.")
            return redirect(url_for("main.gerenciar_usuarios"))

        usuario = Usuario.query.get(user_id)

        if usuario:
            if usuario.perfil == "admin" and novo_perfil != "admin":
                total_admins = Usuario.query.filter_by(
                    perfil="admin",
                    ativo=True
                ).count()

                if total_admins <= 1:
                    flash("Não é possível remover o último administrador ativo.")
                    return redirect(url_for("main.gerenciar_usuarios"))

            usuario.perfil = novo_perfil
            db.session.commit()
            flash("Perfil atualizado com sucesso!")
        else:
            flash("Usuário não encontrado.")

        return redirect(url_for("main.gerenciar_usuarios"))

    return render_template("admin_usuarios.html", usuarios=usuarios)


@main.route("/disciplinas")
@login_required
@perfil_requerido("professor", "admin")
def listar_disciplinas():
    if current_user.perfil == "admin":
        disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    else:
        disciplinas = Disciplina.query.filter_by(
            professor_id=current_user.id
        ).order_by(Disciplina.nome).all()

    return render_template("disciplinas.html", disciplinas=disciplinas)


@main.route("/disciplinas/nova", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor", "admin")
def nova_disciplina():
    if current_user.perfil == "admin":
        professores = Usuario.query.filter(
            Usuario.perfil.in_(["professor", "admin"]),
            Usuario.ativo == True
        ).order_by(Usuario.nome).all()
    else:
        professores = [current_user]

    if request.method == "POST":
        nome = request.form["nome"].strip()
        codigo = request.form["codigo"].strip().upper()
        professor_id = (
            request.form["professor_id"]
            if current_user.perfil == "admin"
            else current_user.id
        )

        disciplina_existente = Disciplina.query.filter_by(codigo=codigo).first()
        if disciplina_existente:
            flash("Já existe uma disciplina com esse código.")
            return redirect(url_for("main.nova_disciplina"))

        professor = Usuario.query.get(professor_id)
        if not professor or not professor.ativo or professor.perfil not in ["professor", "admin"]:
            flash("Professor responsável inválido.")
            return redirect(url_for("main.nova_disciplina"))

        disciplina = Disciplina(
            nome=nome,
            codigo=codigo,
            professor_id=int(professor_id)
        )

        db.session.add(disciplina)
        db.session.commit()

        flash("Disciplina cadastrada com sucesso!")
        return redirect(url_for("main.listar_disciplinas"))

    return render_template("nova_disciplina.html", professores=professores)


@main.route("/monitorias")
@login_required
@perfil_requerido("professor", "admin", "monitor")
def listar_monitorias():
    if current_user.perfil == "admin":
        monitorias = Monitoria.query.all()
    elif current_user.perfil == "professor":
        monitorias = Monitoria.query.join(Disciplina).filter(
            Disciplina.professor_id == current_user.id
        ).all()
    else:
        monitorias = Monitoria.query.filter_by(
            monitor_id=current_user.id
        ).all()

    return render_template("monitorias.html", monitorias=monitorias)


@main.route("/monitorias/nova", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor", "admin")
def nova_monitoria():
    if current_user.perfil == "admin":
        disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    else:
        disciplinas = Disciplina.query.filter_by(
            professor_id=current_user.id
        ).order_by(Disciplina.nome).all()

    usuarios = Usuario.query.filter(
        Usuario.perfil == "monitor",
        Usuario.ativo == True
    ).order_by(Usuario.nome).all()

    if request.method == "POST":
        descricao = request.form["descricao"].strip()
        disciplina_id = request.form["disciplina"]
        monitor_id = request.form["monitor"]

        disciplina = Disciplina.query.get(disciplina_id)
        if not disciplina:
            flash("Disciplina inválida.")
            return redirect(url_for("main.nova_monitoria"))

        if current_user.perfil != "admin" and disciplina.professor_id != current_user.id:
            flash("Você não pode criar monitoria para uma disciplina que não é sua.")
            return redirect(url_for("main.nova_monitoria"))

        monitor = Usuario.query.get(monitor_id)
        if not monitor or not monitor.ativo or monitor.perfil != "monitor":
            flash("Monitor inválido.")
            return redirect(url_for("main.nova_monitoria"))

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
@perfil_requerido("professor", "admin", "monitor")
def listar_horarios():
    filtro_validos = filtro_horarios_nao_encerrados()

    if current_user.perfil == "admin":
        horarios = HorarioMonitoria.query.filter(
            filtro_validos
        ).order_by(
            HorarioMonitoria.data,
            HorarioMonitoria.hora_inicio
        ).all()

    elif current_user.perfil == "professor":
        horarios = HorarioMonitoria.query.join(Monitoria).join(Disciplina).filter(
            Disciplina.professor_id == current_user.id,
            filtro_validos
        ).order_by(
            HorarioMonitoria.data,
            HorarioMonitoria.hora_inicio
        ).all()

    else:
        horarios = HorarioMonitoria.query.join(Monitoria).filter(
            Monitoria.monitor_id == current_user.id,
            filtro_validos
        ).order_by(
            HorarioMonitoria.data,
            HorarioMonitoria.hora_inicio
        ).all()

    return render_template("horarios.html", horarios=horarios)


@main.route("/horarios/novo", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor", "admin")
def novo_horario():
    if current_user.perfil == "admin":
        monitorias = Monitoria.query.all()
    else:
        monitorias = Monitoria.query.join(Disciplina).filter(
            Disciplina.professor_id == current_user.id
        ).all()

    if request.method == "POST":
        monitoria_id = request.form["monitoria"]
        data = datetime.strptime(request.form["data"], "%Y-%m-%d").date()

        hora_inicio = datetime.strptime(
            request.form["hora_inicio"], "%H:%M"
        ).time()

        hora_fim = datetime.strptime(
            request.form["hora_fim"], "%H:%M"
        ).time()

        monitoria = Monitoria.query.get(monitoria_id)
        if not monitoria:
            flash("Monitoria inválida.")
            return redirect(url_for("main.novo_horario"))

        if current_user.perfil != "admin" and monitoria.disciplina.professor_id != current_user.id:
            flash("Você não pode criar horário para uma monitoria que não pertence às suas disciplinas.")
            return redirect(url_for("main.novo_horario"))

        if data < date.today():
            flash("Não é possível cadastrar horário em uma data passada.")
            return redirect(url_for("main.novo_horario"))

        if hora_inicio >= hora_fim:
            flash("Horário de início deve ser menor que o horário de fim.")
            return redirect(url_for("main.novo_horario"))

        if data == date.today() and hora_fim <= datetime.now().time():
            flash("Não é possível cadastrar um horário que já terminou.")
            return redirect(url_for("main.novo_horario"))

        existe = HorarioMonitoria.query.filter_by(
            monitoria_id=monitoria_id,
            data=data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim
        ).first()

        if existe:
            flash("Já existe um horário igual para essa monitoria nesta data.")
            return redirect(url_for("main.novo_horario"))

        horario = HorarioMonitoria(
            data=data,
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
    horarios = HorarioMonitoria.query.filter(
        filtro_horarios_agendaveis()
    ).order_by(
        HorarioMonitoria.data,
        HorarioMonitoria.hora_inicio
    ).all()

    vagas_por_horario = {
        horario.id: calcular_vagas_horario(horario)
        for horario in horarios
    }

    horarios = [
        horario for horario in horarios
        if horario_ainda_pode_ser_agendado(horario)
        and vagas_por_horario[horario.id] > 0
    ]

    return render_template(
        "aluno_horarios.html",
        horarios=horarios,
        vagas_por_horario=vagas_por_horario
    )


@main.route("/aluno/agendar/<int:horario_id>", methods=["GET", "POST"])
@login_required
@perfil_requerido("aluno")
def agendar_atendimento(horario_id):
    horario = HorarioMonitoria.query.get_or_404(horario_id)

    if not horario_ainda_pode_ser_agendado(horario):
        flash("Não é possível agendar um atendimento que já começou ou já passou.")
        return redirect(url_for("main.aluno_horarios"))

    if aluno_ja_tem_agendamento_ativo(current_user.id, horario.id):
        flash("Você já possui um atendimento ativo para este horário.")
        return redirect(url_for("main.aluno_horarios"))

    if calcular_vagas_horario(horario) <= 0:
        flash("Este horário já está lotado.")
        return redirect(url_for("main.aluno_horarios"))

    if request.method == "POST":
        descricao_duvida = request.form["descricao_duvida"].strip()

        horario = HorarioMonitoria.query.filter_by(
            id=horario_id
        ).with_for_update().first_or_404()

        if not horario_ainda_pode_ser_agendado(horario):
            flash("Não é possível agendar um atendimento que já começou ou já passou.")
            return redirect(url_for("main.aluno_horarios"))

        existe_ativo = aluno_ja_tem_agendamento_ativo(
            current_user.id,
            horario.id
        )

        if existe_ativo:
            flash("Você já está inscrito neste horário.")
            return redirect(url_for("main.aluno_horarios"))

        atendimento_cancelado = Atendimento.query.filter(
            Atendimento.aluno_id == current_user.id,
            Atendimento.horario_id == horario.id,
            Atendimento.status == "Cancelado"
        ).first()

        conflito_horario = Atendimento.query.join(HorarioMonitoria).filter(
            Atendimento.aluno_id == current_user.id,
            Atendimento.status != "Cancelado",
            HorarioMonitoria.data == horario.data,
            HorarioMonitoria.hora_inicio < horario.hora_fim,
            HorarioMonitoria.hora_fim > horario.hora_inicio
        ).first()

        if conflito_horario:
            flash("Você já possui um atendimento agendado nesse mesmo dia e horário.")
            return redirect(url_for("main.aluno_horarios"))

        if calcular_vagas_horario(horario) <= 0:
            flash("Este horário já está lotado.")
            return redirect(url_for("main.aluno_horarios"))

        if atendimento_cancelado:
            atendimento_cancelado.status = "Agendado"
            atendimento_cancelado.descricao_duvida = descricao_duvida
            atendimento_cancelado.atualizado_em = datetime.utcnow()
            db.session.commit()

            flash("Atendimento reagendado com sucesso!")
            return redirect(url_for("main.meus_agendamentos"))

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
    atendimentos = Atendimento.query.filter_by(
        aluno_id=current_user.id
    ).order_by(Atendimento.criado_em.desc()).all()

    return render_template("meus_agendamentos.html", atendimentos=atendimentos)


@main.route("/aluno/agendamentos/<int:atendimento_id>/cancelar")
@login_required
@perfil_requerido("aluno")
def cancelar_agendamento(atendimento_id):
    atendimento = Atendimento.query.get_or_404(atendimento_id)

    if not usuario_pode_acessar_atendimento(atendimento):
        flash("Você não tem permissão para cancelar este agendamento.")
        return redirect(url_for("main.meus_agendamentos"))

    if atendimento.status == "Realizado":
        flash("Não é possível cancelar um atendimento já realizado.")
        return redirect(url_for("main.meus_agendamentos"))

    if atendimento.status == "Cancelado":
        flash("Este agendamento já está cancelado.")
        return redirect(url_for("main.meus_agendamentos"))

    atendimento.status = "Cancelado"
    db.session.commit()

    flash("Agendamento cancelado com sucesso.")
    return redirect(url_for("main.meus_agendamentos"))


@main.route("/monitor/atendimentos")
@login_required
@perfil_requerido("monitor", "admin")
def monitor_atendimentos():
    if current_user.perfil == "admin":
        atendimentos = Atendimento.query.all()
    else:
        atendimentos = Atendimento.query.join(HorarioMonitoria).join(Monitoria).filter(
            Monitoria.monitor_id == current_user.id
        ).all()

    return render_template("monitor_atendimentos.html", atendimentos=atendimentos)


@main.route("/monitor/atendimentos/<int:atendimento_id>/concluir")
@login_required
@perfil_requerido("monitor", "admin")
def concluir_atendimento(atendimento_id):
    atendimento = Atendimento.query.get_or_404(atendimento_id)

    if not usuario_pode_acessar_atendimento(atendimento):
        flash("Você não tem permissão para concluir este atendimento.")
        return redirect(url_for("main.dashboard"))

    if atendimento.status == "Cancelado":
        flash("Não é possível concluir um atendimento cancelado.")
        return redirect(url_for("main.monitor_atendimentos"))

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
