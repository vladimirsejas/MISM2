import re
from dataclasses import dataclass, field

import apoio
import entendimento as ent
from lia import INICIO, Resposta

# =====================================
# PERGUNTE À LIA no APOIO À MULHER (10/2026, pedido do autor)
#
# Aqui a pessoa é quem PROCURA cuidado, então o desenho é mais cauteloso que o do painel:
#
#   - Nenhuma IA escreve sobre serviço. Telefone, prazo, regra e endereço saem do catálogo
#     conferido (algoritimos/apoio.py: fonte oficial, data de conferência, "a confirmar").
#   - O motor só ESCOLHE quais itens mostrar. Mesma busca do painel (entendimento.Indice:
#     palavras + letras), agora sobre os 81 itens do catálogo e o vocabulário popular de cada porta.
#   - Com confiança alta: o cartão do item, igual ao do clique. Com dúvida: até 3 candidatos em
#     botões ("será que é um destes?"). Sem nada parecido: diz que não achou e mostra as portas.
#   - O Gemini (se ligado) é só a segunda chance de ENTENDER: escolhe uma porta ou lâmina numa lista
#     fechada. O que ele devolve é conferido, e o texto mostrado continua sendo do catálogo.
#   - Segurança primeiro (violência, risco de vida, emergência) e sintoma pessoal têm texto fixo e
#     NÃO passam por IA. As perguntas desta página não são gravadas em lugar nenhum.
#   - A Lia não é médica: não diagnostica e não promete vaga.
# =====================================

# Palavras de quem fala do jeito do dia a dia, por porta (id de apoio.CAMINHOS). Entram na busca de
# todos os itens daquela porta. É vocabulário do domínio, revisável linha a linha.
VOCABULARIO = {
    "mama": "mamografia exame da mama mamas seio peito mastologista mastologia ultrassom das mamas rastreamento "
            "carreta mamografia gratuita sem pedido médico prevenção do câncer de mama",
    "colo": "papanicolau papanicolaou preventivo colo do útero hpv vacina hpv teste de dna colpo exame ginecológico "
            "prevenção do câncer do colo do útero ginecologista",
    "outros": "outros tipos de câncer além da mama e do colo do útero câncer ginecológico sinais e sintomas exames",
    "diagnostico": "exame alterado resultado alterado laudo biópsia birads bi-rads suspeito colposcopia punção investigação "
                   "especialista diagnóstico confirmar câncer",
    "regulacao": "fila vaga encaminhamento encaminhada regulação cross lista de espera demora não me chamaram consulta "
                 "com especialista oncologia acompanhar a fila",
    "tratamento": "quimioterapia quimio radioterapia cirurgia tratamento do câncer oncologia prazo 60 dias hospital onde me tratar "
                  "apoio durante o tratamento peruca",
    "rede": "rede oncológica unacon cacon hospital habilitado hospital de referência onde tratar câncer pelo sus lista de hospitais",
    "direitos": "direitos benefício inss auxílio doença fgts pis imposto de renda isenção tfd transporte para tratamento "
                "diárias reconstrução da mama cartilha",
    "ajuda": "violência agressão ameaça medo ajuda proteção delegacia da mulher ligue 180 medida protetiva psicólogo apoio "
             "emocional sozinha denunciar",
}

