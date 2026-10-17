import re
from dataclasses import dataclass, field

import entendimento as ent
from inteligencia import (
    MODELOS_PREVISAO,
    anos_incompletos,
    cancer_de,
    formatar_numero,
    nome_doenca,
    prever_com_validacao,
    previsao_todos,
    leitura_previsao,
    resumo_doencas,
    serie_doenca,
    _variacao_pct,
)
from lia import INICIO, Resposta, caminho, responder as lia_responder, sobre

# =====================================
# ASSISTENTE DA LIA — a caixa "Pergunte à Lia" (10/2026)
#
# Fluxo: ENTENDER (entendimento.py) -> CALCULAR -> REDIGIR.
#
#   CALCULAR reaproveita a árvore da Lia (lia.responder): são os mesmos
#   números e as mesmas frases dos botões e dos gráficos, já com as regras
#   de meses ausentes, valor registrado e ano incompleto. Assim a caixa
#   nunca diz uma coisa e o painel outra. O que a Lia não tem (previsão
#   validada, óbitos e tempo de todos os cânceres, ajuda, segurança) é
#   montado aqui, também só com inteligencia.py.
#
#   REDIGIR: o Gemini reescreve a resposta da Lia para a pergunta feita.
#   Só em respostas de DADOS. Segurança, sintomas, apoio e encaminhamentos
#   usam texto fixo (a IA não improvisa onde há risco). Todo texto da IA
#   passa por conferência: número que não esteja na base, "vai ficar" ou
#   explicação de causa fazem o texto ser descartado e a resposta direta
#   da Lia aparecer no lugar. Sem chave, sem rede ou sem cota: resposta
#   direta, o painel nunca fica mudo.
# =====================================


@dataclass
class RespostaIA(Resposta):
    """Uma Resposta da Lia com o que a caixa de perguntas acrescenta."""
    pergunta: str = None
    intencao: str = None
    cancer: str = None            # câncer realmente usado (citado, herdado ou em foco)
    tipo: str = "intencao"        # intencao | palpites | fora | risco | saudacao | vazio
    origem: str = "regras"        # regras | seguimento | gemini | escolha
    selo: str = None              # "Redigido pela IA..." ou "Resposta direta..."
    base: str = None              # a resposta determinística, quando a IA a reescreveu
    usou_ia: bool = False
    ia_motivo: str = None         # por que a IA não foi usada / foi descartada
    links: list = field(default_factory=list)   # [(rótulo, página)]
    fonte: str = None             # de onde vêm os números e o limite principal (só respostas de dados)


@dataclass
class IA:
    explicar: object = None       # (pergunta, base, perfil) -> texto
    classificar: object = None    # (pergunta, opções) -> {"intencao", "cancer"}
    ligada: bool = False


def obter_ia():
    """O Gemini, se a chave estiver no .env; senão, tudo desligado (a caixa continua funcionando)."""
    try:
        import ia_linguagem
        if not ia_linguagem.chave_configurada():
            return IA()
        return IA(explicar=ia_linguagem.redigir_resposta, classificar=ia_linguagem.classificar_pergunta, ligada=True)
    except Exception:
        return IA()


# ---------- conferência do texto da IA ----------

def _numeros(texto):
    """Números do texto sem separadores ("1.668" e "1668" são iguais; "5,3" -> "53"); ignora 1 dígito."""
    achados = re.findall(r"\d+(?:[.,]\d+)*", texto)
    return {re.sub(r"[.,]", "", n) for n in achados if len(re.sub(r"[.,]", "", n)) >= 2}


def numeros_novos(texto_ia, *fontes):
    """Números do texto da IA que não aparecem em nenhuma das fontes (base, pergunta)."""
    permitidos = set()
    for fonte in fontes:
        permitidos |= _numeros(fonte)
    return sorted(_numeros(texto_ia) - permitidos)


PROMETE = re.compile(r"\b(vai|ira|irá|vao|vão) (ficar|ter|aumentar|diminuir|crescer|cair|chegar|subir|piorar|melhorar)\b", re.I)
CAUSA_ATRIBUIDA = re.compile(r"\b(por causa d\w+|devido (a|ao|aos|à|às)|causad[oa]s? (por|pel)\w*|provocad[oa]s? (por|pel)\w*|"
                   r"por conta d\w+|resultado d[eao]s?)\b", re.I)


