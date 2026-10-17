import re
import sqlite3
import unicodedata
from datetime import datetime

from inteligencia import (
    MEDIA_PEQUENA,
    ano_atipico_no_estado,
    anos_fora_do_padrao,
    comparar_com_estado,
    formatar_numero,
    leitura_evolucao,
    nome_doenca,
    projetar,
    resumo_doencas,
    ritmo_anual_pct,
    serie_doenca,
    testar_projecao,
    GRUPO_ESTADO,
)

# =====================================
# CHAT DO ESCUDO: entender -> calcular -> explicar
#
# Substitui chat_servico.py no painel. Três passos, nesta ordem:
#
#   1. ENTENDER (determinístico): qual assunto e qual câncer. O
#      assunto é escolhido por PONTUAÇÃO (quantas palavras-chave de
#      cada assunto aparecem), não pelo "primeiro bloco que der
#      match" -- era isso que fazia "mortalidade do câncer de mama"
#      virar uma ficha genérica de mama.
#   2. CALCULAR (determinístico): os fatos saem de inteligencia.py,
#      a mesma fonte dos gráficos. Chat e painel nunca discordam, e
#      nada depende das 13 tabelas antigas.
#   3. EXPLICAR: o Gemini transforma os fatos em texto (ia_linguagem.
#      responder_com_ia, com as regras de não inventar número nem
#      causa). Se ele não estiver disponível, a resposta sai direto
#      dos fatos -- o chat nunca fica mudo.
#
# O Escudo não prescreve orçamento em reais: perguntas sobre
# investimento recebem os sinais que merecem atenção, com evidência.
# =====================================


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).upper()
    return " " + re.sub(r"[^A-Z0-9$ ]+", " ", texto) + " "


# ---------- 1. ENTENDER ----------

# Palavras procuradas como PALAVRA INTEIRA ou início de palavra
# (ex.: "CRESC" pega cresceu/crescendo). A ordem da lista só
# desempata; quem tem mais palavras encontradas vence.
ASSUNTOS = [
    ("METODO", ["COMO CALCUL", "COMO FOI CALCUL", "METODO", "METODOLOGIA", "FONTE",
                "DE ONDE VEM", "CONFIAVE", "CONFIAR", "DATASUS", "SIH", "COMO LER"]),
    ("PROJECAO", ["PREVIS", "PREVER", "PREVE", "PROJEC", "PROJETA", "FUTURO", "PROXIMOS ANOS",
                  "PROXIMO ANO", "VAI AUMENTAR", "VAI CRESCER", "VAI DIMINUIR", "VAI CAIR",
                  "2026", "2027", "2028", "ESPERAR", "DAQUI"]),
    ("ATENCAO", ["ATENCAO", "PRIORIDADE", "PRIORIT", "PREOCUP", "URGEN", "INVESTIR",
                 "INVESTIMENTO", "ORCAMENT", "RECURSO", "ONDE AGIR", "O QUE FAZER", "PLANEJ",
                 "FOCAR", "FOCO", "POLITICA"]),
    ("FORA_PADRAO", ["FORA DO PADRAO", "ANOMALIA", "ATIPIC", "ANORMA", "ESTRANH", "PICO",
                     "SALTO", "SALTOU", "ACIMA DO ESPERADO", "ABAIXO DO ESPERADO", "FORA DO NORMAL"]),
    ("ESTADO", ["ESTADO", "SAO PAULO", "SP", "ESTADUAL", "COMPARAD", "COMPARAR", "COMPARACAO",
                "RESTO DO ESTADO"]),
    ("MORTALIDADE", ["MORTALIDADE", "OBITO", "MORTE", "MORRE", "MORREM", "MORRERAM", "MATA",
                     "LETAL", "GRAVE", "GRAVIDADE"]),
    ("CUSTO", ["CUSTO", "CUSTA", "CUSTOU", "GASTO", "GASTOU", "GASTA", "VALOR", "DINHEIRO",
               "CARO", "REAIS", "R$", "PAGO"]),
    ("PERMANENCIA", ["PERMANENCIA", "DIAS", "LEITO", "TEMPO INTERNAD", "FICAM INTERNAD",
                     "FICA INTERNAD", "QUANTO TEMPO"]),
    ("EVOLUCAO", ["EVOLU", "CRESC", "AUMENT", "DIMINU", "CAIU", "CAINDO", "CAEM", "SUBIU",
                  "MUDOU", "MUDARAM", "AO LONGO", "HISTOR", "TENDENCIA", "ANO A ANO"]),
    ("PANORAMA", ["GERAL", "PANORAMA", "SITUACAO", "RESUMO", "QUAIS", "MAIS COMUM", "MAIS AFETA",
                  "RANKING", "MAIOR", "MAIORES", "TOTAL", "QUANTAS", "QUANTOS"]),
]

