import re
from decimal import Decimal
from dataclasses import dataclass, field, replace

import entendimento as ent
import localizacao
from inteligencia import (
    MODELOS_PREVISAO,
    anos_incompletos,
    cancer_de,
    formatar_numero,
    leitura_ranking,
    nome_doenca,
    prever_com_validacao,
    previsao_todos,
    leitura_previsao,
    resumo_doencas,
    serie_doenca,
    _variacao_pct,
)
from lia import INICIO, Resposta, caminho, responder as lia_responder, sobre, tratamento as lia_tratamento, mortalidade_real as lia_mortalidade, polos as lia_polos

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

def _leituras(numero):
    """Valores que um número escrito em português pode ter, como texto canônico ("5,3" -> {"5.3"}).

    "5,3" é decimal e "1.234.567" é milhar; "1.668" ou "1,668" é ambíguo e vale pelas duas leituras
    ({"1668", "1.668"}). A primeira leitura da lista é a que aparece na mensagem de erro."""
    def canon(texto):
        return format(Decimal(texto).normalize(), "f")

    separadores = re.findall(r"[.,]", numero)
    if not separadores:
        return [canon(numero)]
    ultimo = max(numero.rfind("."), numero.rfind(","))
    cauda = numero[ultimo + 1:]
    if len(set(separadores)) == 2:        # "1.668,5": o último separador é o decimal, o outro é milhar
        return [canon(re.sub(r"[.,]", "", numero[:ultimo]) + "." + cauda)]
    if len(separadores) > 1:              # "1.234.567": só pode ser milhar
        return [canon(re.sub(r"[.,]", "", numero))]
    inteira = numero[:ultimo]
    decimal = canon(inteira + "." + cauda)
    if len(cauda) == 3:                   # "1.668" pode ser milhar ou decimal: vale pelas duas
        return [canon(inteira + cauda), decimal]
    return [decimal]


def _numeros(texto):
    """Um item por número do texto, com as leituras possíveis dele; ignora número de 1 dígito."""
    achados = re.findall(r"\d+(?:[.,]\d+)*", texto)
    return [_leituras(n) for n in achados if len(re.sub(r"[.,]", "", n)) >= 2]


def numeros_novos(texto_ia, *fontes):
    """Números do texto da IA que não aparecem em nenhuma das fontes (base, pergunta).

    Compara o valor, não os dígitos: "5,3" não é "53", e "1.668" é "1668"."""
    permitidos = set()
    for fonte in fontes:
        for leituras in _numeros(fonte):
            permitidos.update(leituras)
    novos = {leituras[0] for leituras in _numeros(texto_ia) if not permitidos.intersection(leituras)}
    return sorted(novos)


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
    "Não há nas internações cor ou raça, renda, escolaridade, estadiamento, sobrevida nem doenças associadas. Cor ou raça e "
    "estadiamento aparecem só no tratamento ambulatorial (quimio e radioterapia, SIA), quando essa base está carregada: pergunte "
    "\"quantas mulheres fazem quimioterapia\". Prefiro dizer isso a responder com um palpite.")

