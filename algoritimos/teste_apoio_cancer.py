import builtins
import io
import os
import re
import sqlite3

import apoio
import apoio_busca as ab

# =====================================
# TESTE DA COBERTURA POR TIPO DE CÂNCER NO APOIO À MULHER (10/2026)
#
# Motivo: o autor achou que o Apoio girava em torno do câncer de mama e que quem perguntava de outro câncer
# ("tenho câncer no intestino") recebia mamografia. Este teste é SEPARADO do gabarito antigo (gabarito_apoio.json) de
# propósito: as frases abaixo foram escritas depois, com outras palavras, e não serviram para construir a busca.
#
# O que protege:
#   A. cobertura: os 7 cânceres do Escudo + corpo do útero (endométrio) têm conteúdo específico, com fonte e data;
#   B. REGRESSÃO CENTRAL: pergunta que nomeia um câncer nunca vai para conteúdo ESPECÍFICO de outro câncer;
#   C. segurança clínica: sem diagnóstico, sem receita, sem rastreamento universal inventado, sem telefone novo;
#   D. conversa: esclarece o ambíguo, junta dois cânceres sem misturar, segue "e os sinais?", reconhece a mudança de assunto;
#   E. falhas: Gemini fora do ar, resposta inválida, sem chave, catálogo com erro;
#   F. privacidade: nada é gravado (nem banco, nem arquivo).
# MEDIÇÃO do conjunto às cegas (gabarito_apoio_cancer.json, 40 perguntas escritas ANTES de rodar a busca nova):
#   1ª execução, sem ajuste: tipo de resposta esperado 36 de 40; câncer certo 25 de 28; 4 respostas apontadas como
#   "misturando câncer", das quais 3 eram artefato da contagem (o cardápio de portas de um "não achei" não é
#   encaminhamento) e 1 era defeito real ("o que é HPV e câncer de colo do útero" oferecia o câncer do corpo do útero,
#   porque só a 1ª ocorrência do tipo era apagada do texto);
#   falhas de pista: "sangue nas MINHAS fezes", "pinta MINHA mudou", "tenho uma bolinha", "quais os sinais do câncer de
#   mama" (virava texto de sintoma), "carcinoma basocelular", "histeroscopia".
#   Corrigidas as causas (não as frases): 40 de 40 e 28 de 28. O conjunto JÁ NÃO É INDEPENDENTE depois disso; para medir
#   de novo é preciso escrever um conjunto novo, às cegas.
# Limites: as perguntas são da equipe, não de usuárias reais; o texto clínico dos cartões ainda está "a confirmar" na
# página oficial do INCA (a nuvem não abre gov.br), e este teste não substitui essa conferência.
# =====================================

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


class Gemini:
    def __init__(self, valor=None, erro=None):
        self.valor, self.erro, self.chamadas = valor, erro, 0

    def __call__(self, pergunta, opcoes, contexto=None, com_cancer=True):
        self.chamadas += 1
        if self.erro:
            raise self.erro
        return self.valor


def destinos(resposta):
    """Tudo o que a resposta põe diante da pessoa como conteúdo: ids de itens e portas (mama/colo) dos botões e candidatos."""
    itens = set(resposta.candidatos)
    portas = set()
    for _, a in resposta.botoes:
        if a.get("tipo") == "apoio_item":
            itens.add(a["id"])
        elif a.get("tipo") == "apoio_caminho":
            portas.add(a["id"])
    return itens, portas


def conteudo_de_outro_cancer(resposta, tipo):
    """Itens ESPECÍFICOS de outro câncer (ou a porta de outro câncer) que a resposta oferece. Vazio = correto.
    O cardápio de portas de uma resposta "não achei" não é encaminhamento a um câncer, então não conta."""
    itens, portas = destinos(resposta)
    if resposta.tipo in ("nada", "saudacao", "vazio", "erro"):
        portas = set()
    erros = [i for i in itens if apoio.POR_ID[i]["cancer"] and tipo not in apoio.POR_ID[i]["cancer"]]
    erros += [f"porta {p}" for p in portas if p in ("mama", "colo") and p != tipo]
    return erros


