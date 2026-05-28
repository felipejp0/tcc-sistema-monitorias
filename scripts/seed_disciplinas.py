import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.extensions import db
from app.models import Disciplina, Usuario


PROFESSOR_EMAIL = "felipejpo2019@gmail.com"

DISCIPLINAS = [
    ("OBBGSIN.044", "Ética e Legislação"),
    ("OBBGSIN.085", "Introdução à Programação"),
    ("OBBGSIN.001", "Introdução à Sistemas de Informação"),
    ("OBBGSIN.007", "Português Instrumental I"),
    ("OBBGSIN.101", "Pré-Cálculo"),
    ("OBBGSIN.011", "Princípios da Administração I"),
    ("OBBGSIN.009", "Algoritmos e Estrutura de Dados I"),
    ("OBBGSIN.012", "Cálculo Diferencial e Integral I"),
    ("OBBGSIN.003", "Inglês Instrumental I"),
    ("OBBGSIN.002", "Métodos e Técnicas de Pesquisa"),
    ("OBBGSIN.010", "Programação Orientada a Objetos I"),
    ("OBBGSIN.013", "Sistemas Digitais e Circuitos Combinacionais"),
    ("OBBGSIN.015", "Algoritmos e Estrutura de Dados II"),
    ("OBBGSIN.024", "Arquitetura e Organização de Computadores"),
    ("OBBGSIN.016", "Banco de Dados I"),
    ("OBBGSIN.018", "Contabilidade"),
    ("OBBGSIN.017", "Engenharia de Software I"),
    ("OBBGSIN.021", "Álgebra Linear e Geometria Analítica"),
    ("OBBGSIN.020", "Matemática Discreta"),
    ("OBBGSIN.022", "Programação Orientada a Objetos II"),
    ("OBBGSIN.023", "Programação Web"),
    ("OBBGSIN.030", "Sistemas Operacionais"),
    ("OBBGSIN.041", "Engenharia de Software II"),
    ("OBBGSIN.019", "Governança e Gestão da Informação"),
    ("OBBGSIN.031", "Probabilidade e Estatística"),
    ("OBBGSIN.029", "Redes de Computadores I"),
    ("OBBGSIN.039", "Programação para Dispositivos Móveis"),
    ("OBBGSIN.038", "Projeto e Análise de Algoritmos"),
    ("OBBGSIN.036", "Sistemas de Apoio à Decisão"),
    ("OBBGSIN.037", "Sistemas Distribuídos"),
    ("OBBGSIN.040", "Gestão de Projetos"),
    ("OBBGSIN.034", "Inteligência Artificial"),
    ("OBBGSIN.026", "Interface Humano Computador"),
    ("OBBGSIN.091", "Trabalho de Conclusão de Curso I"),
    ("OBBGSIN.102", "Empreendedorismo"),
    ("OBBGSIN.103", "Qualidade de Software"),
    ("OBBGSIN.092", "Trabalho de Conclusão de Curso II"),
]


def validar_configuracao():
    erros = []

    if PROFESSOR_EMAIL == "ederson.junior@aluno.ufop.edu.br":
        erros.append("Defina PROFESSOR_EMAIL com o email de um professor existente.")

    if not DISCIPLINAS:
        erros.append("Preencha DISCIPLINAS com codigo e nome das disciplinas da matriz.")

    codigos_vistos = set()
    for indice, item in enumerate(DISCIPLINAS, start=1):
        if not isinstance(item, tuple) or len(item) != 2:
            erros.append(f"Item {indice} invalido: use o formato ('CODIGO', 'Nome').")
            continue

        codigo, nome = item
        codigo = str(codigo).strip()
        nome = str(nome).strip()

        if not codigo or not nome:
            erros.append(f"Item {indice} invalido: codigo e nome sao obrigatorios.")
            continue

        if codigo in codigos_vistos:
            erros.append(f"Codigo duplicado na lista de seed: {codigo}.")

        codigos_vistos.add(codigo)

    return erros


def seed_disciplinas():
    erros = validar_configuracao()
    if erros:
        return {
            "criadas": 0,
            "ignoradas": 0,
            "erros": erros,
        }

    professor = Usuario.query.filter_by(email=PROFESSOR_EMAIL).first()
    if not professor:
        return {
            "criadas": 0,
            "ignoradas": 0,
            "erros": [
                f"Professor com email '{PROFESSOR_EMAIL}' nao encontrado.",
                "Crie o usuario professor antes de executar este seed.",
            ],
        }

    criadas = 0
    ignoradas = 0

    for codigo, nome in DISCIPLINAS:
        codigo = str(codigo).strip()
        nome = str(nome).strip()

        disciplina_existente = Disciplina.query.filter_by(codigo=codigo).first()
        if disciplina_existente:
            ignoradas += 1
            continue

        disciplina = Disciplina(
            codigo=codigo,
            nome=nome,
            professor_id=professor.id,
        )
        db.session.add(disciplina)
        criadas += 1

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {
            "criadas": 0,
            "ignoradas": ignoradas,
            "erros": [f"Erro ao salvar disciplinas: {exc}"],
        }

    return {
        "criadas": criadas,
        "ignoradas": ignoradas,
        "erros": [],
    }


def imprimir_resumo(resultado):
    print("Seed de disciplinas concluido.")
    print(f"Criadas: {resultado['criadas']}")
    print(f"Ignoradas: {resultado['ignoradas']}")
    print(f"Erros: {len(resultado['erros'])}")

    for erro in resultado["erros"]:
        print(f"- {erro}")


def main():
    app = create_app()
    with app.app_context():
        resultado = seed_disciplinas()
        imprimir_resumo(resultado)
        return 1 if resultado["erros"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