# Popular a mais para itens específicos (o texto do catálogo é formal).
EXTRA = {
    # Cada câncer novo tem o seu vocabulário popular (sem palavra solta ambígua: "caroço", "barriga", "sangramento"
    # sozinhos não decidem o câncer; ver PISTAS e AMBIGUAS).
    "cancer_intestino": "câncer no intestino cólon reto colorretal câncer de intestino sangue nas fezes mudança no intestino "
                        "intestino preso intestino solto colonoscopia pólipo teste de sangue oculto nas fezes fit",
    "cancer_ovario": "câncer de ovário ovários câncer ginecológico barriga inchada que não passa dor pélvica dor na pelve "
                     "ovario cisto no ovário",
    "cancer_pele": "câncer de pele pele não melanoma melanoma carcinoma basocelular espinocelular pinta mancha ferida que não cicatriza ferida que não fecha "
                   "lesão que sangra pintinha protetor solar sol dermatologista",
    "cancer_pulmao": "câncer de pulmão pulmões tosse persistente tosse que não passa sangue no escarro falta de ar cigarro "
                     "fumar parar de fumar tabagismo fumante",
    "cancer_tireoide": "câncer de tireoide tiroide nódulo na tireoide caroço no pescoço nódulo no pescoço caroço na garganta "
                       "papo ultrassom da tireoide punção",
    "cancer_corpo_utero": "câncer de endométrio corpo do útero útero endométrio sangramento depois da menopausa "
                          "sangramento na menopausa diferença entre câncer do colo do útero e do endométrio histeroscopia",
    "inca_tipos_cancer": "outros tipos de câncer câncer de estômago câncer de próstata leucemia linfoma lista de tipos de câncer inca",
    "lei_30_dias": "prazo exames quantos dias demora diagnóstico lei",
    "lei_60_dias": "prazo começar tratamento quantos dias quimioterapia radioterapia lei 60 dias demora",
    "nao_achei_nome": "meu nome não aparece lista fila parada ninguém me chamou esperando",
    "tfd": ["tfd", "sigla tfd tratamento fora do domicílio transporte ônibus ambulância ir para outra cidade tratar viagem diárias passagem"],
    "fgts_pis": "sacar fgts pis pasep dinheiro do fundo de garantia",
    "auxilio_inss": "afastamento do trabalho licença imposto de renda isenção aposentadoria por invalidez",
    "reconstrucao_mamaria": "refazer o seio prótese depois da cirurgia retirada da mama mastectomia",
    "rc_perucas": "peruca cabelo queda de cabelo quimioterapia",
    "ligue_180": "denunciar violência telefone número central",
    "casa_mulher_brasileira": "acolhimento mulher violência abrigo atendimento integrado",
    "rc_patrulha": "guarda municipal medida protetiva acompanhamento mulher ameaçada",
    "defensoria_nudem": "medida protetiva advogado gratuito direitos da mulher",
    "carretas_estado": "carreta caminhão mamografia itinerante quando passa calendário",
    "caminho_do_exame": "nunca fiz mamografia idade para começar quantos anos primeira vez por onde começar passo a passo primeira consulta pedido médico unidade de saúde",
    "rc_unidades": "posto de saúde ubs usf unidade de saúde perto de casa ginecologista consulta",
    "rc_cadu_agendamento": "marcar consulta exame agendamento telefone prefeitura",
    "preventivo_alterado": "papanicolau papanicolaou deu alterado resultado alterado exame do colo alterado",
    "mamografia_alterada": "mamografia deu alterada resultado alterado laudo birads 3 4 5",
    "cartilha_inca": "quais são os direitos de quem tem câncer direitos da pessoa com câncer guia de direitos",
    "rede_oncologica": "unacon cacon o que é unacon centro de assistência de alta complexidade em oncologia",
    "rc_gacc": "filho filha criança com câncer infantil pediátrico grupo de apoio gacc",
    "mulheres_de_peito": "0800 779 0000 agendar mamografia pelo telefone central de agendamento sem pedido médico",
    "lista_regulacao": "acompanhar a fila ver a fila da regulação posição na lista de espera consultar",
}

SEGURANCA_ETAPA = "violencia"   # etapa da Lia com os canais de proteção (apoio.ETAPAS)
ALTO, FOLGA, BAIXO, NOTA_FORA = 0.30, 0.05, 0.17, 0.25   # escolhidos no conjunto de desenvolvimento (teste_apoio_busca.py)


def _documentos():
    docs = []
    for i in apoio.ITENS:
        extra = EXTRA.get(i["id"]) or []
        frases = [i["titulo"], i["resumo"], i["onde"], i["para_quem"], (i["como"] or "")[:260],
                  VOCABULARIO.get(i["caminho"])] + ([extra] if isinstance(extra, str) else list(extra))
        docs.append({"id": i["id"], "frases": [f for f in frases if f]})
    return docs


INDICE = ent.Indice(_documentos())


# ---------- TRAVA POR TIPO DE CÂNCER (10/2026) ----------
# Falha encontrada pelo autor: quem perguntava de outro câncer caía em mamografia, porque a busca por semelhança de
# palavras não sabe que "intestino" e "mama" são doenças diferentes. A trava vem ANTES da semelhança: se a pessoa cita um
# tipo de câncer, o conteúdo específico de OUTRO tipo sai da disputa (nota zero) e o cartão principal do tipo citado ganha um bônus. O que
# não é específico de câncer nenhum (rede, regulação, direitos, hospitais) continua valendo para todos.
# Palavra solta do dia a dia ("caroço", "peito", "barriga", "sangramento") NUNCA decide o câncer sozinha: ver AMBIGUAS.
BONUS_PRINCIPAL = 0.25   # só o cartão geral do câncer citado: vence os hospitais e serviços que apenas o mencionam.
                         # Os demais itens do tipo NÃO ganham bônus (mama e colo continuam disputando como antes).