def conferir(texto_ia, base, pergunta):
    """None se o texto da IA pode ser mostrado; senão, o motivo de descartá-lo."""
    if not texto_ia or not texto_ia.strip():
        return "a IA devolveu texto vazio"
    if len(texto_ia) > 1800:
        return "a IA escreveu demais"
    if re.search(r"https?://|www\.|\]\(", texto_ia):
        return "a IA incluiu um link; só o Escudo aponta para páginas"
    novos = numeros_novos(texto_ia, base, pergunta)
    if novos:
        return "a IA citou número que não está nos cálculos: " + ", ".join(novos[:3])
    if PROMETE.search(texto_ia):
        return "a IA prometeu um resultado ('vai ficar'); projeção é só tendência"
    if CAUSA_ATRIBUIDA.search(texto_ia):
        return "a IA atribuiu causa; o Escudo detecta, não explica"
    return None


# ---------- textos fixos (nunca passam pela IA) ----------

SEGURANCA = {
    "violencia": (
        "Sinto muito que você esteja passando por isso. **Você não está sozinha e a culpa não é sua.**\n\n"
        "Se há perigo agora, ligue **190** (Polícia). A **Central de Atendimento à Mulher, Ligue 180**, é gratuita, "
        "funciona 24 horas e também atende por WhatsApp.\n\n"
        "Eu sou uma ferramenta de dados e não consigo acompanhar o seu caso. A página **Apoio à mulher** "
        "tem os canais de proteção."),
    "suicidio": (
        "Sinto muito que você esteja sentindo tanta dor. **Você merece apoio agora.**\n\n"
        "Ligue para o **CVV, 188** (gratuito, 24 horas, todos os dias) ou converse pelo chat deles. Se houver risco "
        "imediato, ligue **192** (SAMU) ou **190**. Se puder, fique perto de alguém de confiança.\n\n"
        "Eu sou uma ferramenta de dados e não substituo uma pessoa. A página **Apoio à mulher** reúne outros canais."),
    "emergencia": (
        "Isso pode ser uma emergência. **Ligue 192 (SAMU)** ou vá agora à UPA ou ao pronto-socorro mais próximo.\n\n"
        "Não espere uma resposta aqui: eu sou uma ferramenta de dados e não posso avaliar sintomas."),
}

SINTOMA = (
    "Sinto muito que você esteja com essa preocupação. **Eu não faço diagnóstico** e não consigo dizer o que "
    "isso é: só um profissional de saúde pode avaliar.\n\n"
    "O que costuma ajudar: procure, o quanto antes, a **Unidade Básica de Saúde (UBS)** do seu bairro e conte "
    "o que você percebeu; ela encaminha para exames e especialistas pelo SUS. Se houver sangramento intenso, "
    "dor forte ou você estiver passando mal, vá a uma UPA ou ligue **192**.\n\n"
    "Na página **Apoio à mulher** está o caminho do cuidado (exames, rede oncológica, direitos). "
    "Em **Onde ser atendida**, as unidades da sua cidade.")

TEXTO_CAUSA = (
    "Boa pergunta, e preciso ser honesta: **o Escudo mostra o que aconteceu nas internações, mas não explica por quê.** "
    "Os dados do SIH/SUS não trazem a causa de um aumento, de uma queda ou de uma diferença. Uma mudança assim pode ter "
    "várias origens (mais doença, mais diagnóstico, mudança no registro, acesso ao hospital, ou o simples acaso quando os "
    "números são pequenos) e **os dados não permitem separar uma da outra**.\n\n"
    "O que eu consigo fazer é mostrar **quando** a mudança aconteceu, se foi um **ano fora do padrão**, se os **dados estão "
    "completos** e se o **Estado inteiro** mudou junto. Descobrir a causa pede outros dados e a análise de especialistas.")