# "Me explica isso melhor": o que cada assunto de dados significa, em palavras simples. Texto fixo (sem números e sem causa):
# os números vêm dos cálculos, e a IA não improvisa aqui.
EXPLICACAO_SIMPLES = {
    "mais_aparece": "Aqui eu conto, para cada tipo de câncer, quantas vezes mulheres foram internadas no hospital pelo SUS. O tipo com "
                    "mais internações é o que mais ocupa os hospitais, e isso não quer dizer que seja o mais comum na população.",
    "evolucao": "Comparo o número de internações ano a ano. Se a linha sobe, houve mais internações a cada ano; se desce, menos. "
                "É o que os registros mostram, sem dizer o motivo.",
    "futuro": "É uma projeção de tendência: o Escudo continua a linha dos anos anteriores para os próximos anos e mostra uma faixa de "
              "erro. Não é uma previsão exata, e quanto mais longe no tempo, menos firme ela fica.",
    "obitos": "São mulheres que morreram durante a internação no hospital. Não inclui quem morreu em casa ou depois da alta, e não "
              "mede a gravidade da doença na população.",
    "valores": "É o valor que o SUS registrou para pagar as internações. Não é o orçamento da cidade nem o custo total do tratamento, "
               "que também tem exames e remédios fora do hospital.",
    "tempo": "É o tempo, em dias, que a mulher fica no hospital em cada internação, em média. Dias a mais ou a menos dependem de "
             "muitos fatores que estes dados não mostram.",
    "idade": "Mostro em que faixa de idade estão as mulheres internadas. Isso descreve quem foi internada, e não quem tem mais "
             "risco de adoecer.",
    "estado": "Coloco a cidade ao lado do Estado de São Paulo para ver se o ritmo é parecido. Como as cidades têm tamanhos "
              "diferentes, comparo a variação, não os números brutos.",
    "atencao": "É uma lista do que merece olhar com mais atenção no planejamento, com os sinais que levaram a isso. Quem decide o que "
               "fazer é a gestão, e o Escudo não calcula quanto investir.",
    "fora_padrao": "Um ano fora do padrão é um ano em que o número ficou muito diferente do que a tendência esperava. Os dados mostram "
                   "que foi diferente, e não dizem por quê.",
    "fluxo": "Mostro de onde vêm as mulheres internadas em hospitais de São Paulo, inclusive de outros estados, e para onde vão as "
             "moradoras da cidade. Conto internações, não pessoas.",
    "completude": "O SUS não divulga todos os meses de todos os anos. Quando faltam meses, o Escudo estima o ano inteiro pela média "
                  "dos meses que existem e avisa onde a estimativa é menos firme.",
    "metodo": "Os dados vêm do SIH/SUS, o sistema que registra as internações pagas pelo SUS. Cada registro é uma internação, não um "
              "caso novo de câncer. O Escudo calcula os números, e a IA, quando está ligada, só ajuda na redação.",
}
COMO_LER = ("Para ler os números: cada um conta **internações** registradas no SUS (uma mulher pode ter mais de uma), não casos novos "
            "de câncer. O Escudo mostra o que aconteceu, não explica o porquê.")

# Pedido de ranking ou proporção entre cidades: a recusa diz exatamente o que falta (a população) e o que dá para ver hoje.
SEM_POPULACAO = (
    "Para dizer quais cidades têm mais casos **proporcionalmente**, eu precisaria da **população de cada cidade**, e ela ainda não "
    "está no Escudo (é uma das próximas etapas, com dados do IBGE). Sem ela, contar internações favorece as cidades grandes e não "
    "diz nada sobre o risco de cada mulher.\n\n"
    "O que consigo mostrar hoje, sem depender do tamanho da cidade: a **parcela de cada câncer**, a **letalidade hospitalar**, o "
    "**tempo médio de internação** e o **ritmo de crescimento**, comparando a sua cidade com outra.")
PEDE_PROPORCAO = re.compile(r"proporcion|por habitante|per capita|ranking|em relacao a populacao|numero de habitantes|cidades que mais")

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
USAM_CANCER_SE_CITADO = {"evolucao", "obitos", "valores", "tempo", "estado", "futuro", "idade", "tratamento", "mortalidade_real", "polos"}
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
    if intencao == "polos":
        return lia_polos(ctx, c), c, nota
    if intencao == "tratamento":
        return lia_tratamento(ctx, c), c, nota
    if intencao == "mortalidade_real":
        return lia_mortalidade(ctx, c), c, nota
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
                  "tratamento, carretas, hospitais de câncer pelo SUS (lâmina **Hospitais no Estado**) e direitos (transporte para "
                  "tratamento, FGTS, INSS, reconstrução da mama). Cada item traz a fonte oficial e a data em que foi conferido."),
            expressao="acolhedora"), None, nota
    if intencao == "onde_atendida":
        return Resposta(
            fala=(f"Para saber **onde procurar atendimento** em {ctx.cidade} (postos de saúde, hospitais, UPA, exames e saúde "
                  "mental), use a página **Onde ser atendida**: tem endereço, telefone e como chegar. É um cadastro oficial (CNES): "
                  "não garante vaga nem que o serviço esteja aberto naquele momento. Para **hospital especializado em câncer** (os de "
                  "referência da região), veja na página **Apoio à mulher** a lâmina **Hospitais no Estado**."), expressao="acolhedora"), None, nota
    return lia_responder(ctx, INICIO), None, nota


