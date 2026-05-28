import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(database_url):
    if database_url and database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL"))
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    if not SECRET_KEY:
        raise RuntimeError("A variável de ambiente SECRET_KEY é obrigatória.")

    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("A variável de ambiente DATABASE_URL é obrigatória.")