SINONIMOS_CANCER = {
    "COLORRETAL": ["COLORRETAL", "COLO RETAL", "INTESTINO", "RETO", "COLON"],
    "COLO_UTERO": ["COLO DO UTERO", "COLO UTERO", "UTERO", "CERVICAL", "COLO_UTERO"],
    "MAMA": ["MAMA", "MAMAS", "SEIO", "SEIOS"],
    "PELE_NAO_MELANOMA": ["PELE"],
    "PULMAO": ["PULMAO", "PULMOES", "PULMONAR"],
    "OVARIO": ["OVARIO", "OVARIOS"],
    "TIREOIDE": ["TIREOIDE", "TIROIDE"],
}


def _encontra(texto_norm, palavra):
    """Palavra inteira, ou início de palavra quando o termo é um
    radical (ex.: 'CRESC'). Evita 'RETO' dentro de 'DIRETO'."""
    termo = normalizar(palavra).strip()
    return re.search(r"(?<![A-Z0-9])" + re.escape(termo), texto_norm) is not None


def detectar_cancer(texto_norm, disponiveis):
    for codigo, termos in SINONIMOS_CANCER.items():
        if codigo in disponiveis and any(
                re.search(r"(?<![A-Z0-9])" + re.escape(normalizar(t).strip()) + r"(?![A-Z0-9])", texto_norm)
                for t in termos):
            return codigo
    # códigos que não estão na lista de sinônimos: pelo nome bonito
    for codigo in disponiveis:
        if codigo not in SINONIMOS_CANCER and _encontra(texto_norm, nome_doenca(codigo)):
            return codigo
    return None


def detectar_ano(texto_norm):
    anos = re.findall(r"(?<![0-9])(20[0-9]{2})(?![0-9])", texto_norm)
    return int(anos[0]) if anos else None


def entender(pergunta, disponiveis, cancer_em_foco=None):
    texto = normalizar(pergunta)
    pontos = {nome: sum(_encontra(texto, p) for p in palavras) for nome, palavras in ASSUNTOS}
    melhor = max(pontos.values())
    cancer_citado = detectar_cancer(texto, disponiveis)
    ano = detectar_ano(texto)
    if melhor == 0:
        # "o que aconteceu em 2025?" -> anos fora do padrão
        assunto = "EVOLUCAO" if cancer_citado else ("FORA_PADRAO" if ano else "PANORAMA")
    else:
        assunto = next(nome for nome, _ in ASSUNTOS if pontos[nome] == melhor)
    if assunto == "PANORAMA" and cancer_citado:
        # "quantas internações de mama?" é sobre mama, não sobre todos
        assunto = "EVOLUCAO"
    return {
        "assunto": assunto,
        "cancer": cancer_citado,
        "cancer_citado": cancer_citado is not None,
        "cancer_em_foco": cancer_em_foco if cancer_em_foco in disponiveis else None,
        "ano": ano,
    }


# ---------- 2. CALCULAR ----------

def _plural(n, singular, plural):
    return f"{formatar_numero(n)} {singular if n == 1 else plural}"