# "Preciso de um hospital que atenda câncer de ovário, moro em Catanduva": hospital de câncer pelo SUS não se escolhe por proximidade
# nem pela cidade do painel (Rio Claro é o centro do trabalho, mas os hospitais ficam fora); a paciente é encaminhada ao serviço de
# referência da REGIÃO onde mora. O Escudo não tem a lista de qual região atende cada cidade e prefere não chutar: mostra os
# hospitais do catálogo que citam a cidade e, sem eles, aponta a lâmina Hospitais no Estado e como descobrir a região.
PEDE_HOSPITAL_CANCER = re.compile(r"(hosp\w*|ospital|unacon|cacon|centro de oncologia|oncologista|onde (tratar|se tratar|fazer quimio|fazer radio)).*"
                                  r"(cancer|oncolog|tumor|quimio|radio|mama|ovario|colo do utero|utero|pulmao|intestino|colorretal|endometrio)"
                                  r"|(cancer|oncolog|tumor|quimio|radio|mama|ovario|utero|pulmao|intestino|colorretal|endometrio).*"
                                  r"(hosp\w*|ospital|unacon|cacon|centro de oncologia)")
PEDE_TRATAR = re.compile(r"\bonde\b.*\b(me trato|me tratar|tratar|tratamento|me trata|fazer tratamento|faco tratamento|pra onde eu vou|para onde eu vou)\b"
                         r"|\b(pra|para) onde eu (vou|devo ir)\b")
CITA_CANCER = re.compile(r"cancer|oncolog|tumor|ovario|mama|colo do utero|utero|pulmao|intestino|colorretal|endometrio|diagnostic\w+")
PEDE_MELHOR = re.compile(r"\b(melhor|melhores|mais top|top|mais bom|mais conceituado|mais bem avaliado|qual cidade (que )?tem o)\b")
_PARADA = (r"(?= (?:e|mas|que|com|preciso|quero|gostaria|onde|tem|qual|quais|como|me|pode|trata|atende|faz|fica|pelo|pra|para|"
           r"gratis|sus|eu|existe|queria|vou|devo)\b|$)")
_NOME = r"([a-z]+(?: (?:de|do|da|dos|das|[a-z]+)){0,5}?)"
CIDADE_CITADA = [re.compile(p + _NOME + _PARADA) for p in (
    r"\b(?:moro|moramos|resido|vivo|sou)\s+(?:em|no|na|de|do|da)\s+",
    r"\b(?:perto|proximo|proxima|nas proximidades)\s+(?:de|do|da)\s+",
    r"\b(?:na cidade de|no municipio de)\s+")]


def cidade_citada(pergunta):
    """A cidade que a pessoa diz morar ou procurar ('moro em Catanduva'), normalizada; None se não citou."""
    texto = ent.normalizar(pergunta)
    for padrao in CIDADE_CITADA:
        achado = padrao.search(texto)
        if achado:
            return achado.group(1).strip()
    return None


