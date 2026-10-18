"""Casos novos de conversa progressiva no Apoio, fora do gabarito de busca."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import apoio_busca as ab


def main():
    inicial = ab.responder_pergunta("onde consulto quando a carreta da mamografia vai passar")
    assert inicial.tipo == "itens" and inicial.candidatos == ["carretas_estado"]

    # Só o identificador do catálogo segue para a próxima mensagem; o texto íntimo
    # anterior não é repassado ao classificador externo.
    recebidas = []

    def gemini(pergunta, opcoes, **kwargs):
        recebidas.append(pergunta)
        return {"intencao": "carretas"}

    seguimento = ab.responder_pergunta(
        "e agora?", classificar=gemini, contexto="item:carretas_estado"
    )
    assert seguimento.tipo == "esclarecimento"
    assert seguimento.candidatos == ["item:carretas_estado"]
    assert "continua falando" in seguimento.fala.lower()
    assert recebidas == []  # pergunta vaga pede detalhe, não uma classificação externa

    # Mudança explícita de assunto substitui o contexto anterior.
    novo = ab.responder_pergunta(
        "telefone da regulação de oncologia", contexto="item:carretas_estado"
    )
    assert novo.tipo == "itens" and novo.candidatos == ["lista_regulacao"]

    # As regras determinísticas de risco sempre vencem a memória conversacional.
    risco = ab.responder_pergunta("meu marido me bate", contexto="item:carretas_estado")
    assert risco.tipo == "risco" and "180" in risco.fala

    # Chaves inválidas/ausentes nunca criam resposta contextual inventada.
    sem_memoria = ab.responder_pergunta("e agora?", contexto="relato:texto pessoal não deve ser salvo")
    assert sem_memoria.tipo in {"nada", "palpites"}

    diagnostico = ab.responder_pergunta("e agora?", contexto="etapa:diagnostico_cancer")
    assert diagnostico.tipo == "esclarecimento"
    assert "diagnóstico" in diagnostico.fala.lower()

    print("Todos os casos novos de conversa do Apoio passaram.")


if __name__ == "__main__":
    main()