def _pct(parte, total):
    return parte / total * 100 if total else 0.0


def _taxa(serie, cancer, grupo, campo_num, campo_den="internacoes"):
    dados = serie_doenca(serie, cancer, grupo)
    den = dados[campo_den].sum()
    return (dados[campo_num].sum() / den if den else 0.0), dados[campo_num].sum(), den


def fatos_panorama(serie, cidade, _cancer):
    resumo = resumo_doencas(serie)
    total = resumo["internacoes"].sum()
    ano_ini, ano_fim = int(serie["ano"].min()), int(serie["ano"].max())
    fatos = [f"De {ano_ini} a {ano_fim}, mulheres de {cidade} tiveram {formatar_numero(total)} "
             f"internações no SUS pelos {len(resumo)} tipos de câncer acompanhados, com "
             f"{formatar_numero(resumo['obitos'].sum())} óbitos durante a internação."]
    for i, linha in resumo.head(3).iterrows():
        fatos.append(f"{i + 1}º lugar: {linha['doenca']}, com {formatar_numero(linha['internacoes'])} "
                     f"internações ({formatar_numero(_pct(linha['internacoes'], total))}% do total).")
    ritmos = {c: ritmo_anual_pct(serie_doenca(serie, c)) for c in resumo["tipo_cancer"]}
    mais_rapido = max(ritmos, key=ritmos.get)
    if ritmos[mais_rapido] > 1:
        fatos.append(f"O câncer que mais cresce é {nome_doenca(mais_rapido).lower()}: "
                     f"{formatar_numero(ritmos[mais_rapido], 1)}% ao ano em média.")
    return fatos, "Veja no primeiro gráfico (barras) do painel."


def fatos_evolucao(serie, cidade, cancer, ano=None):
    dados = serie_doenca(serie, cancer)
    fatos = [f"Câncer de {nome_doenca(cancer).lower()} em {cidade}:"]
    fatos += leitura_evolucao(serie, cancer)
    pico = dados.loc[dados["internacoes"].idxmax()]
    fatos.append(f"O ano com mais internações foi {int(pico['ano'])} ({formatar_numero(pico['internacoes'])}).")
    if ano is not None and ano in set(dados["ano"]):
        valor = dados.loc[dados["ano"] == ano, "internacoes"].iloc[0]
        fatos.append(f"Em {ano} foram {formatar_numero(valor)} internações.")
    return fatos, "Veja no gráfico de evolução, com o câncer escolhido nas barras."


def fatos_estado(serie, cidade, cancer):
    if cancer:
        comp = comparar_com_estado(serie, cancer)
        nome = nome_doenca(cancer).lower()
        fatos = [f"Câncer de {nome}: em {cidade} as internações variam "
                 f"{formatar_numero(comp['ritmo_municipio'], 1)}% ao ano; no Estado de SP, "
                 f"{formatar_numero(comp['ritmo_estado'] or 0, 1)}% ao ano."]
        fatos += [f for f in leitura_evolucao(serie, cancer) if "Estado" in f]
        return fatos, "Veja no gráfico de evolução com o botão 'Comparar com o Estado de SP' ligado."
    fatos = [f"Ritmo de crescimento das internações, {cidade} x Estado de SP:"]
    for codigo in resumo_doencas(serie)["tipo_cancer"]:
        comp = comparar_com_estado(serie, codigo)
        dif = comp["ritmo_municipio"] - (comp["ritmo_estado"] or 0)
        situacao = ("mais rápido que o Estado" if dif > 1.5 else
                    "mais lento que o Estado" if dif < -1.5 else "parecido com o Estado")
        fatos.append(f"{nome_doenca(codigo)}: {formatar_numero(comp['ritmo_municipio'], 1)}% ao ano "
                     f"({situacao}, que tem {formatar_numero(comp['ritmo_estado'] or 0, 1)}%).")
    return fatos, "Veja no gráfico de evolução com o botão 'Comparar com o Estado de SP' ligado."