SEM_DADOS = (
    "Essa informação **eu não tenho**. O Escudo trabalha só com **internações hospitalares do SIH/SUS**: número de internações, "
    "óbitos durante a internação, dias de leito, valor hospitalar registrado, idade, e o município onde a mulher mora e onde foi "
    "internada. Quem se trata só em ambulatório ou por plano de saúde não aparece.\n\n"
    "Não há nesta base cor ou raça, renda, escolaridade, estadiamento, sobrevida, doenças associadas nem a população de cada cidade. "
    "Prefiro dizer isso a responder com um palpite.")

LINK_APOIO = ("🩷 Abrir Apoio à mulher", "pages/apoio.py")
LINK_ONDE = ("📍 Abrir Onde ser atendida", "pages/onde_ser_atendida.py")

EXEMPLOS = [
    ("Qual câncer mais interna?", "mais_aparece"),
    ("Está aumentando?", "evolucao"),
    ("O que a tendência aponta para os próximos anos?", "futuro"),
    ("Onde podemos ter problema?", "atencao"),
]


def acao(intencao, cancer=None, pergunta=None, ano=None):
    """Ação de botão da caixa: refaz a resposta sem entender de novo."""
    return {"tipo": "assistente", "intencao": intencao, "cancer": cancer, "pergunta": pergunta, "ano": ano}


def _fonte(ctx, intencao):
    """Fonte e limite principal, só com o que o sistema sabe de verdade (sem data de atualização inventada)."""
    escopo = f"internações de mulheres residentes em {ctx.cidade}"
    if intencao in ("estado", "fluxo"):
        escopo += " e do Estado de SP"
    return (f"Fonte: SIH/SUS (DATASUS), {escopo}, {int(ctx.serie['ano'].min())}–{int(ctx.serie['ano'].max())}. "
            "Internação não é caso novo e não é incidência.")


def _inicio():
    return ("Começar de novo", INICIO)


def _cancer_texto(codigo):
    return nome_doenca(codigo).lower()


# ---------- respostas montadas aqui ----------

def _canceres(ctx):
    return list(resumo_doencas(ctx.serie)["tipo_cancer"])


def _futuro_cancer(ctx, c, ano=None):
    dados = serie_doenca(ctx.serie, c)
    prev = prever_com_validacao(dados)
    if prev is None:
        return Resposta(
            fala=(f"Para o {cancer_de(c)} tenho poucos anos de dados em {ctx.cidade}: não dá para testar um modelo "
                  f"de previsão com honestidade. Prefiro não projetar."),
            expressao="cautelosa", botoes=[("Evolução", sobre(c, "evolucao"))], destino={"aba": "Evolução", "cancer": c})
    frases = leitura_previsao(prev, c)
    p = prev["previsao"]
    if ano is not None:
        if ano <= prev["ano_fim"]:
            frases.insert(0, f"{ano} já passou nos dados: o que foi registrado está na Evolução.")
        elif ano in set(p["ano"]):
            linha = p[p["ano"] == ano].iloc[0]
            frases.insert(0, f"Para {ano}, a tendência aponta cerca de {formatar_numero(linha['internacoes'])} internações "
                             f"(faixa de {formatar_numero(linha['minimo'])} a {formatar_numero(linha['maximo'])}).")
        else:
            frases.insert(0, f"Só projeto até {int(p['ano'].max())}: mais longe que isso a incerteza passa do que os dados sustentam.")
    fala = f"**{nome_doenca(c)} em {ctx.cidade}.** " + " ".join(frases) + (
        " É uma projeção de tendência de internações, não previsão de casos novos nem de causa.")
    tabela = prev["tabela"]
    return Resposta(
        fala=fala,
        expressao="cautelosa" if prev["fragil"] else "explicando",
        botoes=[("Ver a projeção no gráfico", sobre(c, "projecao")), ("Evolução", sobre(c, "evolucao")),
                ("Onde podemos ter problema?", caminho("atencao"))],
        destino={"aba": "Evolução", "cancer": c, "camadas": {"ver_projecao": True}},
        numeros=[f"{r['descricao']}: erro médio de {formatar_numero(r['mae'], 1)} internações por ano nos testes"
                 + (" (escolhido)" if r["modelo"] == prev["modelo"] else "") for _, r in tabela.iterrows()]
                + [f"{int(l['ano'])}: {formatar_numero(l['internacoes'])} (faixa {formatar_numero(l['minimo'])} a "
                   f"{formatar_numero(l['maximo'])})" for _, l in p.iterrows()],
    )