def _hospital_de_cancer(ctx, pergunta):
    """Resposta de texto fixo para 'hospital que atenda câncer', respeitando a cidade que a pessoa citou. None se não for esse pedido."""
    import apoio
    norm = ent.normalizar(pergunta)
    if not (PEDE_HOSPITAL_CANCER.search(norm) or (PEDE_TRATAR.search(norm) and CITA_CANCER.search(norm))):
        return None
    citada = cidade_citada(pergunta)
    do_painel = ent.normalizar(ctx.cidade)
    outra = citada if citada and citada != do_painel else None
    hospitais = [i for i in apoio.ITENS if i["lamina"] == "hospitais" or i["id"] in localizacao.IDS_EXTRAS]
    if outra:
        da_cidade = sorted((i for i in hospitais if outra in ent.normalizar(f"{i['onde']} {i['titulo']} {i['grupo'] or ''}")),
                           key=lambda i: outra not in ent.normalizar(i["onde"]))[:3]
        nome = outra.title()
    elif PEDE_MELHOR.search(norm):
        da_cidade, nome = [], None  # "qual o melhor hospital": não ranqueia, então não apresenta o da cidade do painel como resposta
    elif do_painel == "rio claro":
        da_cidade = [i for i in apoio.ITENS if i["lamina"] == "rio_claro" and "oncolog" in ent.normalizar(i["titulo"])][:2]
        nome = ctx.cidade
    else:
        da_cidade, nome = [], None
    proximos = localizacao.hospitais_proximos(getattr(ctx, "localizacao", None), outra, hospitais) if outra else []
    if da_cidade and any(localizacao.cidade_do_item(i["onde"]) == outra for i in da_cidade):
        proximos = []  # a cidade tem hospital no catálogo: a lista dela já responde
    if proximos:
        km = "\n".join(f"- **{i['titulo']}** ({i['onde']}): cerca de **{int(round(d, -1)) if d >= 20 else int(round(d))} km** em linha reta"
                       for d, i in proximos)
        fala = (f"Não há hospital de câncer do catálogo em **{nome}**. Os mais próximos, em **linha reta entre os centros das cidades** "
                f"(não é a rota nem o tempo de viagem):\n\n{km}\n\n")
    elif da_cidade:
        linhas = "\n".join(f"- **{i['titulo']}** ({i['onde']}; {i['grupo'] or 'região'}): {i['como'] or i['resumo']}" for i in da_cidade)
        fala = (f"Hospitais do catálogo do Escudo ligados a **{nome}**:\n\n{linhas}\n\n")
    else:
        onde = f" para quem mora em **{nome}**" if nome else ""
        fala = (f"Não tenho no catálogo um hospital de câncer{onde} que eu possa indicar com segurança. Prefiro não chutar.\n\n")
    if PEDE_MELHOR.search(norm):
        fala = ("O Escudo **não classifica hospitais** nem diz qual é o melhor: os dados que tenho contam internações, não qualidade. "
                "Pelo SUS, a escolha também não é da paciente: ela segue o encaminhamento.\n\n") + fala
    fala += ("**Como funciona pelo SUS:** hospital de câncer não se escolhe por proximidade. A paciente é encaminhada, pela unidade de "
             "saúde e pela regulação (CROSS), ao serviço de referência da **região** onde mora. Na página **Apoio à mulher**, a lâmina "
             "**Hospitais no Estado** reúne 23 hospitais por região, com a fonte oficial e como chegar pela CROSS. Se não achar a "
             "sua cidade, pergunte na unidade de saúde ou na Secretaria de Saúde a qual região (DRS) ela pertence: o Escudo ainda não "
             "tem essa lista por cidade.")
    return Resposta(fala=fala, expressao="acolhedora")


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

    # pedido composto: responde os dois assuntos, um depois do outro, sem descartar nenhum
    if e.tambem:
        ra = montar(ctx, replace(e, tambem=None, origem="regras"), pergunta, foco, perfil, ia)
        rb = montar(ctx, replace(e, intencao=e.tambem, tambem=None, origem="regras"), pergunta, foco, perfil, ia)
        resp = ra
        resp.fala = (f"Você fez dois pedidos, e respondo os dois.\n\n**{ent.ROTULOS_TODOS[ra.intencao]}**\n\n{ra.fala}"
                     f"\n\n**{ent.ROTULOS_TODOS[rb.intencao]}**\n\n{rb.fala}")
        resp.links = list(dict.fromkeys(list(ra.links) + list(rb.links)))
        ja = {r for r, _ in resp.botoes}
        resp.botoes = resp.botoes + [(r, a) for r, a in rb.botoes if r not in ja and a.get("tipo") != "inicio"]
        resp.usou_ia = ra.usou_ia or rb.usou_ia
        resp.origem = "composta"
        resp.selo = "Respondi os dois pedidos da sua pergunta, um depois do outro. Os números vêm dos cálculos do Escudo."
        return resp

    # intenção entendida
    pedido, nota_foco = e.cancer, None
    if e.foco and not pedido and not e.varios_canceres:  # "esse câncer": o que está em foco no painel
        pedido, nota_foco = foco, f"Considerando o câncer em foco no painel: {_cancer_texto(foco)}."
    intencao = e.intencao
    if intencao == "mais_aparece" and pedido and e.ano is not None and e.ano <= int(ctx.serie["ano"].max()):
        intencao = "evolucao"  # "quantas internações de mama em 2020?" é sobre aquele câncer e aquele ano
    base, usado, nota = _resposta_base(ctx, intencao, pedido, foco, e.ano, ia)
    if intencao == "onde_atendida":
        hospital = _hospital_de_cancer(ctx, pergunta)
        if hospital is not None:
            base = hospital
    if intencao == "sem_dados" and PEDE_PROPORCAO.search(ent.normalizar(pergunta)):
        rankings = getattr(ctx, "ranking", None) or {}
        chave = pedido if pedido in rankings else None  # o câncer citado, ou os 7 somados
        tabela = rankings.get(chave)
        botoes = [("Comparar com outra cidade", acao("comparar_cidades", None, pergunta)),
                  ("Cidades que mais tratam", caminho("polos")),
                  ("Mulheres de outros estados", caminho("fluxo")),
                  ("Como esses dados funcionam?", caminho("metodo"))]
        if tabela is not None and len(tabela):  # a população do IBGE está no banco: responde com o ranking de verdade
            base = Resposta(fala=leitura_ranking(tabela, chave, ctx.cidade, ctx.codigo_ibge), expressao="explicando",
                            destino={"aba": "Investigar"}, botoes=botoes)
            usado = chave
        else:  # sem a população: diz o que falta e o que dá para ver hoje
            base = Resposta(fala=SEM_POPULACAO, expressao="cautelosa", destino={"aba": "Investigar"}, botoes=botoes)
    nota = nota or (nota_foco if usado else None)
    if e.nao_acompanhado and intencao in SO_DADOS:  # nos textos fixos (sintoma, apoio...) o aviso só atrapalharia
        nota = (f"Ainda não acompanho o câncer de {e.nao_acompanhado}; mostro os que acompanho. " + (nota or "")).strip()
    if e.origem == "comparar_canceres":
        nota = ("Para comparar cânceres, mostro todos os que o Escudo acompanha, lado a lado. " + (nota or "")).strip()
    resp = _tornar(base, intencao=intencao, cancer=usado, links=list(LINKS.get(intencao, [])), **comum)
    if e.origem == "explicar" and intencao in EXPLICACAO_SIMPLES and base.fala:
        # "me explica isso melhor": a mesma resposta, com o que ela significa em palavras simples (texto fixo, sem a IA)
        resp.fonte = _fonte(ctx, intencao)
        numeros = ("\n" + "\n".join(f"- {n}" for n in resp.numeros)) if resp.numeros else ""
        resp.fala = ((nota + "\n\n" if nota else "") + "Vou explicar de outro jeito, com palavras simples.\n\n"
                     + EXPLICACAO_SIMPLES[intencao] + "\n\nOs números, de novo:\n\n" + base.fala + numeros + "\n\n" + COMO_LER)
        resp.selo = "Texto fixo do Escudo (a IA não improvisa na explicação simples)."
        return _finalizar(resp)
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
    norm_p = ent.normalizar(pergunta)
    pede_hospital = bool(PEDE_HOSPITAL_CANCER.search(norm_p) or (PEDE_TRATAR.search(norm_p) and CITA_CANCER.search(norm_p)))
    if pede_hospital and (e.tipo in ("palpites", "fora") or e.intencao == "apoio"
                           or (e.intencao == "comparar_cidades" and "compar" not in norm_p)):
        # pede hospital de câncer mas a busca ficou em dúvida (nome de cidade e erro de digitação atrapalham): é o assunto "onde ser atendida"
        e = ent.Entendimento("intencao", intencao="onde_atendida", origem="regras")
    return montar(ctx, e, pergunta, foco, perfil, ia)


def responder_escolha(ctx, a, foco, perfil="TECNICO", ia=None):
    """Botão de palpite ou de exemplo: a pessoa já escolheu o assunto."""
    ia = ia or IA()
    pergunta = a.get("pergunta") or ent.ROTULOS.get(a["intencao"], "")
    e = ent.Entendimento("intencao", intencao=a["intencao"], cancer=a.get("cancer"), ano=a.get("ano"), origem="escolha",
                         cancer_citado=bool(a.get("cancer")))
    return montar(ctx, e, pergunta, foco, perfil, ia)