def _alerta_estado(serie):
    ano_fim = int(serie["ano"].max())
    fora, total = ano_atipico_no_estado(serie, ano_fim)
    if total and fora >= total / 2:
        return (f"Atenção: em {ano_fim}, {fora} dos {total} cânceres saltaram ao mesmo tempo no "
                f"Estado de SP inteiro. Isso sugere mudança no registro ou processamento das AIHs, "
                f"não necessariamente no adoecimento; {ano_fim} está em investigação.")
    return None


def fatos_fora_padrao(serie, cidade, cancer):
    canceres = [cancer] if cancer else list(resumo_doencas(serie)["tipo_cancer"])
    fatos = []
    for codigo in canceres:
        fora = anos_fora_do_padrao(serie_doenca(serie, codigo))
        for _, linha in fora.iterrows():
            aviso = " (números pequenos: pode ser acaso)" if linha["numeros_pequenos"] else ""
            fatos.append(f"{nome_doenca(codigo)}: {linha['ano']} ficou {linha['direcao']} do esperado "
                         f"({formatar_numero(linha['observado'])} internações; esperado cerca de "
                         f"{formatar_numero(linha['esperado'])}){aviso}.")
    if not fatos:
        alvo = f"câncer de {nome_doenca(cancer).lower()}" if cancer else "nenhum câncer"
        fatos.append(f"Em {cidade}, {alvo} {'não teve' if cancer else 'teve'} ano fora do padrão "
                     f"pela tendência dos outros anos.")
    alerta = _alerta_estado(serie)
    if alerta:
        fatos.append(alerta)
    fatos.append("Detectar um ano fora do padrão não explica a causa.")
    return fatos, "Veja no gráfico de evolução com o botão 'Destacar anos fora do padrão' ligado."


def fatos_projecao(serie, cidade, cancer):
    canceres = [cancer] if cancer else list(resumo_doencas(serie)["tipo_cancer"].head(3))
    fatos = []
    for codigo in canceres:
        dados = serie_doenca(serie, codigo)
        proj = projetar(dados).iloc[-1]
        teste = testar_projecao(dados)
        fatos.append(
            f"{nome_doenca(codigo)}: se a tendência de {int(dados['ano'].min())}–{int(dados['ano'].max())} "
            f"continuar, {int(proj['ano'])} deve ter cerca de {formatar_numero(proj['internacoes'])} "
            f"internações (faixa provável de {formatar_numero(proj['minimo'])} a "
            f"{formatar_numero(proj['maximo'])}); em {int(dados['ano'].max())} foram "
            f"{formatar_numero(dados['internacoes'].iloc[-1])}.")
        if teste:
            melhor = "menos" if teste["erro_tendencia"] <= teste["erro_media"] else "mais"
            fatos.append(f"No teste de acerto (prevendo anos já conhecidos), a tendência de "
                         f"{nome_doenca(codigo).lower()} errou {melhor} do que repetir a média dos anos anteriores.")
        if dados["internacoes"].mean() < MEDIA_PEQUENA:
            fatos.append(f"{nome_doenca(codigo)} tem poucas internações por ano: a faixa é larga e a projeção é frágil.")
    alerta = _alerta_estado(serie)
    if alerta:
        fatos.append(alerta)
    fatos.append("É uma projeção exploratória: descreve o que acontece se o passado se repetir; "
                 "não é previsão clínica e não indica causa.")
    return fatos, "Veja no gráfico de evolução com o botão 'Projeção exploratória' ligado."