def _futuro_todos(ctx, ano=None):
    itens = previsao_todos(ctx.serie)
    if not itens:
        return Resposta(fala="Não tenho anos suficientes para testar modelos de previsão.", expressao="cautelosa",
                        destino={"aba": "Evolução"})
    ano_alvo = int(itens[0]["previsao"]["ano"].iloc[-1])
    fortes = [i for i in itens if not i["fragil"]]
    topo = itens[0]
    fala = (f"Testei {len(MODELOS_PREVISAO)} modelos simples em cada câncer, prevendo anos que já conheço, e usei o que errou menos. "
            f"Se o comportamento passado continuar, a tendência aponta para {ano_alvo}: "
            + "; ".join(f"**{i['doenca']}** {'+' if _variacao_pct(i) >= 0 else '-'}{formatar_numero(abs(_variacao_pct(i)))}% "
                        f"(cerca de {formatar_numero(i['previsao']['internacoes'].iloc[-1])} internações)"
                        for i in itens[:3])
            + f". {len(itens) - len(fortes)} dos {len(itens)} cânceres têm previsão frágil (poucas internações, ou o modelo "
              f"não ganhou de repetir o último ano). Escolha um câncer para ver o detalhe.")
    if ano is not None and ano > ano_alvo:
        fala = f"Só projeto até {ano_alvo}. " + fala
    return Resposta(
        fala=fala, expressao="cautelosa" if len(fortes) < len(itens) else "explicando",
        botoes=[(nome_doenca(i["tipo_cancer"]), acao("futuro", i["tipo_cancer"])) for i in itens[:4]]
               + [("Onde podemos ter problema?", caminho("atencao"))],
        destino={"aba": "Planejamento", "cancer": topo["tipo_cancer"]},
        numeros=[f"{i['doenca']}: {formatar_numero(i['atual'])} em {i['ano_fim']} -> cerca de "
                 f"{formatar_numero(i['previsao']['internacoes'].iloc[-1])} em {ano_alvo} ({i['descricao']}"
                 f"{'; frágil' if i['fragil'] else ''})" for i in itens],
    )


def _obitos_todos(ctx):
    r = resumo_doencas(ctx.serie)
    r = r.assign(letalidade=r["obitos"] / r["internacoes"] * 100).sort_values("letalidade", ascending=False)
    topo = r.iloc[0]
    fala = (f"Entre os cânceres que acompanho, a maior letalidade hospitalar em {ctx.cidade} é a do "
            f"**{cancer_de(topo['tipo_cancer'])}**: {formatar_numero(topo['obitos'])} óbitos em "
            f"{formatar_numero(topo['internacoes'])} internações ({formatar_numero(topo['letalidade'], 1)}%).")
    if topo["obitos"] < 10:
        fala += " São poucos óbitos, então a comparação é frágil."
    fala += " Isso mede óbitos durante a internação, não a mortalidade da doença na população."
    return Resposta(
        fala=fala, expressao="cautelosa" if topo["obitos"] < 10 else "atenta",
        botoes=[(nome_doenca(c), sobre(c, "obitos")) for c in r["tipo_cancer"].head(3)],
        destino={"aba": "Panorama", "cancer": topo["tipo_cancer"], "medida": "Óbitos na internação"},
        numeros=[f"{l['doenca']}: {formatar_numero(l['obitos'])} óbitos em {formatar_numero(l['internacoes'])} "
                 f"internações ({formatar_numero(l['letalidade'], 1)}%)" for _, l in r.iterrows()])