_PALAVRA_CANCER = re.compile(r"\b(cancer|cancro|tumor|neoplasia|oncologi\w*|ca)\b")
# A ordem importa: o trecho reconhecido sai do texto antes de procurar o próximo ("colo retal" não vira "colo do útero").
_FORTES = [
    ("colorretal", r"colorretal|colo ?retal|colonoscopia|sangue oculto"),
    ("colo", r"colo (do |de |)uter\w*|colo uterino|papanicola\w*|preventivo|\bhpv\b|colposcopia"),
    ("endometrio", r"endometri\w*|corpo (do )?uter\w*|histeroscopia"),
    ("mama", r"\bmamas?\b|mamograf\w*|mastolog\w*|mastectomia|\bseios?\b|bi ?rads"),
    ("ovario", r"ovari\w*"),
    ("tireoide", r"tir?eoid\w*|tiroid\w*"),
    ("pulmao", r"pulm\w+"),
    ("pele", r"nao melanoma|melanoma|cancer (de |na |da )pele|tumor (de |na )pele|basocelular|espinocelular"),
]
_SO_COM_CANCER = [   # palavras comuns do corpo: só indicam o tipo quando a pessoa também fala em câncer
    ("colorretal", r"intestin\w*|\bcolon\b|\breto\b|\bretal\b"),
    ("pele", r"\bpele\b"),
    ("mama", r"\bpeitos?\b"),
]
_NAO_COBERTOS = (r"(?:cancer|tumor|neoplasia|ca) (?:de |do |da |no |na |dos |das )?(estomago|figado|pancreas|cerebro|bexiga|"
                 r"rim|boca|esofago|osso|ossos|garganta|laringe|vagina|vulva|prostata|testiculo|vesicula)\b|"
                 r"\b(leucemia|linfoma|mieloma)\b")
_NOME_NAO_COBERTO = {"estomago": "estômago", "figado": "fígado", "pancreas": "pâncreas", "cerebro": "cérebro",
                     "esofago": "esôfago", "osso": "osso", "ossos": "osso", "testiculo": "testículo", "vesicula": "vesícula",
                     "prostata": "próstata"}


def tipos_citados(pergunta):
    """(tipos citados, na ordem em que aparecem; "câncer de útero" sem dizer colo ou corpo?; nome de um câncer que o
    guia não detalha ou None). Cita = nomeia a doença, o órgão ou o exame que só serve a ela."""
    texto = " " + ent.normalizar(pergunta) + " "
    com_cancer = bool(_PALAVRA_CANCER.search(texto))
    achados, resto = [], texto
    for tipo, padrao in _FORTES + (_SO_COM_CANCER if com_cancer else []):
        ocorrencias = list(re.finditer(padrao, resto))
        if ocorrencias:   # tira TODAS: "HPV e câncer de colo do útero" não pode deixar "útero" sobrando
            achados.append((ocorrencias[0].start(), tipo))
            for m in ocorrencias:
                resto = resto[:m.start()] + " " * (m.end() - m.start()) + resto[m.end():]
    tipos = []
    for _, t in sorted(achados):
        if t not in tipos:
            tipos.append(t)
    utero_ambiguo = com_cancer and bool(re.search(r"\buter\w*", resto))
    nao = re.search(_NAO_COBERTOS, resto)
    outro = None
    if nao:
        palavra = nao.group(1) or nao.group(2)
        outro = _NOME_NAO_COBERTO.get(palavra, palavra)
    return tipos, utero_ambiguo, outro