def fatos_mortalidade(serie, cidade, cancer):
    canceres = [cancer] if cancer else list(resumo_doencas(serie)["tipo_cancer"])
    linhas = []
    for codigo in canceres:
        taxa, obitos, intern = _taxa(serie, codigo, "MUNICIPIO", "obitos")
        taxa_sp, _, _ = _taxa(serie, codigo, GRUPO_ESTADO, "obitos")
        linhas.append((taxa, codigo, obitos, intern, taxa_sp))
    linhas.sort(reverse=True)
    fatos = [f"Óbitos durante a internação (letalidade hospitalar), {cidade} x Estado de SP, "
             f"{int(serie['ano'].min())}–{int(serie['ano'].max())}:"]
    if len(linhas) > 1:
        taxa, codigo = linhas[0][0], linhas[0][1]
        fatos[0] = (f"Em {cidade}, a maior letalidade hospitalar é a do câncer de "
                    f"{nome_doenca(codigo).lower()} ({formatar_numero(taxa * 100, 1)}% das internações "
                    f"terminaram em óbito). " + fatos[0])
    for taxa, codigo, obitos, intern, taxa_sp in linhas:
        aviso = " (poucos óbitos: comparação frágil)" if obitos < 10 else ""
        fatos.append(f"{nome_doenca(codigo)}: {_plural(obitos, 'óbito', 'óbitos')} em {formatar_numero(intern)} "
                     f"internações = {formatar_numero(taxa * 100, 1)}%; no Estado, "
                     f"{formatar_numero(taxa_sp * 100, 1)}%{aviso}.")
    fatos.append("Isso mede óbitos no hospital, não a mortalidade da doença na população.")
    return fatos, "Os óbitos aparecem ao passar o mouse nas barras do painel."


def fatos_custo(serie, cidade, cancer):
    canceres = [cancer] if cancer else list(resumo_doencas(serie)["tipo_cancer"])
    fatos = []
    total = 0.0
    for codigo in canceres:
        medio, valor, intern = _taxa(serie, codigo, "MUNICIPIO", "valor_total")
        medio_sp, _, _ = _taxa(serie, codigo, GRUPO_ESTADO, "valor_total")
        total += valor
        fatos.append(f"{nome_doenca(codigo)}: R$ {formatar_numero(valor)} em {formatar_numero(intern)} internações "
                     f"(média de R$ {formatar_numero(medio)} por internação; no Estado, R$ {formatar_numero(medio_sp)}).")
    fatos.insert(0, f"Valor pago pelo SUS pelas internações de mulheres de {cidade}, "
                    f"{int(serie['ano'].min())}–{int(serie['ano'].max())}: R$ {formatar_numero(total)}.")
    fatos.append("É o valor das AIHs (internação); quimioterapia e radioterapia ambulatoriais não entram. "
                 "O Escudo não define valores de orçamento.")
    return fatos, "Esses valores ainda não têm gráfico próprio no painel."


def fatos_permanencia(serie, cidade, cancer):
    canceres = [cancer] if cancer else list(resumo_doencas(serie)["tipo_cancer"])
    fatos = [f"Tempo médio de internação, {cidade} x Estado de SP:"]
    for codigo in canceres:
        media, _, _ = _taxa(serie, codigo, "MUNICIPIO", "dias_permanencia")
        media_sp, _, _ = _taxa(serie, codigo, GRUPO_ESTADO, "dias_permanencia")
        fatos.append(f"{nome_doenca(codigo)}: {formatar_numero(media, 1)} dias "
                     f"(Estado: {formatar_numero(media_sp, 1)} dias).")
    return fatos, "Esses valores ainda não têm gráfico próprio no painel."


