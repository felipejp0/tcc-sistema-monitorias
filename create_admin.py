from app import create_app, db
from app.models import Usuario
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    email = "felipejpo2019@gmail.com"
    senha = "1"

    usuario = Usuario.query.filter_by(email=email).first()

    if usuario:
        usuario.perfil = "admin"
        usuario.senha = generate_password_hash(senha)
        print("Usuário admin atualizado com sucesso.")
    else:
        admin = Usuario(
            nome="Administrador",
            email=email,
            senha=generate_password_hash(senha),
            perfil="admin"
        )

        db.session.add(admin)
        print("Usuário admin criado com sucesso.")

    db.session.commit()