# Sintomas descritos em palavras do dia a dia que apontam para um tipo. NÃO são diagnóstico: servem só para oferecer a
# informação geral sobre os sinais que merecem avaliação, depois do texto fixo de sintoma.
PISTAS = [
    ("colorretal", r"sangue .{0,14}fezes|fezes com sangue|fezes sangu\w+|mudanca (no|do) (intestino|habito intestinal)|"
                   r"intestino (preso|solto)"),
    ("pele", r"ferida (que )?(nao|nunca) (cicatriza|fecha|sara)|ferida (na|da|em) pele|ferida que demora|lesao (na pele )?que sangra|"
             r"(pinta|pintinha|mancha|sinal) .{0,20}(mudou|cresceu|cresce|sangra|coca|escureceu|aumentou|esta crescendo)"),
    ("pulmao", r"tosse (que )?(nao passa|persistente|constante|ha (semanas|meses))|tosse com sangue|sangue (no|na) (escarro|catarro)|"
               r"falta de ar"),
    ("tireoide", r"(nodulo|caroco|bolinha|inchaco|bola) (no|na) (pescoco|garganta)|rouquidao"),
    ("endometrio", r"sangramento (depois|apos|pos) (d[ao] |a )?menopausa|sangr\w+ (depois|apos) (d[ao] |a )?menopausa|"
                   r"menopausa .{0,25}sangr\w+"),
    ("ovario", r"barriga (inchada|aumentada|estufada) (ha|faz|por|que nao)|dor pelvica|(dor|pressao|peso) (na|no) (pelve|parte baixa da barriga)"),
]
# Palavras sozinhas que servem a vários cânceres (ou a nenhum): pedem uma pergunta de volta, não um palpite.
AMBIGUAS = re.compile(r"\b(caroco|caroços?|nodulo|bolinha|sangramento|sangrando|sangrou|barriga|mancha|ferida|peitos?)\b")
ONDE_E = ("Para eu mostrar a informação certa, me conta em que parte do corpo é: na mama, no pescoço, na pele ou "
          "sangramento pela vagina?")
# Pedido de visão geral ("quero informações sobre câncer de mama") x pedido de serviço ("onde faço mamografia de graça?").
# Só o primeiro abre o cartão ou a porta do câncer; o segundo continua mostrando as opções de serviço.
_VISAO_GERAL = re.compile(r"\b(informacoes?|saber|sobre|entender|explica\w*|o que e|conhecer|sinais|sintomas|como funciona)\b")
_PEDE_SERVICO = re.compile(r"\b(onde|agend\w*|marc\w*|gratis|gratuit\w*|perto|telefone|endereco|carreta|vaga|fila|hospital|posto|ubs)\b")
# Relato pessoal de sintoma ("tenho", "estou com", "senti"): só então o aviso de cuidado vem antes da informação.
_RELATO = re.compile(r"\b(tenho|estou|estava|sinto|sentindo|senti|notei|percebi|apareceu|surgiu|minha|meu)\b")
# Continuação da conversa: "e os sinais?", "como trata?" (só com um câncer já em foco, e só em pergunta curta)
_CONTINUA = re.compile(r"\b(sinais?|sintomas?|tratamento|trata|exames?|diagnostico|prevencao|prevenir|rastreamento|risco|fatores|causas?|"
                       r"biopsia|acompanhamento|cura|curavel|quem tem)\b")


def pistas_de(pergunta):
    texto = " " + re.sub(r"\bq\b", "que", ent.normalizar(pergunta)) + " "
    return [t for t, padrao in PISTAS if re.search(padrao, texto)]


def buscar(pergunta, n=3, tipos=()):
    """[(id do item, nota)] dos n mais parecidos com a pergunta, do maior para o menor.
    Com `tipos`: item específico de OUTRO câncer sai da disputa; o cartão principal do tipo citado ganha BONUS_PRINCIPAL."""
    notas = INDICE.notas(pergunta)
    if tipos:
        for id in notas:
            do_item = apoio.POR_ID[id]["cancer"]
            if do_item and not set(do_item) & set(tipos):
                notas[id] = 0.0
            elif do_item and id in apoio.ITEM_PRINCIPAL.values():
                notas[id] = min(1.0, notas[id] + BONUS_PRINCIPAL)
    return sorted(notas.items(), key=lambda kv: -kv[1])[:n]


def _diagnostico_recente(pergunta):
    """Reconhece pedidos pessoais explícitos sobre diagnóstico confirmado, antes da busca por itens."""
    texto = ent.normalizar(pergunta)
    menciona_cancer = any(p in texto for p in ("cancer", "tumor maligno", "neoplasia maligna"))
    relata_diagnostico = any(p in texto for p in (
        "recebi diagnostico", "recebi o diagnostico", "recebi um diagnostico",
        "acabei de receber diagnostico", "acabei de receber um diagnostico", "acabei de receber o diagnostico",
        "acabou de receber diagnostico", "acabou de receber o diagnostico", "recebeu diagnostico", "recebeu o diagnostico",
        "acabei de receber um laudo", "recebi um laudo que confirma", "meu laudo confirmou",
        "minha biopsia confirmou", "biopsia confirmou", "laudo confirmou", "laudo confirma",
        "fui diagnosticada", "fui diagnosticado", "me diagnosticaram",
        "descobri que tenho cancer", "descobri um cancer", "descobri cancer",
        "acabou de descobrir um cancer", "acabou de descobrir cancer", "acaba de descobrir cancer",
    ))
    return menciona_cancer and relata_diagnostico