def sinais_de_atencao(serie, codigo):
    """Evidências (não opiniões) que justificam olhar para um câncer
    no planejamento. Cada sinal vem com o número que o sustenta."""
    dados = serie_doenca(serie, codigo)
    comp = comparar_com_estado(serie, codigo)
    sinais = []
    if comp["ritmo_municipio"] >= 3:
        sinais.append(f"internações crescem {formatar_numero(comp['ritmo_municipio'], 1)}% ao ano")
    if comp["ritmo_estado"] is not None and comp["ritmo_municipio"] - comp["ritmo_estado"] > 1.5:
        sinais.append(f"cresce mais rápido que o Estado ({formatar_numero(comp['ritmo_estado'], 1)}% ao ano)")
    taxa, obitos, _ = _taxa(serie, codigo, "MUNICIPIO", "obitos")
    taxa_sp, _, _ = _taxa(serie, codigo, GRUPO_ESTADO, "obitos")
    if obitos >= 5 and taxa > taxa_sp * 1.2:
        sinais.append(f"letalidade hospitalar de {formatar_numero(taxa * 100, 1)}%, acima do Estado "
                      f"({formatar_numero(taxa_sp * 100, 1)}%)")
    ano_fim = int(dados["ano"].max())
    recentes = anos_fora_do_padrao(dados)
    recentes = recentes[(recentes["direcao"] == "acima") & (recentes["ano"] >= ano_fim - 2)
                        & (recentes["ano"] < ano_fim)]  # o último ano está em investigação
    for _, linha in recentes.iterrows():
        sinais.append(f"{linha['ano']} ficou acima do esperado")
    return sinais


# Linhas de ação conhecidas (diretrizes do INCA). O Escudo lista
# possibilidades; não escolhe nem define valores.
LINHAS_DE_ACAO = {
    "MAMA": "existe rastreamento recomendado (mamografia de 50 a 69 anos)",
    "COLO_UTERO": "existe rastreamento recomendado (exame preventivo / teste de DNA-HPV) e vacina contra HPV",
    "COLORRETAL": "existe rastreamento possível (pesquisa de sangue oculto nas fezes)",
    "PELE_NAO_MELANOMA": "há prevenção por fotoproteção e exame de lesões na atenção básica",
    "PULMAO": "a prevenção passa pelo controle do tabagismo",
}


def fatos_atencao(serie, cidade, cancer):
    canceres = [cancer] if cancer else list(resumo_doencas(serie)["tipo_cancer"])
    avaliados = sorted(((sinais_de_atencao(serie, c), c) for c in canceres), key=lambda x: -len(x[0]))
    fatos = [f"Sinais nos dados de {cidade} que merecem atenção no planejamento "
             f"(evidências, não uma ordem de gasto):"]
    com_sinal = [(s, c) for s, c in avaliados if s]
    for sinais, codigo in com_sinal:
        linha = f"{nome_doenca(codigo)}: " + "; ".join(sinais) + "."
        if codigo in LINHAS_DE_ACAO:
            linha += f" Possível linha de ação: {LINHAS_DE_ACAO[codigo]}."
        fatos.append(linha)
    sem = [nome_doenca(c) for s, c in avaliados if not s]
    if sem:
        fatos.append("Sem sinal de alerta pelos mesmos critérios: " + ", ".join(sem) + ".")
    alerta = _alerta_estado(serie)
    if alerta:
        fatos.append(alerta)
    fatos.append("O Escudo não define quanto investir: aponta onde os dados mostram sinais. "
                 "A decisão é da gestão, que conhece orçamento, filas e capacidade instalada.")
    return fatos, "Para cada câncer citado, veja o gráfico de evolução com as camadas ligadas."


def fatos_metodo(serie, cidade, _cancer):
    return [
        f"Fonte: internações do SUS (SIH/SUS, DATASUS) de mulheres residentes em {cidade}, "
        f"{int(serie['ano'].min())}–{int(serie['ano'].max())}, para 7 tipos de câncer.",
        "Internação não é caso novo: a mesma mulher pode ser internada mais de uma vez, e quem se "
        "trata só em ambulatório ou por plano privado não aparece.",
        "O ano é o de processamento da internação (competência da AIH).",
        "Tendência: reta ajustada sobre todos os anos. Ano fora do padrão: longe do esperado pela "
        "tendência dos outros anos, além da oscilação normal e com diferença de pelo menos 3 internações.",
        "Comparação com o Estado: a série de SP redimensionada para o tamanho da cidade, para comparar o ritmo.",
        "Projeção exploratória: a tendência prolongada, com faixa de ~90% e teste de acerto em anos já conhecidos.",
        "Os números são calculados pelo sistema; a IA só redige a explicação.",
    ], "Veja também 'Como ler estes dados', no fim do painel."