def _tempo_todos(ctx):
    r = resumo_doencas(ctx.serie)
    r = r.assign(media=r["dias_permanencia"] / r["internacoes"]).sort_values("media", ascending=False)
    topo = r.iloc[0]
    fala = (f"Em {ctx.cidade}, a internação mais longa em média é a do **{cancer_de(topo['tipo_cancer'])}**: "
            f"{formatar_numero(topo['media'], 1)} dias por internação. O que menos ocupa leito é o "
            f"{cancer_de(r.iloc[-1]['tipo_cancer'])}, com {formatar_numero(r.iloc[-1]['media'], 1)} dias.")
    return Resposta(
        fala=fala, expressao="explicando",
        botoes=[(nome_doenca(c), sobre(c, "tempo")) for c in r["tipo_cancer"].head(3)],
        destino={"aba": "Panorama", "cancer": topo["tipo_cancer"], "medida": "Dias de internação"},
        numeros=[f"{l['doenca']}: {formatar_numero(l['dias_permanencia'])} dias em {formatar_numero(l['internacoes'])} "
                 f"internações ({formatar_numero(l['media'], 1)} dias cada)" for _, l in r.iterrows()])


def _sobre_ia(ctx, ia):
    ligada = ("Neste momento a IA de linguagem (Gemini) está **ligada**." if ia.ligada else
              "Neste momento a IA de linguagem (Gemini) está **desligada** (sem chave): respondo direto dos cálculos.")
    fala = (
        "Sou a **Lia**, uma guia do Escudo Feminino, não uma pessoa. Por trás de mim há três partes de IA, "
        "cada uma com um papel limitado:\n\n"
        f"1. **Entender a pergunta:** busca por palavras e por trechos de letras num vocabulário de {len(ent.INTENCOES)} assuntos que o Escudo "
        "sabe responder. Quando fico em dúvida, o Gemini escolhe um assunto da lista, nunca inventa outro.\n"
        f"2. **Prever:** para cada câncer, testo {len(MODELOS_PREVISAO)} modelos simples em anos que já conheço e uso o que errou menos, "
        "comparando sempre com 'repetir o último ano'. Os dados são poucos: é projeção de tendência, não previsão clínica.\n"
        "3. **Redigir:** o Gemini reescreve a resposta, mas os números vêm do banco e eu confiro o texto dele: se aparecer "
        "número novo, promessa ou explicação de causa, descarto e mostro a resposta direta.\n\n"
        + ligada + " Eu não faço diagnóstico e não digo causas.")
    return Resposta(fala=fala, expressao="pensativa",
                    botoes=[("Como esses dados funcionam?", caminho("metodo")), ("O que a tendência aponta?", acao("futuro"))],
                    destino={"aba": "Método"})


def _ajuda(ctx, ia):
    fala = (f"Pergunte do seu jeito. Com os números de **{ctx.cidade}**, sei responder: quais cânceres mais internam, "
            "se estão aumentando, o que a tendência aponta para os próximos anos, óbitos na internação, valores "
            "hospitalares registrados, tempo de internação, idade, comparação com o Estado, anos fora do padrão, "
            "mulheres de outros estados, se os dados estão completos e como tudo é calculado. Também encaminho para "
            "**Apoio à mulher** e **Onde ser atendida**. Não faço diagnóstico.")
    return Resposta(fala=fala, expressao="acolhedora", botoes=[(r, acao(i, pergunta=r)) for r, i in EXEMPLOS])


def _comparar_cidades(ctx):
    fala = (f"Na aba **Investigar**, mais abaixo, você compara {ctx.cidade} com outra cidade (sugiro a de número de "
            "internações mais parecido). Como ainda não tenho a população de cada cidade, comparo o que não depende do "
            "tamanho: a parcela de cada câncer, a letalidade hospitalar, a permanência média e o ritmo de crescimento.")
    return Resposta(fala=fala, expressao="explicando", destino={"aba": "Investigar"},
                    botoes=[("Comparar com São Paulo", caminho("estado")), ("Os dados estão completos?", caminho("completude"))])


