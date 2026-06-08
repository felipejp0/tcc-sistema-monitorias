import os
import sys
from datetime import date, time, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Usuario, Disciplina, Monitoria, HorarioMonitoria, Atendimento


def proxima_data(dias_a_frente):
    return date.today() + timedelta(days=dias_a_frente)


def main():
    app = create_app()

    with app.app_context():
        print("Iniciando limpeza de atendimentos, horários e monitorias...")

        atendimentos_removidos = Atendimento.query.delete()
        horarios_removidos = HorarioMonitoria.query.delete()
        monitorias_removidas = Monitoria.query.delete()

        db.session.commit()

        print(f"Atendimentos removidos: {atendimentos_removidos}")
        print(f"Horários removidos: {horarios_removidos}")
        print(f"Monitorias removidas: {monitorias_removidas}")

        monitores = Usuario.query.filter_by(
            perfil="monitor",
            ativo=True
        ).order_by(Usuario.nome).all()

        if not monitores:
            print("Nenhum usuário com perfil monitor encontrado.")
            print("Crie ou promova pelo menos um usuário para monitor antes de rodar este script.")
            return

        disciplinas = Disciplina.query.order_by(Disciplina.nome).limit(8).all()

        if not disciplinas:
            print("Nenhuma disciplina cadastrada.")
            return

        print("Criando monitorias...")

        monitorias_criadas = []

        descricoes = [
            "Atendimento para dúvidas e resolução de exercícios.",
            "Apoio aos conteúdos trabalhados em sala de aula.",
            "Revisão de conceitos e acompanhamento dos estudantes.",
            "Suporte para atividades práticas e estudos dirigidos.",
        ]

        for i, disciplina in enumerate(disciplinas):
            monitor = monitores[i % len(monitores)]

            monitoria = Monitoria(
                descricao=descricoes[i % len(descricoes)],
                disciplina_id=disciplina.id,
                monitor_id=monitor.id
            )

            db.session.add(monitoria)
            monitorias_criadas.append(monitoria)

        db.session.commit()

        print(f"Monitorias criadas: {len(monitorias_criadas)}")

        print("Criando horários...")

        horarios_base = [
            (1, time(9, 0), time(10, 0), 15),
            (2, time(14, 0), time(15, 0), 15),
            (3, time(19, 0), time(20, 0), 15),
        ]

        total_horarios = 0

        for i, monitoria in enumerate(monitorias_criadas):
            for deslocamento, hora_inicio, hora_fim, capacidade in horarios_base:
                horario = HorarioMonitoria(
                    data=proxima_data(i + deslocamento + 1),
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    capacidade=capacidade,
                    monitoria_id=monitoria.id
                )

                db.session.add(horario)
                total_horarios += 1

        db.session.commit()

        print(f"Horários criados: {total_horarios}")
        print("Seed concluído com sucesso.")


if __name__ == "__main__":
    main()