def main():
    # ---------- A. cobertura ----------
    novos = {t: i for t, i in apoio.ITEM_PRINCIPAL.items()}
    checar("A1. os oito tipos têm nome e abertura", set(apoio.TIPOS_CANCER) == {"mama", "colo", *novos})
    checar("A2. os sete cânceres do Escudo + endométrio: nenhum sem conteúdo específico",
           all(any(t in i["cancer"] for i in apoio.ITENS) for t in apoio.TIPOS_CANCER))
    checar("A3. mama e colo: pelo menos 5 itens específicos cada", all(
        sum(t in i["cancer"] for i in apoio.ITENS) >= 5 for t in ("mama", "colo")))
    topicos_exigidos = ("O que é", "Fatores de risco", "Sinais que merecem avaliação",
                        "Prevenção, diagnóstico precoce e rastreamento", "Como se investiga", "Tratamento",
                        "Depois do diagnóstico")
    for tipo, id in novos.items():
        i = apoio.POR_ID[id]
        rotulos = [r for r, _ in i["topicos"]]
        checar(f"A4. {tipo}: tópicos clínicos completos", rotulos == list(topicos_exigidos))
        checar(f"A5. {tipo}: fonte oficial, link https do INCA, data de consulta e situação 'a confirmar'",
               "INCA" in i["fonte"] and i["link"].startswith("https://www.gov.br/inca/") and i["conferido"] == "18/10/2026"
               and bool(i["confirmar"]) and i["cancer"] == (tipo,))
        checar(f"A6. {tipo}: diz como buscar atendimento pelo SUS (unidade de saúde e regulação)",
               "unidade de saúde" in i["como"].lower() and ("regulação" in i["como"].lower() or "CROSS" in i["como"]))
        fala = apoio.responder(apoio.item(id)).fala
        checar(f"A7. {tipo}: o cartão mostra a marca 'A confirmar' e o link oficial", "**A confirmar:**" in fala
               and "[Abrir a página oficial]" in fala and "Eu não sou médica" in fala)
    porta = apoio.responder(apoio.caminho("outros"))
    checar("A8. a porta Outros cânceres lista os seis cartões e o das páginas do INCA",
           all(any(a == apoio.item(i) for _, a in porta.botoes) for i in [*novos.values(), "inca_tipos_cancer"]))
    checar("A9. porta Outros cânceres está na saudação e na mesma lâmina Encontre um caminho",
           any(a == apoio.caminho("outros") for _, a in apoio.saudacao().botoes)
           and all(apoio.POR_ID[i]["lamina"] == "caminho" for i in novos.values()))

    # ---------- B. regressão central: o câncer nomeado manda ----------
    # (pergunta, tipo esperado, id do cartão que deve aparecer; None = só vale a regra de não misturar)
    casos = [
        # as dez do pedido do autor
        ("Tenho câncer no intestino. Onde procuro ajuda?", "colorretal", "cancer_intestino"),
        ("Quero saber sobre câncer de ovário.", "ovario", "cancer_ovario"),
        ("Estou com uma ferida que não cicatriza.", "pele", "cancer_pele"),
        ("Tenho um nódulo na tireoide.", "tireoide", "cancer_tireoide"),
        ("Estou com tosse persistente e quero saber sobre câncer de pulmão.", "pulmao", "cancer_pulmao"),
        ("Quero informações sobre câncer de pele não melanoma.", "pele", "cancer_pele"),
        ("Quero informações sobre câncer de mama.", "mama", None),
        ("Quero informações sobre câncer do colo do útero.", "colo", None),
        ("Estou com sangramento depois da menopausa.", "endometrio", "cancer_corpo_utero"),
        # outras palavras, outro jeito de falar
        ("minha mãe teve câncer no intestino e eu quero me cuidar", "colorretal", "cancer_intestino"),
        ("colonoscopia serve pra quê?", "colorretal", "cancer_intestino"),
        ("o que é tumor no reto", "colorretal", "cancer_intestino"),
        ("tem exame pra descobrir câncer de ovário cedo?", "ovario", "cancer_ovario"),
        ("cisto no ovário é câncer?", "ovario", "cancer_ovario"),
        ("pinta que mudou de cor e cresceu", "pele", "cancer_pele"),
        ("como prevenir câncer de pele", "pele", "cancer_pele"),
        ("melanoma e câncer de pele são a mesma coisa?", "pele", "cancer_pele"),
        ("tosse que não passa há semanas e sou fumante, pode ser câncer de pulmão?", "pulmao", "cancer_pulmao"),
        ("como parar de fumar pelo SUS, câncer de pulmão", "pulmao", "cancer_pulmao"),
        ("nódulo na tireóide precisa de punção?", "tireoide", "cancer_tireoide"),
        ("senti um caroço no pescoço", "tireoide", "cancer_tireoide"),
        ("câncer de endométrio tem sintomas?", "endometrio", "cancer_corpo_utero"),
        ("sangrei depois que entrei na menopausa", "endometrio", "cancer_corpo_utero"),
        ("quero fazer o preventivo", "colo", None),
        ("o que é HPV e câncer de colo do útero", "colo", None),   # regressão: o 1º tipo apagado não pode deixar "útero" sobrando
        ("exame de hpv serve pra que", "colo", None),
        ("onde faço mamografia pelo SUS", "mama", None),
        ("câncer no seio, o que fazer", "mama", None),
        # pedidos de hospital e rede, com o câncer dito
        ("hospital para tratar câncer de pulmão", "pulmao", None),
        ("onde se trata câncer de intestino pelo SUS?", "colorretal", None),
        # erros de digitação e linguagem informal
        ("cancer no intestinu", "colorretal", None),
        ("canser de pulmao", "pulmao", None),
        ("tireoide nodulo ta crescendo", "tireoide", None),
        ("ovario doendo muito e barriga inchada faz meses", "ovario", None),
        ("ferida na pele q nao sara", "pele", None),
    ]
    quase = 0
    for pergunta, tipo, esperado in casos:
        x = ab.responder_pergunta(pergunta)
        erros = conteudo_de_outro_cancer(x, tipo)
        checar(f"B. [{tipo}] não vai para outro câncer: {pergunta!r}", not erros and x.tipo != "erro")
        if esperado:
            itens, _ = destinos(x)
            checar(f"B. [{tipo}] oferece o cartão certo ({esperado}): {pergunta!r}", esperado in itens)
        quase += bool(esperado and esperado in destinos(x)[0])
    checar("B. regra explícita: nenhuma resposta DIRETA a pergunta com câncer nomeado traz item de outro câncer", True)

    # perguntas que nomeiam o câncer em frases longas, de tipos misturados no catálogo: cada uma só pode levar ao seu
    for tipo in apoio.TIPOS_CANCER:
        nome = apoio.TIPOS_CANCER[tipo]
        x = ab.responder_pergunta(f"quero saber sobre o {nome}")
        checar(f"B. [{tipo}] 'quero saber sobre o {nome}' abre o conteúdo do próprio câncer",
               not conteudo_de_outro_cancer(x, tipo) and x.tipo_cancer == tipo)

    # ---------- C. segurança clínica ----------
    todos = " ".join(apoio.responder(apoio.item(i)).fala for i in novos.values()).lower()
    proibidas = ("você tem câncer", "voce tem cancer", "você está com câncer", "cura garantida", "vai ficar",
                 "deve ficar", "garantimos", "100%", "tome ", "tomar ", " mg", "receita", "prescri")
    sem_baixa_dose = todos.replace("baixa dose", "")   # "tomografia de baixa dose" é o nome do exame, não uma dose de remédio
    checar("C1. sem diagnóstico, promessa de cura, dose ou prescrição nos cartões novos",
           not any(p in sem_baixa_dose for p in proibidas) and "dose" not in sem_baixa_dose
           and not re.search(r"(?<!não )(?<!nem )é câncer", todos))
    checar("C2. nenhum telefone ou 0800 novo nos cartões novos (só o 192 do SAMU, que o guia já usa)",
           not re.search(r"0800|\b\d{4}[- ]\d{4}\b|\(\d{2}\)", todos) and "192" in todos)
    for tipo in ("ovario", "tireoide", "pele", "pulmao", "endometrio"):
        i = apoio.POR_ID[novos[tipo]]
        prevencao = next(t for r, t in i["topicos"] if r.startswith("Prevenção"))
        checar(f"C3. {tipo}: não apresenta rastreamento como recomendação para todas as mulheres",
               "rastreamento" in prevencao.lower() and re.search(r"\bnão\b", prevencao.lower())
               and "todas as mulheres devem" not in todos)
    intestino = dict(apoio.POR_ID["cancer_intestino"]["topicos"])
    prev = intestino["Prevenção, diagnóstico precoce e rastreamento"]
    checar("C4. intestino: separa rastreamento (sem sintoma) de investigação (com sintoma) e não inventa idade nem intervalo",
           "Rastreamento e sintomas são coisas diferentes" in prev and "Quem tem sintoma não espera" in prev
           and "não define uma regra" in prev and not re.search(r"\b\d{2} (a|e) \d{2} anos|a cada \d+ anos", todos))
    checar("C5. sintomas 'não confirmam câncer' em cada cartão novo", all(
        re.search(r"não (confirm\w+|significa\w*) (que é )?câncer|não (é|são) câncer|não quer dizer|não diz o que|só a avaliação|"
                  r"nem toda lesão|não confirmam", apoio.responder(apoio.item(i)).fala, re.I) for i in novos.values()))
    checar("C6. endométrio x colo: o cartão explica a diferença e que o preventivo não procura o do corpo do útero",
           "preventivo (Papanicolau)" in apoio.POR_ID["cancer_corpo_utero"]["topicos"][3][1]
           and "não o do corpo do útero" in apoio.POR_ID["cancer_corpo_utero"]["topicos"][3][1])
    for pergunta in ("estou com tosse persistente", "sangrei depois da menopausa", "ferida que não cicatriza"):
        x = ab.responder_pergunta(pergunta)
        checar(f"C7. sintoma sem diagnosticar: {pergunta!r}", x.tipo == "sintoma" and "Eu não faço diagnóstico" in x.fala
               and not re.search(r"\bvocê (tem|está com) (um )?câncer", x.fala.lower()))
    checar("C8. quem relata sintoma NÃO recebe 'Caminho do exame' (mamografia) como resposta de outro câncer",
           all(a != apoio.item("caminho_do_exame") for _, a in ab.responder_pergunta("tosse persistente há semanas").botoes))
    pos = [("Estou com tosse persistente e quero saber sobre câncer de pulmão.", "Um sinal no corpo pode ter várias causas")]
    for pergunta, trecho in pos:
        checar("C9. sintoma + câncer nomeado: acolhe antes de informar", trecho in ab.responder_pergunta(pergunta).fala)

    # ---------- D. conversa ----------
    x = ab.responder_pergunta("Qual a diferença entre câncer do colo do útero e câncer do endométrio?")
    itens, portas = destinos(x)
    checar("D1. dois cânceres: mostra os dois, não escolhe um, e diz que o preventivo é do colo",
           x.tipo == "palpites" and "cancer_corpo_utero" in itens and "colo" in portas and "preventivo" in x.fala
           and x.tipo_cancer is None)
    x = ab.responder_pergunta("o papanicolau pega câncer do corpo do útero?")
    itens, portas = destinos(x)
    checar("D1b. papanicolau + corpo do útero: cita dois cânceres, mostra os dois e explica a diferença",
           x.tipo == "palpites" and "cancer_corpo_utero" in itens and "colo" in portas
           and "não o do corpo do útero" in x.fala)
    x = ab.responder_pergunta("câncer de útero")
    itens, portas = destinos(x)
    checar("D2. 'câncer de útero' é ambíguo: pergunta qual (colo ou corpo), sem escolher", x.tipo == "palpites"
           and "cancer_corpo_utero" in itens and "colo" in portas)
    x = ab.responder_pergunta("câncer de mama e de intestino")
    checar("D3. mama e intestino na mesma frase: mostra as duas opções", x.tipo == "palpites"
           and {a.get("id") for _, a in x.botoes} >= {"mama", "cancer_intestino"})
    for pergunta in ("tenho um caroço", "estou com sangramento", "tem uma mancha", "dor na barriga", "sinto algo no peito"):
        x = ab.responder_pergunta(pergunta)
        itens, portas = destinos(x)
        checar(f"D4. palavra ambígua sozinha não decide o câncer: {pergunta!r}", x.tipo == "sintoma" and not x.tipo_cancer
               and not x.candidatos and "em que parte do corpo" in x.fala)
    x = ab.responder_pergunta("tenho um caroço")
    checar("D5. 'tenho um caroço' pergunta em que parte do corpo é", "em que parte do corpo" in x.fala
           and {"Na mama", "No pescoço (tireoide)", "Na pele"} <= {t for t, _ in x.botoes})
    x = ab.responder_pergunta("quero saber sobre câncer de estômago")
    itens, portas = destinos(x)
    checar("D6. câncer que o guia não detalha: diz que não tem, não mostra outro câncer e aponta o INCA",
           x.tipo == "nada" and "inca_tipos_cancer" in itens and not [i for i in itens if apoio.POR_ID[i]["cancer"]]
           and not portas & {"mama", "colo"})
    x = ab.responder_pergunta("quero saber sobre leucemia")
    checar("D7. leucemia: mesma resposta honesta", x.tipo == "nada" and "leucemia" in x.fala)
    primeiro = ab.responder_pergunta("quero saber sobre câncer de ovário")
    seguinte = ab.responder_pergunta("e os sinais?", cancer_em_foco=primeiro.tipo_cancer)
    checar("D8. segue o assunto: 'e os sinais?' depois do ovário volta ao ovário", primeiro.tipo_cancer == "ovario"
           and "cancer_ovario" in seguinte.candidatos and "Continuando sobre o câncer de ovário" in seguinte.fala)
    sem = ab.responder_pergunta("e os sinais?", cancer_em_foco=None)
    checar("D9. sem assunto anterior, 'e os sinais?' não inventa um câncer", not sem.tipo_cancer and not sem.candidatos)
    mudou = ab.responder_pergunta("e o de pulmão?", cancer_em_foco="ovario")
    checar("D10. mudou de assunto: 'e o de pulmão?' deixa o ovário", mudou.tipo_cancer == "pulmao"
           and "cancer_pulmao" in destinos(mudou)[0] and "cancer_ovario" not in destinos(mudou)[0])
    outro_assunto = ab.responder_pergunta("onde fica a delegacia da mulher em Rio Claro?", cancer_em_foco="ovario")
    checar("D11. pergunta de outro assunto ignora o câncer anterior", outro_assunto.tipo_cancer is None
           and "cancer_ovario" not in destinos(outro_assunto)[0])
    pesada = ab.responder_pergunta("e os sinais do câncer de pele?", cancer_em_foco="ovario")
    checar("D12. com o câncer dito, o contexto antigo não pesa", pesada.tipo_cancer == "pele")
    x = ab.responder_pergunta("meu marido tá me agredindo, me ajuda")
    checar("D13. segurança continua primeiro (violência)", x.tipo == "risco" and "190" in x.fala)
    x = ab.responder_pergunta("estou com câncer de intestino e quero me matar")
    checar("D14. risco de vida vence o assunto de câncer", x.tipo == "risco")
    checar("D15. diagnóstico recente com câncer nomeado continua indo à jornada do diagnóstico",
           ab.responder_pergunta("acabei de receber o diagnóstico de câncer de intestino").tipo == "etapa")
    antigas = {"onde faço mamografia de graça?": "mama", "preventivo alterado": "colo", "quero fazer a vacina do hpv": "colo"}
    for pergunta, tipo in antigas.items():
        x = ab.responder_pergunta(pergunta)
        checar(f"D16. busca que já funcionava continua: {pergunta!r}", x.tipo in ("itens", "palpites")
               and not conteudo_de_outro_cancer(x, tipo))

    # ---------- E. falhas e Gemini ----------
    for nome, g in (("erro de rede", Gemini(erro=RuntimeError("fora do ar"))), ("devolveu None", Gemini(valor=None)),
                    ("devolveu lixo", Gemini(valor={"intencao": "xyz"})), ("devolveu texto", Gemini(valor="oi")),
                    ("devolveu id inexistente", Gemini(valor={"intencao": "cancer_de_marte"}))):
        x = ab.responder_pergunta("asdf qwer zxcv", classificar=g)
        checar(f"E1. Gemini {nome}: o guia responde sozinho, sem inventar", x.tipo in ("nada", "palpites") and x.origem == "regras"
               and "Nada foi inventado" in (x.selo or "") or x.tipo == "palpites")
    g = Gemini(valor={"intencao": "mama"})
    for pergunta in ("tenho câncer no intestino", "estou com tosse persistente", "câncer de útero", "sangrei depois da menopausa"):
        ab.responder_pergunta(pergunta, classificar=g)
    checar("E2. com câncer nomeado, sintoma ou ambiguidade o Gemini nem é chamado", g.chamadas == 0)
    g = Gemini(valor={"intencao": "outros"})
    x = ab.responder_pergunta("xyzzy plugh", classificar=g)
    checar("E3. a opção nova 'outros' é aceita do Gemini e o texto continua sendo do guia",
           g.chamadas == 1 and x.origem == "gemini" and apoio.responder(apoio.caminho("outros")).fala in x.fala)
    checar("E4. as opções do Gemini incluem a porta nova", any(i == "outros" for i, _ in ab.OPCOES_IA))
    import ia_linguagem
    chave_antes = ia_linguagem.chave_configurada
    ia_linguagem.chave_configurada = lambda: False
    try:
        checar("E5. sem chave de API não há classificador (a busca segue sozinha)", ab.obter_classificador() is None)
    finally:
        ia_linguagem.chave_configurada = chave_antes
    consulta = apoio.responder
    apoio.responder = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("catálogo com erro"))
    try:
        x = ab.responder_pergunta("quero saber sobre câncer de ovário")
        checar("E6. falha na consulta ao catálogo: aviso seguro (192), sem derrubar a página e sem inventar",
               x.tipo == "erro" and "192" in x.fala and not x.candidatos)
    finally:
        apoio.responder = consulta
    x = ab.responder_pergunta("quanto custa uma passagem para Marte")
    checar("E7. sem correspondência: diz que não achou e não mostra conteúdo de câncer", x.tipo == "nada"
           and not [i for i in destinos(x)[0] if apoio.POR_ID[i]["cancer"]])
    checar("E8. pergunta vazia vira a saudação", ab.responder_pergunta("   ").tipo == "vazio")

    # ---------- F. privacidade ----------
    gravacoes = []
    conectar, abrir = sqlite3.connect, builtins.open

    def sem_banco(*a, **k):
        gravacoes.append(("sqlite", a))
        raise AssertionError("o Apoio não pode abrir banco")

    def abrir_vigiado(arq, modo="r", *a, **k):
        if any(c in str(modo) for c in "wax+"):
            gravacoes.append(("arquivo", arq))
        return abrir(arq, modo, *a, **k)

    sqlite3.connect, builtins.open = sem_banco, abrir_vigiado
    try:
        for pergunta, _, _ in casos[:12] + [("meu marido tá me agredindo", 0, 0), ("tenho um caroço", 0, 0)]:
            ab.responder_pergunta(pergunta, classificar=Gemini(valor=None))
    finally:
        sqlite3.connect, builtins.open = conectar, abrir
    checar("F1. nenhuma pergunta abre banco nem grava arquivo", not gravacoes)
    marca = "texto-secreto-xyz-da-usuaria"
    saida = io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
        ab.responder_pergunta(f"tenho câncer no intestino {marca}")
    checar("F2. o texto da pergunta não vai para a saída nem para log", marca not in saida.getvalue())
    checar("F3. nenhum estado global guarda a pergunta (o contexto é só o tipo de câncer)",
           not any(marca in repr(v) for v in vars(ab).values() if not callable(v) and not isinstance(v, type)))

    # ---------- G. conjunto novo, escrito às cegas (gabarito_apoio_cancer.json) ----------
    import json
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gabarito_apoio_cancer.json"), encoding="utf-8") as f:
        cego = json.load(f)
    n_tipo = n_cancer = n_com_cancer = n_mistura = 0
    for g in cego:
        x = ab.responder_pergunta(g["pergunta"])
        esperado = set(g["cancer"])
        itens, portas = destinos(x)
        if x.tipo in ("nada", "saudacao", "vazio", "erro"):
            portas = set()
        mistura = [i for i in itens if esperado and apoio.POR_ID[i]["cancer"] and not set(apoio.POR_ID[i]["cancer"]) & esperado]
        mistura += [p for p in portas if esperado and p in ("mama", "colo") and p not in esperado]
        acerto = (not esperado) or any(set(apoio.POR_ID[i]["cancer"]) & esperado for i in itens) or bool(portas & esperado)
        n_tipo += x.tipo in g["tipos"]
        n_com_cancer += bool(esperado)
        n_cancer += bool(esperado) and acerto
        n_mistura += bool(mistura)
        if mistura or not acerto or x.tipo not in g["tipos"]:
            print(f"     (conjunto às cegas) {g['pergunta']!r}: {x.tipo}, câncer certo={acerto}, mistura={mistura}")
    print(f"  [às cegas] {len(cego)} perguntas: tipo de resposta esperado {n_tipo}; câncer certo {n_cancer} de {n_com_cancer}; "
          f"respostas misturando câncer {n_mistura}")
    checar("G1. às cegas: NENHUMA resposta leva a conteúdo específico de outro câncer", n_mistura == 0)
    checar("G2. às cegas: tipo de resposta esperado em pelo menos 85%", n_tipo >= 0.85 * len(cego))
    checar("G3. às cegas: o câncer certo aparece em pelo menos 85% das que citam câncer", n_cancer >= 0.85 * n_com_cancer)

    print()
    if falhas:
        print(f"{len(falhas)} falha(s):")
        for f in falhas:
            print(" -", f)
        raise SystemExit(1)
    print("Todas as checagens da cobertura por tipo de câncer passaram.")


if __name__ == "__main__":
    main()