def _fato_do_ano(ctx, c, ano):
    """Frase com o número de um ano passado (pergunta tipo "quantas em 2020?"). Usa o REGISTRADO,
    e avisa se a fonte não tem os 12 meses desse ano."""
    dados = serie_doenca(ctx.serie, c)
    linha = dados[dados["ano"] == ano]
    if linha.empty:
        return (f"Não tenho dados de {ano} para o {cancer_de(c)}: vão de {int(dados['ano'].min())} a "
                f"{int(dados['ano'].max())}.")
    linha = linha.iloc[0]
    registrado = linha["internacoes_reg"] if "internacoes_reg" in dados else linha["internacoes"]
    frase = f"Em {ano}, foram registradas {formatar_numero(registrado)} internações por {cancer_de(c)} em {ctx.cidade}"
    meses = anos_incompletos(ctx.serie).get(ano)
    if meses:
        frase += (f"; a fonte só tem {meses} de 12 meses desse ano, e a estimativa para o ano inteiro é "
                  f"{formatar_numero(linha['internacoes'])}")
    return frase + "."


# ---------- decisão: qual resposta da Lia (ou daqui) serve a cada intenção ----------

POR_CANCER = {"idade"}                      # sem câncer citado, usam o câncer em foco no painel
USAM_CANCER_SE_CITADO = {"evolucao", "obitos", "valores", "tempo", "estado", "futuro", "idade"}
SO_DADOS = {"mais_aparece", "evolucao", "futuro", "obitos", "valores", "tempo", "idade", "estado", "atencao",
            "fora_padrao", "fluxo", "completude", "metodo"}   # as únicas que a IA pode reescrever


def _resposta_base(ctx, intencao, cancer, foco, ano, ia):
    """(Resposta, câncer usado, nota). `foco`: o câncer em foco no painel."""
    nota = None
    c = cancer if intencao in USAM_CANCER_SE_CITADO else None
    if c is None and intencao in POR_CANCER:
        c = foco
        nota = f"Considerando o câncer em foco no painel: {_cancer_texto(foco)}. Se quiser outro, é só dizer qual."
    if c is not None and c not in _canceres(ctx):
        return (Resposta(fala=f"Não encontro internações por {cancer_de(c)} em {ctx.cidade} no banco. Posso olhar os outros cânceres?",
                         expressao="cautelosa", botoes=[(nome_doenca(x), sobre(x, "menu")) for x in _canceres(ctx)[:4]]), None, None)

    if intencao == "mais_aparece":
        return lia_responder(ctx, caminho("mais_aparece")), None, nota
    if intencao == "evolucao":
        resposta = lia_responder(ctx, sobre(c, "evolucao")) if c else lia_responder(ctx, caminho("aumentando"))
        if c and ano is not None and ano <= int(ctx.serie["ano"].max()):
            resposta.fala = _fato_do_ano(ctx, c, ano) + "\n\n" + resposta.fala
        return resposta, c, nota
    if intencao == "futuro":
        return (_futuro_cancer(ctx, c, ano) if c else _futuro_todos(ctx, ano)), c, nota
    if intencao == "obitos":
        return (lia_responder(ctx, sobre(c, "obitos")) if c else _obitos_todos(ctx)), c, nota
    if intencao == "valores":
        return (lia_responder(ctx, sobre(c, "valores")) if c else lia_responder(ctx, caminho("valores"))), c, nota
    if intencao == "tempo":
        return (lia_responder(ctx, sobre(c, "tempo")) if c else _tempo_todos(ctx)), c, nota
    if intencao == "idade":
        return lia_responder(ctx, sobre(c, "idade")), c, nota
    if intencao == "estado":
        return (lia_responder(ctx, sobre(c, "estado")) if c else lia_responder(ctx, caminho("estado"))), c, nota
    if intencao in ("atencao", "fora_padrao", "fluxo", "completude", "metodo"):
        return lia_responder(ctx, caminho(intencao)), None, nota
    if intencao == "causa":
        return Resposta(fala=TEXTO_CAUSA, expressao="pensativa", destino={"aba": "Método"},
                        botoes=[("Anos fora do padrão", caminho("fora_padrao")), ("Comparar com São Paulo", caminho("estado")),
                                ("Os dados estão completos?", caminho("completude"))]), None, nota
    if intencao == "sem_dados":
        return Resposta(fala=SEM_DADOS, expressao="cautelosa", destino={"aba": "Método"},
                        botoes=[("Como esses dados funcionam?", caminho("metodo")), ("O que mais aparece?", caminho("mais_aparece"))]), None, nota
    if intencao == "sobre_ia":
        return _sobre_ia(ctx, ia), None, nota
    if intencao == "comparar_cidades":
        return _comparar_cidades(ctx), None, nota
    if intencao == "ajuda":
        return _ajuda(ctx, ia), None, nota
    if intencao == "sintoma":
        return Resposta(fala=SINTOMA, expressao="acolhedora", destino=None), None, nota
    if intencao == "apoio":
        return Resposta(
            fala=("O Escudo estuda dados para quem planeja e pesquisa. Para quem **procura cuidado**, a página **Apoio à mulher** "
                  "reúne o caminho: mamografia e preventivo pelo SUS, rede oncológica, regulação (\"fui encaminhada, e agora?\"), "
                  "tratamento, carretas e direitos (transporte para tratamento, FGTS, INSS, reconstrução da mama). Cada item "
                  "traz a fonte oficial e a data em que foi conferido."), expressao="acolhedora"), None, nota
    if intencao == "onde_atendida":
        return Resposta(
            fala=(f"Para saber **onde procurar atendimento** em {ctx.cidade} (postos de saúde, hospitais, UPA, exames e saúde "
                  "mental), use a página **Onde ser atendida**: tem endereço, telefone e como chegar. É um cadastro oficial (CNES): "
                  "não garante vaga nem que o serviço esteja aberto naquele momento."), expressao="acolhedora"), None, nota
    return lia_responder(ctx, INICIO), None, nota