# ---------- respostas ----------

@dataclass
class RespostaApoio(Resposta):
    pergunta: str = None
    tipo: str = "itens"        # itens | palpites | nada | risco | sintoma | saudacao | vazio
    origem: str = "regras"     # regras | gemini
    selo: str = None
    candidatos: list = field(default_factory=list)   # ids dos itens oferecidos
    tipo_cancer: str = None    # câncer em foco depois desta resposta (só na memória da sessão, nunca gravado)


def _de(resposta, **extra):
    return RespostaApoio(fala=resposta.fala, expressao=resposta.expressao, botoes=list(resposta.botoes),
                         destino=resposta.destino, numeros=list(resposta.numeros), **extra)


def _com_inicio(r):
    if not any(a.get("tipo") == "inicio" for _, a in r.botoes):
        r.botoes = r.botoes + [("Começar de novo", INICIO)]
    return r


SELO_GUIA = f"Texto do guia, conferido em {apoio.CONFERIDO}. Nenhuma IA escreveu sobre o serviço."

# A opção do Gemini: portas e lâminas (lista fechada).
OPCOES_IA = [(c, f"{r}: {dentro}") for c, r, dentro, _ in apoio.CAMINHOS] + [
    ("hospitais", "hospitais de câncer pelo SUS no Estado"), ("carretas", "carretas da mamografia: onde e quando"),
    ("rio_claro", "serviços de saúde e apoio em Rio Claro"), ("barretos", "Hospital de Amor de Barretos")]
CONTEXTO_IA = ("um guia de serviços de apoio a mulheres sobre prevenção, diagnóstico e tratamento de câncer pelo SUS, "
               "direitos e proteção contra violência")


def obter_classificador():
    """O Gemini como segunda chance de entender, se a chave estiver no .env; senão None (a busca segue sozinha)."""
    try:
        import ia_linguagem
        return ia_linguagem.classificar_pergunta if ia_linguagem.chave_configurada() else None
    except Exception:
        return None


def _acao_da_opcao(escolha):
    if escolha in apoio.NOME_CAMINHO:
        return apoio.caminho(escolha)
    if escolha in ("hospitais", "carretas", "rio_claro", "barretos"):
        return apoio.lamina(escolha)
    return None


def _destino_do_tipo(tipo):
    return {"aba": apoio.LAMINAS["caminho"], "caminho": tipo if tipo in ("mama", "colo") else "outros"}


def _ids_dos_botoes(botoes):
    return [a["id"] for _, a in botoes if a.get("tipo") == "apoio_item"]


def _ids_mostrados(acao, resposta):
    """Os itens que a resposta abriu (o do próprio botão, se for um cartão) e os que oferece em seguida."""
    return ([acao["id"]] if acao.get("tipo") == "apoio_item" else []) + _ids_dos_botoes(resposta.botoes)


def _tipo_do_item(id, tipos):
    """O câncer em foco depois de mostrar um item: o dele, se for específico de um só; senão o citado na pergunta."""
    do_item = apoio.POR_ID[id]["cancer"]
    if len(do_item) == 1:
        return do_item[0]
    return tipos[0] if len(tipos) == 1 else None


CUIDADO_SINTOMA = ("Um sinal no corpo pode ter várias causas e, sozinho, não quer dizer que seja câncer. Se ele dura ou "
                   "preocupa, procure a unidade de saúde para ser examinada.")


def _escolher_tipos(opcoes, utero_ambiguo, comum):
    """Mais de um câncer na pergunta (ou "câncer de útero"): a Lia não escolhe por ela, mostra as opções."""
    nomes = " e ".join(apoio.TIPOS_CANCER[t] for t in opcoes[:2]) if len(opcoes) <= 2 else ", ".join(
        apoio.TIPOS_CANCER[t] for t in opcoes)
    if utero_ambiguo:
        fala = ("\"Câncer de útero\" pode ser o **câncer do colo do útero** (a parte de baixo, ligada ao vírus HPV) ou o "
                "**câncer do corpo do útero**, o endométrio (a parte de cima). São doenças diferentes, com sinais, exames e "
                "cuidados próprios. Qual você quer ver?")
    else:
        fala = (f"Você falou de mais de um câncer: {nomes}. São doenças diferentes, com sinais, exames e cuidados "
                "próprios, e eu não vou misturar uma com a outra. Qual você quer ver primeiro?")
    if "colo" in opcoes and "endometrio" in opcoes:
        fala += (" Uma diferença importante: o preventivo (Papanicolau) e o teste de HPV procuram o câncer do colo do "
                 "útero, não o do corpo do útero.")
    r = Resposta(fala=fala, expressao="explicando",
                 botoes=[(f"Ver {apoio.TIPOS_CANCER[t]}", apoio.abertura_do_tipo(t)) for t in opcoes],
                 destino=_destino_do_tipo(opcoes[0]))
    return _com_inicio(_de(r, tipo="palpites", selo=SELO_GUIA, candidatos=_ids_dos_botoes(r.botoes), **comum))