CALCULOS = {
    "PANORAMA": fatos_panorama,
    "EVOLUCAO": fatos_evolucao,
    "ESTADO": fatos_estado,
    "FORA_PADRAO": fatos_fora_padrao,
    "PROJECAO": fatos_projecao,
    "MORTALIDADE": fatos_mortalidade,
    "CUSTO": fatos_custo,
    "PERMANENCIA": fatos_permanencia,
    "ATENCAO": fatos_atencao,
    "METODO": fatos_metodo,
}

# Assuntos que falam de UM câncer: sem câncer citado, usam o que está
# em foco no painel. Os demais, sem câncer citado, comparam todos.
POR_CANCER = {"EVOLUCAO"}


def calcular(entendido, serie, cidade):
    assunto = entendido["assunto"]
    cancer = entendido["cancer"]
    if cancer is None and assunto in POR_CANCER:
        cancer = entendido["cancer_em_foco"]
    if assunto == "EVOLUCAO":
        if cancer is None:
            return fatos_panorama(serie, cidade, None)
        return fatos_evolucao(serie, cidade, cancer, entendido["ano"])
    return CALCULOS[assunto](serie, cidade, cancer)


# ---------- 3. EXPLICAR ----------

def resposta_direta(fatos, onde_ver):
    """Resposta sem IA: os próprios fatos, em lista."""
    primeira, resto = fatos[0], fatos[1:]
    texto = primeira + ("\n\n" + "\n".join(f"- {f}" for f in resto) if resto else "")
    return texto + f"\n\n_{onde_ver}_"


def responder(pergunta, serie, cidade, cancer_em_foco=None, perfil="SIMPLES", explicar=None):
    """Devolve dict com texto, assunto, câncer, fatos e se a IA foi
    usada. `explicar` é a função da IA (padrão: Gemini via
    ia_linguagem); qualquer erro dela cai na resposta direta."""
    disponiveis = set(serie["tipo_cancer"].unique())
    entendido = entender(pergunta, disponiveis, cancer_em_foco)
    fatos, onde_ver = calcular(entendido, serie, cidade)

    if explicar is None:
        try:
            from ia_linguagem import responder_com_ia as explicar
        except Exception:
            explicar = None

    texto, usou_ia = None, False
    if explicar is not None:
        try:
            contexto = "\n".join(f"- {f}" for f in fatos)
            texto = explicar(pergunta, contexto, perfil)
            usou_ia = bool(texto and texto.strip())
            if usou_ia:
                texto = texto.strip() + f"\n\n_{onde_ver}_"
        except Exception:
            texto = None
    if not usou_ia:
        texto = resposta_direta(fatos, onde_ver)

    return {"texto": texto, "assunto": entendido["assunto"],
            "cancer": entendido["cancer"] or entendido["cancer_em_foco"],
            "fatos": fatos, "usou_ia": usou_ia}


def registrar_pergunta(banco, assunto):
    """Conta em perguntas_usuarios o ASSUNTO de uma pergunta (a tabela que
    analise_perguntas.py lê), para saber o que as pessoas perguntam.

    O texto escrito nunca é guardado (decisão de privacidade, 10/2026): quem escreve
    "estou com câncer, o que faço?" conta um dado de saúde, e texto livre pode trazer
    nome, bairro ou idade. A coluna `pergunta` existe só por compatibilidade e fica vazia."""
    try:
        conn = sqlite3.connect(banco)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS perguntas_usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT,
                    pergunta TEXT, categoria TEXT, reconhecida TEXT)
            """)
            conn.execute(
                "INSERT INTO perguntas_usuarios (data_hora, pergunta, categoria, reconhecida) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), None, assunto, "SIM"),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        pass  # registrar é opcional; nunca derruba a resposta