LINKS = {"apoio": [LINK_APOIO], "sintoma": [LINK_APOIO, LINK_ONDE], "onde_atendida": [LINK_ONDE, LINK_APOIO]}


def _tornar(r, **extra):
    """Resposta da Lia -> RespostaIA, sem perder nada."""
    dados = {"fala": r.fala, "expressao": r.expressao, "botoes": list(r.botoes), "destino": r.destino,
             "numeros": list(r.numeros)}
    dados.update(extra)
    return RespostaIA(**dados)


def _finalizar(resp):
    if not any(a.get("tipo") == "inicio" for _, a in resp.botoes):
        resp.botoes = resp.botoes + [_inicio()]
    return resp


def _redigir(resp, pergunta, ia, perfil):
    """Pede ao Gemini a redação e confere. Altera `resp` no lugar."""
    if not (ia and ia.explicar):
        resp.selo = "Resposta direta dos cálculos do Escudo (sem IA)."
        resp.ia_motivo = "IA desligada"
        return
    base = resp.fala + (("\n" + "\n".join(f"- {n}" for n in resp.numeros)) if resp.numeros else "")
    try:
        texto = ia.explicar(pergunta, base, perfil)
    except Exception as erro:
        resp.selo = "A IA não respondeu agora; esta é a resposta direta dos cálculos do Escudo."
        resp.ia_motivo = f"erro da IA: {type(erro).__name__}"
        return
    motivo = conferir(texto, base, pergunta)
    if motivo:
        resp.selo = "Resposta direta dos cálculos do Escudo (o texto da IA não passou na conferência)."
        resp.ia_motivo = motivo
        return
    resp.base = resp.fala
    resp.fala = texto.strip()
    resp.usou_ia = True
    resp.selo = "🤖 Redigido pela IA (Gemini) a partir de números calculados pelo Escudo."