def _responder_pergunta(pergunta, classificar=None, contexto=None):
    """Entende a pergunta e devolve uma resposta do guia. `classificar`: função do Gemini
    (pergunta, opções, contexto=, com_cancer=) -> {"intencao"} ou None; só é chamada sem confiança.
    `contexto`: o câncer em foco na resposta anterior (resposta.tipo_cancer), só da sessão; serve para "e os sinais?"."""
    pergunta = (pergunta or "").strip()
    comum = dict(pergunta=pergunta)
    if not pergunta:
        return _de(apoio.saudacao(), tipo="vazio", **comum)

    social = ent.compreender(pergunta)   # segurança, conversa social e sintoma: mesmas regras do painel
    if social.tipo == "risco":
        import assistente
        canais = ([(apoio.POR_ID[i["id"]]["titulo"], apoio.item(i["id"])) for i in apoio.itens_da_etapa(SEGURANCA_ETAPA)[:3]]
                  if social.risco == "violencia" else [])
        r = Resposta(fala=assistente.SEGURANCA[social.risco], expressao="acolhedora",
                     botoes=canais + [("Em que ponto você está?", apoio.caminho("ajuda"))],
                     destino={"aba": apoio.LAMINAS["caminho"], "caminho": "ajuda"})
        return _com_inicio(_de(r, tipo="risco", selo="Texto fixo de segurança. A IA não é usada aqui.", **comum))
    if social.tipo == "saudacao":
        return _de(apoio.saudacao(), tipo="saudacao", **comum)

    # Trava por tipo de câncer: o que a pessoa nomeou manda; semelhança de palavras só desempata dentro do tipo.
    tipos, utero_ambiguo, outro = tipos_citados(pergunta)
    pistas_ = pistas_de(pergunta)
    opcoes = list(tipos) + [t for t in (("colo", "endometrio") if utero_ambiguo else ()) if t not in tipos]
    if len(opcoes) >= 2:
        return _escolher_tipos(opcoes, utero_ambiguo, comum)
    if outro and not tipos:
        r = Resposta(fala=(f"O guia ainda não tem uma orientação específica sobre o câncer de {outro}, e não vou mostrar a de "
                           "outro câncer no lugar. O caminho no SUS é parecido para qualquer câncer: unidade de saúde, "
                           "exames, regulação e hospital habilitado em oncologia. O INCA tem uma página para cada tipo."),
                     expressao="cautelosa",
                     botoes=[("Páginas do INCA por tipo de câncer", apoio.item("inca_tipos_cancer")),
                             ("Exame alterado ou diagnóstico", apoio.caminho("diagnostico")),
                             ("Rede oncológica", apoio.caminho("rede")), ("Seus direitos", apoio.caminho("direitos"))],
                     destino={"aba": apoio.LAMINAS["caminho"], "caminho": "outros"})
        return _com_inicio(_de(r, tipo="nada", selo="Nada foi inventado: o guia só mostra o que está no catálogo.", **comum))
    texto_norm = ent.normalizar(pergunta)
    if (contexto in apoio.TIPOS_CANCER and not tipos and not pistas_ and len(texto_norm.split()) <= 8
            and _CONTINUA.search(texto_norm)):   # "e os sinais?" depois de falar de um câncer
        abertura = apoio.abertura_do_tipo(contexto)
        r = apoio.responder(abertura)
        resposta = _de(r, tipo="itens", selo=SELO_GUIA, tipo_cancer=contexto, candidatos=_ids_mostrados(abertura, r),
                       **comum)
        resposta.fala = f"Continuando sobre o {apoio.TIPOS_CANCER[contexto]}:\n\n" + r.fala
        return resposta

    achados = buscar(pergunta, tipos=tipos)
    (id1, n1), (_, n2) = achados[0], achados[1]

    direto = n1 >= ALTO and (n1 - n2) >= FOLGA
    parece_sintoma = (social.tipo == "intencao" and social.intencao == "sintoma") or (
        social.tipo == "palpites" and social.palpites and social.palpites[0][0] == "sintoma")
    so_pista = bool(pistas_) and not tipos
    relato = bool(_RELATO.search(texto_norm))
    # "quais os sinais do câncer de mama?" pede informação; só o relato pessoal ("tenho", "minha") vira texto de sintoma
    pede_informacao = bool(tipos) and bool(_VISAO_GERAL.search(texto_norm)) and not relato
    ambiguo_sem_tipo = bool(AMBIGUAS.search(texto_norm)) and not tipos and not pistas_ and (parece_sintoma or relato)
    if ((parece_sintoma and not pede_informacao and (not direto or ambiguo_sem_tipo)) or so_pista
            or ambiguo_sem_tipo):   # sem um item claro para o que ela descreve
        import assistente
        para_ler = [t for t in (list(tipos) + pistas_) if t in apoio.TIPOS_CANCER]
        # "Caminho do exame" é da mamografia: só acompanha o sintoma quando ele não aponta para outro câncer
        # palavra ambígua sem nada de mama ("tenho um caroço"): as opções "Na mama..." já cobrem o exame; com "peito" fica
        ambiguo = not para_ler and bool(AMBIGUAS.search(texto_norm)) and not re.search(r"\b(peitos?|seios?|mamas?)\b", texto_norm)
        do_exame = [("Caminho do exame", apoio.item("caminho_do_exame"))] if (not para_ler and not ambiguo) or "mama" in para_ler else []
        r = Resposta(fala=assistente.SINTOMA.replace("Na página **Apoio à mulher** está o caminho do cuidado (exames, rede oncológica, direitos). "
                                                     "Em **Onde ser atendida**, as unidades da sua cidade.",
                                                     "Aqui no guia estão o caminho do exame e o que fazer depois."),
                     expressao="acolhedora",
                     botoes=do_exame + [("Exame alterado ou diagnóstico", apoio.caminho("diagnostico")),
                                        ("Unidades de Saúde em Rio Claro", apoio.item("rc_unidades"))],
                     destino={"aba": apoio.LAMINAS["caminho"], "caminho": "diagnostico"})
        if para_ler:   # informação geral sobre os sinais, nunca "você tem"
            r.fala += ("\n\nSe quiser entender o que costuma ser investigado, abaixo está a informação geral sobre os sinais "
                       "que merecem avaliação. Ela não diz o que você tem.")
            r.botoes = [(f"Sinais e exames: {apoio.TIPOS_CANCER[t]}", apoio.abertura_do_tipo(t)) for t in para_ler[:2]] + r.botoes
            r.destino = _destino_do_tipo(para_ler[0])
        elif ambiguo_sem_tipo or AMBIGUAS.search(texto_norm):
            r.fala += "\n\n" + ONDE_E
            r.botoes = [("Na mama", apoio.caminho("mama")), ("No pescoço (tireoide)", apoio.item("cancer_tireoide")),
                        ("Na pele", apoio.item("cancer_pele")),
                        ("Sangramento pela vagina", apoio.item("cancer_corpo_utero"))] + r.botoes
        return _com_inicio(_de(r, tipo="sintoma", selo="Texto fixo. A IA não improvisa sobre sintomas.",
                               tipo_cancer=para_ler[0] if len(para_ler) == 1 else None, **comum))
    if _diagnostico_recente(pergunta):
        # Não deixar semelhança lexical transformar um diagnóstico confirmado em mamografia ou hospital aleatório.
        r = apoio.responder(apoio.etapa("diagnostico_cancer"))
        if len(tipos) == 1:   # o câncer dito também tem o seu cartão (sinais, exames, tratamento)
            r.botoes = [(f"Sobre o {apoio.TIPOS_CANCER[tipos[0]]}", apoio.abertura_do_tipo(tipos[0]))] + r.botoes
        return _de(r, tipo="etapa", selo="Orientação fixa do guia; a Lia não escolhe hospital nem tratamento.",
                   tipo_cancer=tipos[0] if len(tipos) == 1 else None, **comum)
    # parece "previsão do tempo", não um item do guia; mas evidência clara de item vence esse sinal geral
    # ("o que é UNACON" lembra "o que é inflação"). Quem nomeou um câncer está sempre no assunto.
    fora_do_assunto = social.tipo == "fora" and n1 < NOTA_FORA and not tipos
    if not fora_do_assunto and direto:
        r = apoio.responder(apoio.item(id1))
        outros = [(f"Ver também: {apoio.POR_ID[i]['titulo']}", apoio.item(i)) for i, n in achados[1:] if n >= BAIXO][:2]
        resposta = _de(r, tipo="itens", selo=SELO_GUIA, candidatos=[id1], tipo_cancer=_tipo_do_item(id1, tipos), **comum)
        resposta.fala = "Pelo que você escreveu, isto parece ser o que você procura:\n\n" + r.fala
        if tipos and (pistas_ or (parece_sintoma and _RELATO.search(texto_norm))):   # citou o câncer E um sintoma: acolhe antes
            resposta.fala = CUIDADO_SINTOMA + "\n\n" + resposta.fala
        resposta.botoes = outros + r.botoes
        return resposta
    visao_geral = len(tipos) == 1 and _VISAO_GERAL.search(texto_norm) and not _PEDE_SERVICO.search(texto_norm)
    if len(tipos) == 1 and (n1 < BAIXO or visao_geral):
        # citou um câncer e quer a visão geral (ou nada parecido sobrou): o cartão ou a porta do PRÓPRIO câncer
        abertura = apoio.abertura_do_tipo(tipos[0])
        r = apoio.responder(abertura)
        resposta = _de(r, tipo="itens", selo=SELO_GUIA, tipo_cancer=tipos[0], candidatos=_ids_mostrados(abertura, r), **comum)
        resposta.fala = f"Sobre o {apoio.TIPOS_CANCER[tipos[0]]}, o guia tem isto:\n\n" + r.fala
        return resposta
    if not fora_do_assunto and n1 >= BAIXO:
        candidatos = [i for i, n in achados if n >= BAIXO]
        linhas = "\n".join(f"- **{apoio.POR_ID[i]['titulo']}**: {apoio.POR_ID[i]['resumo']}." for i in candidatos)
        r = Resposta(fala="Não tenho certeza do que você procura. Encontrei estes itens do guia, e o primeiro é o que mais se parece:\n\n"
                          + linhas, expressao="explicando",
                     botoes=[(apoio.POR_ID[i]["titulo"], apoio.item(i)) for i in candidatos],
                     destino={"aba": apoio.LAMINAS["caminho"]})
        return _com_inicio(_de(r, tipo="palpites", selo=SELO_GUIA, candidatos=candidatos,
                               tipo_cancer=tipos[0] if len(tipos) == 1 else None, **comum))

    if classificar is not None:   # segunda chance: o Gemini escolhe uma porta ou lâmina da lista fechada
        try:
            escolha = classificar(pergunta, OPCOES_IA, contexto=CONTEXTO_IA, com_cancer=False)
        except Exception:
            escolha = None
        acao = _acao_da_opcao(escolha.get("intencao")) if isinstance(escolha, dict) else None
        if acao is not None:
            r = apoio.responder(acao)
            resposta = _de(r, tipo="itens", origem="gemini",
                           selo="A IA ajudou a entender a pergunta. O texto abaixo é do guia, não da IA.", **comum)
            resposta.fala = "Acho que você procura isto:\n\n" + r.fala
            return resposta
    r = apoio.saudacao()
    r.fala = ("Não encontrei isso no guia. Ele cobre prevenção, exames, diagnóstico, regulação, tratamento, direitos e proteção "
              "contra violência, e os principais tipos de câncer. Escolha uma porta, ou escreva de outro jeito. Se for sobre a "
              "sua saúde agora, procure a unidade de saúde; em emergência, ligue 192.")
    return _de(r, tipo="nada", selo="Nada foi inventado: o guia só mostra o que está no catálogo.", **comum)


SEM_CONSULTA = ("Não consegui consultar o guia agora. Tente de novo em instantes. Se for sobre a sua saúde, procure a unidade "
                "de saúde do seu bairro; em emergência, ligue 192.")


def responder_pergunta(pergunta, classificar=None, contexto=None):
    """Igual a _responder_pergunta, mas uma falha inesperada na consulta ao catálogo vira um aviso, nunca uma página
    quebrada nem uma resposta improvisada. Nada da pergunta é registrado."""
    try:
        return _responder_pergunta(pergunta, classificar=classificar, contexto=contexto)
    except Exception:
        r = Resposta(fala=SEM_CONSULTA, expressao="cautelosa", botoes=[("Começar de novo", INICIO)],
                     destino={"aba": apoio.LAMINAS["caminho"]})
        return _de(r, tipo="erro", selo="Nada foi inventado: o guia não pôde ser consultado.",
                   pergunta=(pergunta or "").strip())
