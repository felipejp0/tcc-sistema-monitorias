from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user

from app.models import Usuario, Disciplina
from app.extensions import db

main = Blueprint("main", __name__)


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

        usuario = Usuario(nome=nome, email=email, perfil="professor")
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


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", usuario=current_user)


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@main.route("/disciplinas")
@login_required
def listar_disciplinas():
    disciplinas = Disciplina.query.all()
    return render_template("disciplinas.html", disciplinas=disciplinas)


@main.route("/disciplinas/nova", methods=["GET", "POST"])
@login_required
def nova_disciplina():
    if request.method == "POST":
        nome = request.form["nome"]
        codigo = request.form["codigo"]
        descricao = request.form["descricao"]

        disciplina_existente = Disciplina.query.filter_by(codigo=codigo).first()
        if disciplina_existente:
            flash("Já existe uma disciplina com esse código.")
            return redirect(url_for("main.nova_disciplina"))

        disciplina = Disciplina(
            nome=nome,
            codigo=codigo,
            descricao=descricao,
            professor_id=current_user.id
        )

        db.session.add(disciplina)
        db.session.commit()

        flash("Disciplina cadastrada com sucesso!")
        return redirect(url_for("main.listar_disciplinas"))

    return render_template("nova_disciplina.html")