def montar(ctx, e, pergunta, foco, perfil="TECNICO", ia=None):
    """Resposta para um Entendimento já feito."""
    ia = ia or IA()
    comum = dict(pergunta=pergunta, tipo=e.tipo, origem=e.origem)

    if e.tipo == "risco":
        return _finalizar(RespostaIA(fala=SEGURANCA[e.risco], expressao="acolhedora", links=[LINK_APOIO], **comum))
    if e.tipo == "saudacao":
        return _finalizar(_tornar(lia_responder(ctx, INICIO), **comum))
    if e.tipo == "vazio":
        return _finalizar(_tornar(_ajuda(ctx, ia), **comum))
    if e.tipo == "palpites":
        botoes = [(ent.ROTULOS[i], acao(i, e.cancer, pergunta, e.ano)) for i, _ in e.palpites]
        return _finalizar(RespostaIA(
            fala="Não tenho certeza do que você quis saber. Foi alguma destas?", expressao="pensativa", botoes=botoes,
            selo="Se nenhuma servir, escreva de outro jeito ou use os botões da Lia.", **comum))
    if e.tipo == "fora":
        if e.nao_acompanhado:
            disponiveis = _canceres(ctx)
            fala = (f"Ainda não acompanho o câncer de {e.nao_acompanhado}. Acompanho "
                    + ", ".join(_cancer_texto(c) for c in disponiveis) + ". Quer olhar algum deles?")
            return _finalizar(RespostaIA(fala=fala, expressao="cautelosa",
                                         botoes=[(nome_doenca(c), sobre(c, "menu")) for c in disponiveis[:5]], **comum))
        return _finalizar(RespostaIA(
            fala=(f"Essa pergunta foge do que sei responder: falo dos dados de câncer feminino em {ctx.cidade} e do caminho "
                  "para encontrar cuidado. Tente, por exemplo:"),
            expressao="acolhedora", botoes=[(r, acao(i, pergunta=r)) for r, i in EXEMPLOS], **comum))

    # intenção entendida
    pedido, nota_foco = e.cancer, None
    if e.foco and not pedido and not e.varios_canceres:  # "esse câncer": o que está em foco no painel
        pedido, nota_foco = foco, f"Considerando o câncer em foco no painel: {_cancer_texto(foco)}."
    intencao = e.intencao
    if intencao == "mais_aparece" and pedido and e.ano is not None and e.ano <= int(ctx.serie["ano"].max()):
        intencao = "evolucao"  # "quantas internações de mama em 2020?" é sobre aquele câncer e aquele ano
    base, usado, nota = _resposta_base(ctx, intencao, pedido, foco, e.ano, ia)
    nota = nota or (nota_foco if usado else None)
    if e.nao_acompanhado:
        nota = (f"Ainda não acompanho o câncer de {e.nao_acompanhado}; mostro os que acompanho. " + (nota or "")).strip()
    resp = _tornar(base, intencao=intencao, cancer=usado, links=list(LINKS.get(intencao, [])), **comum)
    if intencao in SO_DADOS and base.fala:
        resp.fonte = _fonte(ctx, intencao)
        _redigir(resp, pergunta, ia, perfil)
        if nota:
            resp.fala = nota + "\n\n" + resp.fala
    else:
        if nota:
            resp.fala = nota + "\n\n" + resp.fala
        resp.selo = "Texto fixo do Escudo (a IA não improvisa neste assunto)." if intencao in (
            "sintoma", "apoio", "onde_atendida", "ajuda", "sobre_ia", "comparar_cidades", "causa", "sem_dados") else None
    return _finalizar(resp)


def responder_pergunta(ctx, pergunta, foco, memoria=None, perfil="TECNICO", ia=None, outras_cidades=()):
    """Entende e responde a pergunta escrita. `foco`: o câncer em foco no painel. `memoria`:
    {"intencao","cancer"} da resposta anterior (para 'e de mama?')."""
    ia = ia or IA()
    e = ent.compreender(pergunta, set(_canceres(ctx)), memoria=memoria,
                        classificar=ia.classificar if ia.ligada else None,
                        cidade=ctx.cidade, outras_cidades=outras_cidades, ano_dados=int(ctx.serie["ano"].max()))
    return montar(ctx, e, pergunta, foco, perfil, ia)


def responder_escolha(ctx, a, foco, perfil="TECNICO", ia=None):
    """Botão de palpite ou de exemplo: a pessoa já escolheu o assunto."""
    ia = ia or IA()
    pergunta = a.get("pergunta") or ent.ROTULOS.get(a["intencao"], "")
    e = ent.Entendimento("intencao", intencao=a["intencao"], cancer=a.get("cancer"), ano=a.get("ano"), origem="escolha",
                         cancer_citado=bool(a.get("cancer")))
    return montar(ctx, e, pergunta, foco, perfil, ia)
