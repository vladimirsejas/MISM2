import math
import sqlite3
import unicodedata

import numpy as np
import pandas as pd

# =====================================
# INTELIGÊNCIA CENTRAL DO ESCUDO
#
# Um lugar só para calcular o que a tela e o chat mostram. Antes,
# cada aba do dashboard fazia a sua própria consulta a `internacoes`
# e a mesma informação aparecia (e podia divergir) em vários lugares.
# Aqui cada conta é feita uma vez; quem exibe só lê o resultado.
#
# Funções puras (recebem DataFrame, devolvem DataFrame/dict), para
# poderem ser testadas sem o banco do Windows -- ver
# teste_inteligencia.py.
#
# Regras que valem para tudo daqui:
#   - SIH/SUS registra internações (AIH), não casos novos.
#   - O ano é o de competência/processamento da AIH (ANO_CMPT),
#     não necessariamente o ano em que a internação aconteceu.
#   - Detectar um comportamento fora do padrão NÃO explica a causa.
# =====================================

from configuracao_geografica import BANCO  # único lugar que define onde está o banco

GRUPO_MUNICIPIO = "MUNICIPIO"
GRUPO_ESTADO = "SP"

# No banco os cânceres vêm como códigos (MAMA, COLO_UTERO ...).
NOMES_DOENCAS = {
    "MAMA": "Mama",
    "COLO_UTERO": "Colo do útero",
    "COLORRETAL": "Colorretal",
    "OVARIO": "Ovário",
    "PELE_NAO_MELANOMA": "Pele não melanoma",
    "PULMAO": "Pulmão",
    "TIREOIDE": "Tireoide",
}

# Anos fora do padrão: a diferença para o esperado precisa passar
# de LIMIAR_DESVIOS "desvios" E ser de pelo menos DIFERENCA_MINIMA
# internações. A segunda regra existe para cidades pequenas, onde
# 1 -> 3 internações seria "+200%" sem significar nada.
LIMIAR_DESVIOS = 2.5
DIFERENCA_MINIMA = 3

# Abaixo desta média anual, qualquer leitura da série leva o aviso
# de "números pequenos".
MEDIA_PEQUENA = 10

Z_90 = 1.645  # faixa provável de ~90% da projeção


# =====================================
# FORMATAÇÃO
# =====================================

def _sem_acento(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def nome_doenca(codigo):
    """'COLO_UTERO' -> 'Colo do útero'. Nome desconhecido vira
    'Primeira maiúscula' em vez de sumir."""
    chave = _sem_acento(codigo).upper().replace(" ", "_")
    if chave in NOMES_DOENCAS:
        return NOMES_DOENCAS[chave]
    texto = str(codigo).replace("_", " ").strip().lower()
    return texto[:1].upper() + texto[1:]


def cancer_de(codigo):
    """'MAMA' -> 'câncer de mama'; 'COLORRETAL' -> 'câncer colorretal'
    (sem o "de", que fica errado em português)."""
    nome = nome_doenca(codigo).lower()
    return "câncer colorretal" if nome == "colorretal" else f"câncer de {nome}"


def formatar_numero(valor, casas=0):
    """1234.5 -> '1.234,5' (padrão brasileiro)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


# =====================================
# CARREGAMENTO (única consulta a `internacoes`)
# =====================================

SQL_MUNICIPIO = """
SELECT tipo_cancer, origem, ano,
       COUNT(*) AS internacoes,
       COALESCE(SUM(obito), 0) AS obitos,
       COALESCE(SUM(valor_total), 0) AS valor_total,
       COALESCE(SUM(dias_permanencia), 0) AS dias_permanencia
FROM internacoes
WHERE municipio = ?
GROUP BY tipo_cancer, origem, ano
"""

SQL_ESTADO = """
SELECT tipo_cancer, 'SP' AS grupo, ano,
       COUNT(*) AS internacoes,
       COALESCE(SUM(obito), 0) AS obitos,
       COALESCE(SUM(valor_total), 0) AS valor_total,
       COALESCE(SUM(dias_permanencia), 0) AS dias_permanencia
FROM internacoes
WHERE origem = ?
GROUP BY tipo_cancer, ano
"""


def escolher_uma_fonte(linhas_municipio, uf_referencia="SP"):
    """As moradoras de Rio Claro podem estar em `internacoes` duas
    vezes com municipio = 'RIO_CLARO': vindas do arquivo de Rio
    Claro (origem RIO_CLARO) E do arquivo estadual (origem SP), que
    traz todas as cidades. Somar tudo por `municipio` contaria essas
    internações em dobro. Por isso usamos UMA fonte por cidade: a
    estadual, que é a mesma para todas as cidades (comparação
    justa); o arquivo próprio da cidade só entra se ela não estiver
    no estadual. A escolha é por câncer: um câncer sem arquivo
    estadual continua valendo pelo arquivo da cidade.
    (etl/carga_todas_bases.py já evita a duplicidade na carga; isto
    protege bancos carregados antes da correção.)"""
    if linhas_municipio.empty:
        return linhas_municipio
    partes = []
    for _, linhas in linhas_municipio.groupby("tipo_cancer"):
        fontes = linhas["origem"].unique()
        fonte = uf_referencia if uf_referencia in fontes else fontes[0]
        partes.append(linhas[linhas["origem"] == fonte])
    return pd.concat(partes, ignore_index=True)


# ---------- anos incompletos na fonte ----------
#
# O DATASUS não oferece todos os meses do SIH/RD de SP: faltam 35 dos
# 156 meses de 2013 a 2025 (2018 tem só 6), os mesmos para todos os
# cânceres -- ver docs/FONTE_DOS_DADOS.md. Um ano com meses faltando
# tem total menor sem que menos mulheres tenham sido internadas, e
# isso distorcia tendência, anos fora do padrão, projeção e radar
# (o "salto de 2025" era só 2025 ter os 12 meses).
#
# Regra: para COMPARAR anos, cada ano vale a média dos meses
# disponíveis x 12 (colunas internacoes, obitos, valor_total,
# dias_permanencia). Os valores REGISTRADOS ficam em <coluna>_reg e
# são os usados nos totais do período (resumo, ficha, letalidade).
# O número de meses de cada ano vem do Estado (o arquivo mensal que
# falta é o do Estado inteiro, então falta também para a cidade).

COLUNAS_VALOR = ["internacoes", "obitos", "valor_total", "dias_permanencia"]
MESES_NO_ANO = 12

SQL_MESES = """
SELECT ano, COUNT(DISTINCT mes) AS meses
FROM internacoes
WHERE origem = ? AND mes IS NOT NULL
GROUP BY ano
"""


def meses_por_ano(conexao, uf_referencia="SP"):
    """{ano: meses de competência disponíveis}. None se o banco foi
    carregado antes de a carga guardar o mês (coluna `mes`)."""
    try:
        tabela = pd.read_sql(SQL_MESES, conexao, params=(uf_referencia,))
    except Exception:  # banco antigo, sem a coluna mes
        return None
    if tabela.empty:
        return None
    return {int(a): int(m) for a, m in zip(tabela["ano"], tabela["meses"])}


def ajustar_meses(serie, meses):
    """Guarda os valores registrados em <coluna>_reg, anota os meses
    de cada ano e, se `meses` for conhecido, põe em <coluna> a média
    mensal x 12 (valor comparável entre anos)."""
    serie = serie.copy()
    serie["meses"] = serie["ano"].map(meses).astype(float) if meses else np.nan
    for coluna in COLUNAS_VALOR:
        serie[coluna + "_reg"] = serie[coluna]
        if meses:
            fator = (MESES_NO_ANO / serie["meses"]).where(serie["meses"] > 0, 1.0)
            serie[coluna] = serie[coluna] * fator
    return serie


def registrado(dados, coluna):
    """A coluna com o valor REGISTRADO (sem o ajuste de meses), para
    somar totais do período. Séries sem ajuste: a própria coluna."""
    return dados[coluna + "_reg"] if coluna + "_reg" in dados else dados[coluna]


def anos_incompletos(serie):
    """{ano: meses} dos anos com menos de 12 meses na fonte."""
    if "meses" not in serie or serie["meses"].isna().all():
        return {}
    por_ano = serie.groupby("ano")["meses"].max()
    return {int(a): int(m) for a, m in por_ano.items() if 0 < m < MESES_NO_ANO}


def carregar_serie(conexao, municipio, uf_referencia="SP"):
    """Série anual por câncer do município e da referência
    estadual. Tudo o que o dashboard mostra sai daqui. Os anos são
    comparáveis (média mensal x 12, ver ajustar_meses); os valores
    registrados ficam em <coluna>_reg."""
    mun = pd.read_sql(SQL_MUNICIPIO, conexao, params=(municipio,))
    mun = escolher_uma_fonte(mun, uf_referencia).drop(columns="origem")
    mun.insert(1, "grupo", GRUPO_MUNICIPIO)
    est = pd.read_sql(SQL_ESTADO, conexao, params=(uf_referencia,))
    serie = pd.concat([mun, est], ignore_index=True)
    serie = serie[serie["tipo_cancer"].notna()]
    if serie.empty:
        return serie
    return ajustar_meses(completar_anos(serie), meses_por_ano(conexao, uf_referencia))


def completar_anos(serie):
    """Uma linha por (câncer, grupo, ano) no período inteiro, com
    zero onde não houve internação: ano sem registro é informação
    (zero), não dado faltante. Sem isso, uma cidade pequena com
    internação só em 2014 e 2020 ganharia uma "reta" entre os dois."""
    anos = range(int(serie["ano"].min()), int(serie["ano"].max()) + 1)
    indice = pd.MultiIndex.from_product(
        [serie["tipo_cancer"].unique(), serie["grupo"].unique(), anos],
        names=["tipo_cancer", "grupo", "ano"],
    )
    return (serie.set_index(["tipo_cancer", "grupo", "ano"])
                 .reindex(indice, fill_value=0)
                 .reset_index())


def serie_doenca(serie, cancer, grupo=GRUPO_MUNICIPIO):
    return (serie[(serie["tipo_cancer"] == cancer) & (serie["grupo"] == grupo)]
            .sort_values("ano").reset_index(drop=True))


# =====================================
# PANORAMA: quais doenças pesam mais
# =====================================

def resumo_doencas(serie):
    """Totais do município por câncer no período, maior primeiro."""
    mun = serie[serie["grupo"] == GRUPO_MUNICIPIO]
    # totais do período: sempre o REGISTRADO (sem o ajuste de meses)
    mun = mun.assign(**{c: registrado(mun, c) for c in COLUNAS_VALOR})
    resumo = (mun.groupby("tipo_cancer", as_index=False)[COLUNAS_VALOR].sum())
    resumo = resumo[resumo["internacoes"] > 0]
    resumo["doenca"] = resumo["tipo_cancer"].map(nome_doenca)
    return resumo.sort_values("internacoes", ascending=False).reset_index(drop=True)


# =====================================
# TENDÊNCIA
# =====================================

def ajustar_tendencia(anos, valores):
    """Reta de mínimos quadrados + o necessário para a faixa de
    previsão."""
    x = np.asarray(anos, dtype=float)
    y = np.asarray(valores, dtype=float)
    n = len(x)
    if n < 3:
        media = float(y.mean()) if n else 0.0
        return {"inclinacao": 0.0, "intercepto": media,
                "x_medio": float(x.mean()) if n else 0.0,
                "sxx": 1.0, "s": float(y.std()) if n else 0.0, "n": n}
    x_medio = x.mean()
    sxx = float(((x - x_medio) ** 2).sum())
    inclinacao = float(((x - x_medio) * (y - y.mean())).sum() / sxx)
    intercepto = float(y.mean() - inclinacao * x_medio)
    residuos = y - (intercepto + inclinacao * x)
    s = float(np.sqrt((residuos ** 2).sum() / (n - 2)))
    return {"inclinacao": inclinacao, "intercepto": intercepto,
            "x_medio": float(x_medio), "sxx": sxx, "s": s, "n": n}


def prever(modelo, anos):
    """Ponto e faixa de ~90%, nunca abaixo de zero."""
    x0 = np.asarray(anos, dtype=float)
    ponto = modelo["intercepto"] + modelo["inclinacao"] * x0
    erro = modelo["s"] * np.sqrt(
        1 + 1 / max(modelo["n"], 1) + (x0 - modelo["x_medio"]) ** 2 / modelo["sxx"])
    return (np.clip(ponto, 0, None),
            np.clip(ponto - Z_90 * erro, 0, None),
            np.clip(ponto + Z_90 * erro, 0, None))


def ritmo_anual_pct(dados):
    """Inclinação da tendência em % da média anual: o "ritmo",
    comparável entre cidade e Estado apesar do tamanho diferente."""
    media = dados["internacoes"].mean()
    if media <= 0:
        return 0.0
    return ajustar_tendencia(dados["ano"], dados["internacoes"])["inclinacao"] / media * 100


# =====================================
# COMPARAÇÃO COM O ESTADO
# =====================================

def ritmo_estadual_na_escala(serie, cancer):
    """A série do Estado redimensionada para o tamanho do município
    (mesmo total no período). Assim as duas linhas ficam no MESMO
    eixo, em internações, e a leitura é direta: onde a linha da
    cidade passa acima da cinza, a cidade cresceu mais que o
    Estado. Evita o gráfico de dois eixos, que engana."""
    mun = serie_doenca(serie, cancer, GRUPO_MUNICIPIO)
    est = serie_doenca(serie, cancer, GRUPO_ESTADO)
    if est.empty or est["internacoes"].sum() == 0 or mun.empty:
        return pd.DataFrame(columns=["ano", "internacoes"])
    fator = mun["internacoes"].sum() / est["internacoes"].sum()
    return pd.DataFrame({"ano": est["ano"], "internacoes": est["internacoes"] * fator})


def comparar_com_estado(serie, cancer):
    mun = serie_doenca(serie, cancer, GRUPO_MUNICIPIO)
    est = serie_doenca(serie, cancer, GRUPO_ESTADO)
    ritmo_mun = ritmo_anual_pct(mun)
    ritmo_est = ritmo_anual_pct(est) if not est.empty else None
    return {"ritmo_municipio": ritmo_mun, "ritmo_estado": ritmo_est}


# =====================================
# ANOS FORA DO PADRÃO
# =====================================

def anos_fora_do_padrao(dados):
    """Detecta anos internos da série que se afastam da tendência.

    O ano analisado é retirado do ajuste para não "puxar" a própria
    reta. Mas o primeiro e o último ano da série NÃO são testados:
    para eles a tendência ajustada aos outros anos precisaria ser
    extrapolada para fora do intervalo observado, o que pode criar
    esperados artificialmente próximos de zero e percentuais enormes
    (por exemplo, 6 observadas contra 0,8 esperadas).

    Assim, "fora do padrão" significa uma anomalia dentro do intervalo
    histórico observado, não uma extrapolação nas pontas da série.
    Só detecta; não explica a causa."""
    dados = dados.sort_values("ano").reset_index(drop=True)
    if len(dados) < 6:
        return pd.DataFrame(columns=["ano", "observado", "esperado", "direcao", "numeros_pequenos"])

    # Precisamos de anos dos dois lados para avaliar um ponto sem
    # extrapolar. Por isso as pontas (primeiro/último) ficam fora.
    anos_avaliados = dados["ano"].iloc[1:-1]

    linhas = []
    for ano in anos_avaliados:
        outros = dados[dados["ano"] != ano]
        modelo = ajustar_tendencia(outros["ano"], outros["internacoes"])

        # Aqui o ano está dentro do intervalo dos dados usados no
        # ajuste; portanto não há extrapolação.
        esperado = max(float(modelo["intercepto"] + modelo["inclinacao"] * ano), 0.0)
        observado = float(dados.loc[dados["ano"] == ano, "internacoes"].iloc[0])
        desvio = max(modelo["s"], math.sqrt(max(esperado, 1.0)))
        diferenca = observado - esperado

        if abs(diferenca) > LIMIAR_DESVIOS * desvio and abs(diferenca) >= DIFERENCA_MINIMA:
            linhas.append({
                "ano": int(ano),
                "observado": observado,
                "esperado": esperado,
                "direcao": "acima" if diferenca > 0 else "abaixo",
                "numeros_pequenos": esperado < MEDIA_PEQUENA,
            })

    return pd.DataFrame(linhas, columns=["ano", "observado", "esperado", "direcao", "numeros_pequenos"])


def ponta_fora_da_tendencia(dados):
    """O ÚLTIMO ano comparado com a tendência dos anos ANTERIORES
    (a reta só dos outros anos, prolongada um passo).

    anos_fora_do_padrao() não testa as pontas, para não extrapolar
    com números pequenos (6 observadas contra 0,8 esperadas). Aqui é
    um passo só e exige esperado de pelo menos MEDIA_PEQUENA; abaixo
    disso devolve None (não dá para dizer). Serve para ver saltos no
    ano mais recente -- como 2025, quando os 7 cânceres subiram de
    33% a 83% ao mesmo tempo no Estado inteiro."""
    dados = dados.sort_values("ano")
    if len(dados) < 6:
        return None
    anteriores, ultimo = dados.iloc[:-1], dados.iloc[-1]
    modelo = ajustar_tendencia(anteriores["ano"], anteriores["internacoes"])
    esperado = max(float(modelo["intercepto"] + modelo["inclinacao"] * ultimo["ano"]), 0.0)
    if esperado < MEDIA_PEQUENA:
        return None
    observado = float(ultimo["internacoes"])
    diferenca = observado - esperado
    desvio = max(modelo["s"], math.sqrt(esperado))
    return {
        "ano": int(ultimo["ano"]),
        "observado": observado,
        "esperado": esperado,
        "direcao": "acima" if diferenca > 0 else "abaixo",
        "fora": abs(diferenca) > LIMIAR_DESVIOS * desvio and abs(diferenca) >= DIFERENCA_MINIMA,
    }


def ano_atipico_no_estado(serie, ano):
    """Quantos cânceres tiveram `ano` fora do padrão no Estado. Se
    forem todos ao mesmo tempo, é mais provável uma mudança no
    registro/processamento do que em todas as doenças juntas. O
    último ano da série é avaliado por ponta_fora_da_tendencia (os
    números do Estado são grandes; não há o risco da extrapolação
    com números pequenos); os demais, por anos_fora_do_padrao."""
    canceres = serie[serie["grupo"] == GRUPO_ESTADO]["tipo_cancer"].unique()
    fora = 0
    for c in canceres:
        dados = serie_doenca(serie, c, GRUPO_ESTADO)
        if ano == int(dados["ano"].max()):
            ponta = ponta_fora_da_tendencia(dados)
            fora += bool(ponta and ponta["fora"])
        else:
            fora += ano in set(anos_fora_do_padrao(dados)["ano"])
    return fora, len(canceres)


# =====================================
# PROJEÇÃO EXPLORATÓRIA
# =====================================

def projetar(dados, horizonte=3, coluna="internacoes"):
    """Projeção de tendência: continuação da reta histórica com faixa
    de ~90%. Descreve o que acontece SE o comportamento passado
    continuar -- não é previsão clínica nem causal, e não deve ser
    chamada de "IA preditiva". `coluna` permite projetar também os
    valores hospitalares registrados e os dias de internação."""
    dados = dados.sort_values("ano")
    ultimo = int(dados["ano"].max())
    anos = list(range(ultimo + 1, ultimo + 1 + horizonte))
    ponto, minimo, maximo = prever(ajustar_tendencia(dados["ano"], dados[coluna]), anos)
    return pd.DataFrame({"ano": anos, coluna: ponto,
                         "minimo": minimo, "maximo": maximo})


def tendencia_no_periodo(dados, coluna="internacoes"):
    """A reta da tendência sobre os anos observados -- a mesma que a
    projeção prolonga. No gráfico, a projeção sai DELA, não do último
    ponto: senão um último ano acima da reta faz a projeção parecer
    uma queda mesmo quando a tendência é de alta."""
    dados = dados.sort_values("ano")
    modelo = ajustar_tendencia(dados["ano"], dados[coluna])
    anos = dados["ano"].astype(int).tolist()
    return pd.DataFrame({"ano": anos, coluna: [max(modelo["intercepto"] + modelo["inclinacao"] * a, 0.0)
                                                for a in anos]})


def leitura_ponta_projecao(dados, horizonte=3, coluna="internacoes"):
    """Frase para quando o último ano e a projeção parecem se
    contradizer: tendência de alta, mas a projeção fica ABAIXO do
    último ano (ou o contrário). Acontece quando o último ano ficou
    longe da reta -- a projeção segue a reta de todos os anos, não o
    último. None quando não há contradição aparente."""
    dados = dados.sort_values("ano")
    if len(dados) < 3:
        return None
    reta = tendencia_no_periodo(dados, coluna).iloc[-1][coluna]
    proj = projetar(dados, horizonte, coluna).iloc[-1]
    ultimo = float(dados[coluna].iloc[-1])
    ano_fim = int(dados["ano"].iloc[-1])
    ano_ini = int(dados["ano"].iloc[0])
    subindo = proj[coluna] > reta
    if subindo == (proj[coluna] > ultimo) or abs(ultimo - reta) < DIFERENCA_MINIMA:
        return None
    return (f"Em {ano_fim} foram {formatar_numero(ultimo)}, {'acima' if ultimo > reta else 'abaixo'} da tendência de "
            f"{ano_ini}–{ano_fim} (cerca de {formatar_numero(reta)} para esse ano). A projeção segue a tendência de "
            f"todos os anos, não o último: por isso {int(proj['ano'])} aparece "
            f"{'abaixo' if ultimo > reta else 'acima'} de {ano_fim} sem que isso signifique "
            f"{'queda' if ultimo > reta else 'alta'}. Se {ano_fim} for o novo patamar, {int(proj['ano'])} tende a ficar "
            f"{'acima' if ultimo > reta else 'abaixo'} da projeção.")


def testar_projecao(dados, anos_teste=3, coluna="internacoes"):
    """Treina até (último - anos_teste) e compara o erro nos anos
    seguintes com o de simplesmente repetir a média dos 3 últimos
    anos de treino."""
    dados = dados.sort_values("ano")
    corte = int(dados["ano"].max()) - anos_teste
    treino, teste = dados[dados["ano"] <= corte], dados[dados["ano"] > corte]
    if len(treino) < 3 or teste.empty:
        return None
    ponto, minimo, maximo = prever(ajustar_tendencia(treino["ano"], treino[coluna]), teste["ano"])
    real = teste[coluna].to_numpy(dtype=float)
    return {
        "erro_tendencia": float(np.abs(real - ponto).mean()),
        "erro_media": float(np.abs(real - treino[coluna].tail(3).mean()).mean()),
        "dentro_da_faixa": int(((real >= minimo) & (real <= maximo)).sum()),
        "anos_testados": len(real),
    }


# =====================================
# LEITURAS (frases que acompanham os gráficos)
# =====================================

def leitura_evolucao(serie, cancer):
    """Frases curtas, calculadas, que acompanham o gráfico de
    evolução. A mesma lista pode alimentar o chat."""
    mun = serie_doenca(serie, cancer, GRUPO_MUNICIPIO)
    frases = []
    if mun.empty or mun["internacoes"].sum() == 0:
        return frases

    comp = comparar_com_estado(serie, cancer)
    ritmo = comp["ritmo_municipio"]
    if abs(ritmo) < 1:
        frases.append("As internações ficaram praticamente estáveis ao longo do período.")
    else:
        frases.append(
            f"As internações {'cresceram' if ritmo > 0 else 'caíram'} em média "
            f"{formatar_numero(abs(ritmo), 1)}% ao ano de {int(mun['ano'].min())} a {int(mun['ano'].max())}."
        )

    if comp["ritmo_estado"] is not None:
        diferenca = ritmo - comp["ritmo_estado"]
        ritmo_est = formatar_numero(comp["ritmo_estado"], 1)
        if abs(diferenca) < 1.5:
            frases.append(f"O ritmo é parecido com o do Estado de SP ({ritmo_est}% ao ano).")
        elif diferenca > 0:
            frases.append(f"O ritmo é mais rápido que o do Estado de SP ({ritmo_est}% ao ano).")
        else:
            frases.append(f"O ritmo é mais lento que o do Estado de SP ({ritmo_est}% ao ano).")

    fora = anos_fora_do_padrao(mun)
    for _, linha in fora.iterrows():
        frases.append(
            f"{linha['ano']} ficou {linha['direcao']} do esperado pela tendência "
            f"({formatar_numero(linha['observado'])} internações; o esperado era cerca de "
            f"{formatar_numero(linha['esperado'])})."
        )

    if mun["internacoes"].mean() < MEDIA_PEQUENA:
        frases.append(
            "Números pequenos: com poucas internações por ano, variações de um ano "
            "para outro podem ser acaso. Confirme antes de concluir."
        )
    return frases


# =====================================
# FICHA DE UM CÂNCER: "o que chama atenção?"
#
# Dinheiro aqui é "valor hospitalar registrado no SIH/SUS" (VAL_TOT
# das AIHs): o que o SUS registrou pelas internações. NÃO é o
# orçamento municipal nem o custo total do tratamento (quimioterapia
# e radioterapia ambulatoriais ficam fora).
# =====================================

def _razao(num, den):
    return num / den if den else 0.0


def ficha_cancer(serie, cancer):
    """Os quatro números da doença (internações, óbitos, valor
    hospitalar registrado, dias), cada um com a sua referência."""
    mun = serie_doenca(serie, cancer, GRUPO_MUNICIPIO)
    est = serie_doenca(serie, cancer, GRUPO_ESTADO)
    todos = serie[serie["grupo"] == GRUPO_MUNICIPIO]
    # totais e razões do período: valores REGISTRADOS (ver ajustar_meses)
    mun, est, todos = [d.assign(**{c: registrado(d, c) for c in COLUNAS_VALOR}) for d in (mun, est, todos)]
    intern, obitos = mun["internacoes"].sum(), mun["obitos"].sum()
    valor, dias = mun["valor_total"].sum(), mun["dias_permanencia"].sum()
    return {
        "internacoes": float(intern),
        "obitos": float(obitos),
        "valor": float(valor),
        "dias": float(dias),
        "pct_internacoes": _razao(intern, todos["internacoes"].sum()) * 100,
        "pct_valor": _razao(valor, todos["valor_total"].sum()) * 100,
        "letalidade": _razao(obitos, intern) * 100,
        "letalidade_estado": _razao(est["obitos"].sum(), est["internacoes"].sum()) * 100,
        "valor_medio": _razao(valor, intern),
        "valor_medio_estado": _razao(est["valor_total"].sum(), est["internacoes"].sum()),
        "permanencia": _razao(dias, intern),
        "permanencia_estado": _razao(est["dias_permanencia"].sum(), est["internacoes"].sum()),
    }


def destaques_cancer(serie, cancer):
    """Frases de "o que chama atenção", só quando o número sustenta.
    Nenhuma afirma causa."""
    f = ficha_cancer(serie, cancer)
    frases = [f"Concentra {formatar_numero(f['pct_internacoes'], 1)}% das internações e "
              f"{formatar_numero(f['pct_valor'], 1)}% do valor hospitalar registrado entre os cânceres acompanhados."]
    if f["pct_valor"] - f["pct_internacoes"] > 3:
        frases.append(f"Pesa mais no valor registrado do que no número de internações: cada internação por "
                      f"{cancer_de(cancer)} registra, em média, R$ {formatar_numero(f['valor_medio'])}.")
    if f["obitos"] >= 5 and f["letalidade"] > f["letalidade_estado"] * 1.2:
        frases.append(f"Letalidade hospitalar de {formatar_numero(f['letalidade'], 1)}%, acima da do Estado "
                      f"({formatar_numero(f['letalidade_estado'], 1)}%).")
    elif f["obitos"] >= 5 and f["letalidade"] < f["letalidade_estado"] * 0.8:
        frases.append(f"Letalidade hospitalar de {formatar_numero(f['letalidade'], 1)}%, abaixo da do Estado "
                      f"({formatar_numero(f['letalidade_estado'], 1)}%).")
    if f["permanencia_estado"] and abs(f["permanencia"] - f["permanencia_estado"]) >= 1:
        frases.append(f"Cada internação dura em média {formatar_numero(f['permanencia'], 1)} dias "
                      f"(no Estado, {formatar_numero(f['permanencia_estado'], 1)}).")
    comp = comparar_com_estado(serie, cancer)
    if comp["ritmo_estado"] is not None and comp["ritmo_municipio"] - comp["ritmo_estado"] > 1.5:
        frases.append(f"As internações crescem mais rápido que no Estado "
                      f"({formatar_numero(comp['ritmo_municipio'], 1)}% x {formatar_numero(comp['ritmo_estado'], 1)}% ao ano).")
    fora = anos_fora_do_padrao(serie_doenca(serie, cancer))
    if not fora.empty:
        anos = ", ".join(f"{a} ({d})" for a, d in zip(fora["ano"], fora["direcao"]))
        frases.append(f"Anos fora do padrão: {anos}.")
    return frases


# =====================================
# CONFIABILIDADE DA INFORMAÇÃO
#
# Antes de interpretar, dizer o que pode enganar. Cada aviso vem
# de uma checagem nos dados, não de um texto fixo.
# =====================================

SQL_DUPLICIDADE = """
SELECT tipo_cancer
FROM internacoes
WHERE municipio = ?
GROUP BY tipo_cancer
HAVING COUNT(DISTINCT origem) > 1
"""


def canceres_com_duplicidade(conexao, municipio):
    """Cânceres cuja cidade tem internações vindas de duas fontes no
    banco (a contagem em dobro de Rio Claro). O Escudo já usa uma
    fonte só; o aviso diz que o banco precisa ser recarregado."""
    return [linha[0] for linha in conexao.execute(SQL_DUPLICIDADE, (municipio,)).fetchall()]


def confiabilidade(serie, cancer, duplicados=()):
    """Lista de (nível, texto). nível: 'atencao' ou 'info'."""
    mun = serie_doenca(serie, cancer)
    avisos = []
    if cancer in duplicados:
        avisos.append(("atencao", "O banco deste computador ainda tem estas internações em duplicidade (arquivo "
                                  "da cidade + arquivo estadual). Os números da tela já estão certos: o Escudo "
                                  "usa só o estadual. Para o aviso sumir, recarregue os dados: "
                                  "py etl\\carga_todas_bases.py"))
    incompletos = anos_incompletos(serie)
    if incompletos:
        avisos.append(("atencao", "Anos com meses que o DATASUS não oferece: "
                       + ", ".join(f"{a} ({m} de 12)" for a, m in sorted(incompletos.items()))
                       + ". Para comparar anos, o Escudo usa a média dos meses disponíveis × 12; "
                         "os totais do período são os registrados."))
    elif "meses" in serie and serie["meses"].isna().all():
        avisos.append(("atencao", "O banco deste computador foi carregado sem o mês das internações: o Escudo "
                                  "não consegue corrigir os anos com meses faltando na fonte. Recarregue: "
                                  "py etl\\carga_todas_bases.py"))
    ano_fim = int(serie["ano"].max())
    fora, total = ano_atipico_no_estado(serie, ano_fim)
    if total and fora >= total / 2:
        avisos.append(("atencao", f"{ano_fim} está em investigação: {fora} dos {total} cânceres ficaram muito acima "
                                  f"da tendência ao mesmo tempo no Estado. Isso costuma vir do registro (por "
                                  f"exemplo, anos anteriores com meses faltando na fonte), não do adoecimento."))
    if mun["internacoes"].mean() < MEDIA_PEQUENA:
        avisos.append(("atencao", f"Números pequenos: média de {formatar_numero(mun['internacoes'].mean(), 1)} "
                                  f"internações por ano. Variações podem ser acaso."))
    if registrado(mun, "obitos").sum() < 10:
        avisos.append(("info", "Menos de 10 óbitos no período: a letalidade é pouco estável."))
    anos_com_dado = int((mun["internacoes"] > 0).sum())
    if anos_com_dado < 8:
        avisos.append(("info", f"Só {anos_com_dado} dos {len(mun)} anos têm internações: série curta para tendência."))
    avisos.append(("info", "Sem população por município no banco: comparações são de ritmo, não de taxa "
                           "por 100 mil mulheres."))
    return avisos


# =====================================
# INVESTIGAÇÃO
# =====================================

def anos_fora_todos(serie, grupo=GRUPO_MUNICIPIO):
    """Todos os anos fora do padrão, de todos os cânceres, numa
    tabela só -- para quem quer procurar, não só olhar um câncer."""
    partes = []
    for cancer in serie["tipo_cancer"].unique():
        fora = anos_fora_do_padrao(serie_doenca(serie, cancer, grupo))
        if not fora.empty:
            fora = fora.copy()
            fora.insert(0, "doenca", nome_doenca(cancer))
            fora["diferenca_pct"] = [(_razao(o - e, e) * 100 if e else float("nan"))
                                     for o, e in zip(fora["observado"], fora["esperado"])]
            partes.append(fora)
    if not partes:
        return pd.DataFrame(columns=["doenca", "ano", "observado", "esperado", "direcao",
                                     "numeros_pequenos", "diferenca_pct"])
    return pd.concat(partes, ignore_index=True).sort_values(["ano", "doenca"]).reset_index(drop=True)


def quando_aparece(serie):
    """Para cada câncer: primeiro ano com internação, ano de pico,
    em quantos anos aparece (persistência) e o ritmo. Responde
    "em que anos as doenças aparecem" nos seus vários sentidos."""
    linhas = []
    for cancer in resumo_doencas(serie)["tipo_cancer"]:
        mun = serie_doenca(serie, cancer)
        com = mun[mun["internacoes"] > 0]
        anos_com, total = len(com), len(mun)
        pico = mun.loc[mun["internacoes"].idxmax()]
        persistencia = ("todos os anos" if anos_com == total else
                        "quase todos os anos" if anos_com >= total * 0.75 else "episódica")
        linhas.append({
            "doenca": nome_doenca(cancer),
            "primeiro_ano": int(com["ano"].min()) if anos_com else None,
            "anos_com_internacao": f"{anos_com} de {total}",
            "persistencia": persistencia,
            "ano_de_pico": int(pico["ano"]),
            "internacoes_no_pico": int(pico["internacoes"]),
            "ritmo_anual_pct": round(ritmo_anual_pct(mun), 1),
        })
    return pd.DataFrame(linhas)


def tabela_aparece_para_tela(aparece, ano_inicio=None):
    """A tabela de `quando_aparece` em linguagem simples, do câncer que mais
    cresce para o que menos cresce. Uma coluna "Observação" só entra quando
    algum câncer NÃO apareceu em todos os anos (ou só começou depois), e só
    fica preenchida para ele: colunas iguais em todas as linhas não dizem nada."""
    t = aparece.sort_values("ritmo_anual_pct", ascending=False)
    tabela = pd.DataFrame({
        "Câncer": t["doenca"].values,
        "Crescimento por ano": [f"{'+' if v > 0 else ''}{formatar_numero(v, 1)}%" for v in t["ritmo_anual_pct"]],
        "Ano com mais internações": t["ano_de_pico"].values,
        "Internações naquele ano": [formatar_numero(v) for v in t["internacoes_no_pico"]],
    })
    base = int(ano_inicio) if ano_inicio else int(t["primeiro_ano"].min())  # 1º ano da série
    observacoes = []
    for r in t.itertuples():
        partes = []
        if r.persistencia != "todos os anos":
            partes.append(f"só em {r.anos_com_internacao} anos")
        if r.primeiro_ano and int(r.primeiro_ano) > base:
            partes.append(f"desde {int(r.primeiro_ano)}")
        observacoes.append(", ".join(partes))
    if any(observacoes):  # só aparece quando algum câncer foge do normal
        tabela["Observação"] = observacoes
    return tabela


def leitura_aparece(aparece, incompletos=None, ano_fim=None, ano_inicio=None):
    """Frases da tabela "qual câncer cresce mais rápido e quando foi o ponto mais alto".
    Descreve; o ritmo não é previsão e não explica causa."""
    if aparece.empty:
        return ["Sem internações para mostrar."]
    t = aparece.sort_values("ritmo_anual_pct", ascending=False)
    rapido, lento = t.iloc[0], t.iloc[-1]
    frases = []
    if len(t) > 1:
        frases.append(f"{rapido['doenca']} é o que mais cresce ({'+' if rapido['ritmo_anual_pct'] > 0 else ''}"
                      f"{formatar_numero(rapido['ritmo_anual_pct'], 1)}% ao ano) e {lento['doenca']} é o que menos "
                      f"cresce ({'+' if lento['ritmo_anual_pct'] > 0 else ''}{formatar_numero(lento['ritmo_anual_pct'], 1)}% ao ano).")
    caindo = list(t[t["ritmo_anual_pct"] < 0]["doenca"])
    if caindo:
        frases.append("Com tendência de queda: " + ", ".join(caindo) + ".")
    ultimo = int(ano_fim) if ano_fim else int(max(t["ano_de_pico"]))
    recentes = int((t["ano_de_pico"] >= ultimo - 1).sum())
    plural = "cânceres" if len(t) > 1 else "câncer"
    if recentes == 0:
        frases.append(f"Nenhum câncer teve o ano com mais internações em {ultimo - 1} ou {ultimo}.")
    else:
        frases.append(f"Em {recentes} de {len(t)} {plural} o ano com mais internações foi {ultimo - 1} ou {ultimo}"
                      + (": ainda estão no ponto mais alto." if recentes == len(t) and len(t) > 1
                         else ": ainda está no ponto mais alto." if recentes == len(t) else "."))
    raros = t[t["persistencia"] != "todos os anos"]
    base = int(ano_inicio) if ano_inicio else int(t["primeiro_ano"].min())
    if raros.empty:
        frases.append("Todos os cânceres tiveram internações em todos os anos do período.")
    else:
        frases.append("Poucos casos por ano, leia com cuidado: " + "; ".join(
            f"{r.doenca} teve internações em {r.anos_com_internacao.replace(' de ', ' dos ')} anos"
            + (f", desde {int(r.primeiro_ano)}" if int(r.primeiro_ano) > base else "")
            for r in raros.itertuples()) + ".")
    frases.append("Crescimento por ano = quanto as internações sobem (ou caem) em média a cada ano, pela tendência "
                  "do período, em % da média. Não é previsão.")
    if incompletos:
        frases.append("Nos anos em que a fonte não tem todos os meses, o número é estimado para 12 meses "
                      "(média mensal x 12).")
    return frases


# =====================================
# COMPARAR CIDADES (sem população: proporções e médias)
# =====================================
#
# Número absoluto de internações não compara cidades (a maior tem mais
# mulheres). Enquanto a população do IBGE não está no banco, a comparação usa
# o que não depende do tamanho: parcela de cada câncer, letalidade hospitalar,
# permanência média e ritmo de crescimento. Descreve diferenças; não explica.

SQL_PORTE = ("SELECT municipio, COUNT(*) FROM internacoes "
             "WHERE origem = ? AND municipio <> 'OUTRO_ESTADO' GROUP BY municipio")


def porte_das_cidades(conexao, uf_referencia="SP"):
    """{cidade: internações no período}, só para sugerir uma cidade de porte parecido."""
    try:
        return {m: int(n) for m, n in conexao.execute(SQL_PORTE, (uf_referencia,)).fetchall()}
    except Exception:
        return {}


def cidades_parecidas(porte, origem, n=5):
    """As n cidades com número de internações mais próximo (em proporção), sem a própria."""
    base = porte.get(origem)
    if not base:
        return []
    outras = [(o, v) for o, v in porte.items() if o != origem and v > 0]
    outras.sort(key=lambda par: abs(math.log(par[1] / base)))
    return [o for o, _ in outras[:n]]


def perfil_cidade(serie):
    """Os indicadores da cidade que não dependem do tamanho, ou None sem internações."""
    resumo = resumo_doencas(serie)
    if resumo.empty:
        return None
    n = float(resumo["internacoes"].sum())
    por_ano = serie[serie["grupo"] == GRUPO_MUNICIPIO].groupby("ano", as_index=False)["internacoes"].sum()
    mix = resumo[["tipo_cancer", "doenca", "internacoes"]].copy()
    mix["pct"] = 100.0 * mix["internacoes"] / n
    return {
        "internacoes": int(n),
        "letalidade": 100.0 * float(resumo["obitos"].sum()) / n,
        "permanencia": float(resumo["dias_permanencia"].sum()) / n,
        "ritmo": float(ritmo_anual_pct(por_ano)),
        "mix": mix,
        "principal": mix.iloc[0]["doenca"], "pct_principal": float(mix.iloc[0]["pct"]),
        "poucos_casos": bool(por_ano["internacoes"].mean() < MEDIA_PEQUENA),
    }


def tabela_comparacao(a, b, nome_a, nome_b):
    """Uma linha por indicador, uma coluna por cidade."""
    def sinal(v):
        return f"{'+' if v > 0 else ''}{formatar_numero(v, 1)}%"
    linhas = [
        ("Câncer com mais internações", f"{a['principal']} ({formatar_numero(a['pct_principal'], 1)}%)",
         f"{b['principal']} ({formatar_numero(b['pct_principal'], 1)}%)"),
        ("Letalidade hospitalar (óbitos ÷ internações)", f"{formatar_numero(a['letalidade'], 1)}%",
         f"{formatar_numero(b['letalidade'], 1)}%"),
        ("Permanência média por internação", f"{formatar_numero(a['permanencia'], 1)} dias",
         f"{formatar_numero(b['permanencia'], 1)} dias"),
        ("Crescimento das internações por ano", sinal(a["ritmo"]), sinal(b["ritmo"])),
        ("Internações no período (não compara tamanhos)", formatar_numero(a["internacoes"]),
         formatar_numero(b["internacoes"])),
    ]
    return pd.DataFrame(linhas, columns=["Indicador", nome_a, nome_b])


def mix_comparacao(a, b, nome_a, nome_b):
    """Parcela de cada câncer nas internações de cada cidade (0 onde não há)."""
    codigos = list(dict.fromkeys(list(a["mix"]["tipo_cancer"]) + list(b["mix"]["tipo_cancer"])))
    linhas = []
    for codigo in codigos:
        for nome, p in ((nome_a, a), (nome_b, b)):
            achada = p["mix"][p["mix"]["tipo_cancer"] == codigo]
            linhas.append({"tipo_cancer": codigo, "doenca": nome_doenca(codigo), "cidade": nome,
                           "pct": float(achada["pct"].iloc[0]) if not achada.empty else 0.0})
    return pd.DataFrame(linhas)


def leitura_comparacao(a, b, nome_a, nome_b):
    """Frases da comparação. Descreve as diferenças; nunca atribui causa."""
    frases = [f"Sem a população de cada cidade o tamanho não é comparável: {nome_a} teve "
              f"{formatar_numero(a['internacoes'])} internações no período e {nome_b}, "
              f"{formatar_numero(b['internacoes'])}. Por isso a comparação usa proporções e médias."]
    dif = a["letalidade"] - b["letalidade"]
    if abs(dif) < 0.5:
        frases.append(f"A letalidade hospitalar é parecida: {formatar_numero(a['letalidade'], 1)}% em {nome_a} e "
                      f"{formatar_numero(b['letalidade'], 1)}% em {nome_b}.")
    else:
        maior, menor, pm, pn = ((nome_a, nome_b, a, b) if dif > 0 else (nome_b, nome_a, b, a))
        frases.append(f"A letalidade hospitalar é maior em {maior} ({formatar_numero(pm['letalidade'], 1)}%) do que em "
                      f"{menor} ({formatar_numero(pn['letalidade'], 1)}%).")
    dif = a["permanencia"] - b["permanencia"]
    if abs(dif) < 0.3:
        frases.append(f"A permanência média é parecida: {formatar_numero(a['permanencia'], 1)} e "
                      f"{formatar_numero(b['permanencia'], 1)} dias.")
    else:
        maior, menor, pm, pn = ((nome_a, nome_b, a, b) if dif > 0 else (nome_b, nome_a, b, a))
        frases.append(f"A permanência média é maior em {maior} ({formatar_numero(pm['permanencia'], 1)} dias) do que em "
                      f"{menor} ({formatar_numero(pn['permanencia'], 1)}).")
    if a["principal"] == b["principal"]:
        frases.append(f"Nas duas cidades o câncer com mais internações é {a['principal'].lower()} "
                      f"({formatar_numero(a['pct_principal'], 1)}% e {formatar_numero(b['pct_principal'], 1)}%).")
    else:
        frases.append(f"O câncer com mais internações é {a['principal'].lower()} em {nome_a} e "
                      f"{b['principal'].lower()} em {nome_b}.")
    frases.append(f"As internações crescem {formatar_numero(a['ritmo'], 1)}% ao ano em {nome_a} e "
                  f"{formatar_numero(b['ritmo'], 1)}% em {nome_b}.")
    pequenas = [n for n, p in ((nome_a, a), (nome_b, b)) if p["poucos_casos"]]
    if pequenas:
        frases.append(f"{' e '.join(pequenas)} tem poucas internações por ano: diferenças pequenas podem ser acaso.")
    frases.append("Descreve as diferenças; não explica o motivo delas. Conta internações, não pessoas.")
    return frases


# Faixas escolhidas pelas diretrizes: 50-69 é a faixa do rastreamento
# de câncer de mama recomendado pelo INCA.
FAIXAS = [("até 39 anos", 0, 39), ("40 a 49", 40, 49), ("50 a 69", 50, 69), ("70 ou mais", 70, 200)]

SQL_FAIXAS = """
SELECT tipo_cancer, origem, ano,
       CASE WHEN idade < 40 THEN 'até 39 anos'
            WHEN idade < 50 THEN '40 a 49'
            WHEN idade < 70 THEN '50 a 69'
            ELSE '70 ou mais' END AS faixa,
       COUNT(*) AS internacoes
FROM internacoes
WHERE municipio = ? AND idade IS NOT NULL
GROUP BY tipo_cancer, origem, ano, faixa
"""


def carregar_faixas(conexao, municipio, uf_referencia="SP"):
    """Internações por câncer x ano x faixa etária, com a mesma regra
    de uma fonte por cidade (não conta Rio Claro em dobro)."""
    dados = pd.read_sql(SQL_FAIXAS, conexao, params=(municipio,))
    if dados.empty:
        return dados.drop(columns="origem")
    return escolher_uma_fonte(dados, uf_referencia).drop(columns="origem")


def comparar_faixas(faixas, cancer):
    """Distribuição por faixa etária na primeira e na segunda metade
    do período, para responder "a idade das internações mudou?"."""
    dados = faixas[faixas["tipo_cancer"] == cancer]
    if dados.empty:
        return pd.DataFrame(columns=["faixa", "periodo", "internacoes", "pct"]), None
    anos = sorted(dados["ano"].unique())
    meio = anos[len(anos) // 2]
    periodos = {f"{anos[0]}–{meio - 1}": dados[dados["ano"] < meio],
                f"{meio}–{anos[-1]}": dados[dados["ano"] >= meio]}
    linhas = []
    for periodo, parte in periodos.items():
        total = parte["internacoes"].sum()
        for faixa, _, _ in FAIXAS:
            n = parte[parte["faixa"] == faixa]["internacoes"].sum()
            linhas.append({"faixa": faixa, "periodo": periodo, "internacoes": int(n),
                           "pct": _razao(n, total) * 100})
    tabela = pd.DataFrame(linhas)
    return tabela, list(periodos)


def leitura_faixas(tabela, periodos):
    """A faixa que mais mudou de participação entre os dois períodos."""
    if tabela.empty or periodos is None:
        return []
    antes = tabela[tabela["periodo"] == periodos[0]].set_index("faixa")["pct"]
    depois = tabela[tabela["periodo"] == periodos[1]].set_index("faixa")["pct"]
    variacao = (depois - antes).dropna()
    faixa = variacao.abs().idxmax()
    total = tabela["internacoes"].sum()
    frases = []
    if abs(variacao[faixa]) >= 5:
        frases.append(f"A faixa de {faixa} passou de {formatar_numero(antes[faixa], 1)}% para "
                      f"{formatar_numero(depois[faixa], 1)}% das internações entre {periodos[0]} e {periodos[1]}.")
    else:
        frases.append("A distribuição por idade ficou parecida entre os dois períodos "
                      "(nenhuma faixa mudou 5 pontos ou mais).")
    if total < 60:
        frases.append("Poucas internações para dividir em faixas: leia como indício, não como conclusão.")
    return frases


# =====================================
# PLANEJAMENTO: evidências, nunca valor de orçamento
# =====================================

# Linhas de ação conhecidas (diretrizes do INCA). Possibilidades para a
# discussão da gestão, não recomendação de gasto.
LINHAS_DE_ACAO = {
    "MAMA": "rastreamento recomendado: mamografia de 50 a 69 anos",
    "COLO_UTERO": "rastreamento recomendado (exame preventivo / DNA-HPV) e vacina contra HPV",
    "COLORRETAL": "rastreamento possível: pesquisa de sangue oculto nas fezes",
    "PELE_NAO_MELANOMA": "prevenção por fotoproteção e exame de lesões na atenção básica",
    "PULMAO": "prevenção pelo controle do tabagismo",
}


def pressao_projetada(serie, cancer, horizonte=3):
    """Se a tendência continuar: internações, dias de internação e
    valor hospitalar registrado no último ano do horizonte, cada um
    com faixa e com o resultado do teste de acerto. Óbitos não são
    projetados: são poucos por ano e a reta seria enganosa."""
    mun = serie_doenca(serie, cancer)
    resultado = {}
    for coluna in ("internacoes", "dias_permanencia", "valor_total"):
        proj = projetar(mun, horizonte, coluna).iloc[-1]
        teste = testar_projecao(mun, coluna=coluna)
        resultado[coluna] = {
            "ano": int(proj["ano"]),
            "atual": float(mun[coluna].iloc[-1]),
            "previsto": float(proj[coluna]),
            "minimo": float(proj["minimo"]),
            "maximo": float(proj["maximo"]),
            "tendencia_acerta_mais": bool(teste and teste["erro_tendencia"] <= teste["erro_media"]),
        }
    return resultado


def evidencias_planejamento(serie):
    """Para cada câncer: sinais com o número que os sustenta, a
    pressão projetada e a linha de ação conhecida. Ordenado por
    quantidade de sinais. O Escudo não define quanto investir."""
    ano_fim = int(serie["ano"].max())
    linhas = []
    for cancer in resumo_doencas(serie)["tipo_cancer"]:
        f = ficha_cancer(serie, cancer)
        comp = comparar_com_estado(serie, cancer)
        sinais = []
        if comp["ritmo_municipio"] >= 3:
            sinais.append(f"internações crescem {formatar_numero(comp['ritmo_municipio'], 1)}% ao ano")
        if comp["ritmo_estado"] is not None and comp["ritmo_municipio"] - comp["ritmo_estado"] > 1.5:
            sinais.append(f"crescem mais rápido que no Estado ({formatar_numero(comp['ritmo_estado'], 1)}% ao ano)")
        if f["obitos"] >= 5 and f["letalidade"] > f["letalidade_estado"] * 1.2:
            sinais.append(f"letalidade hospitalar de {formatar_numero(f['letalidade'], 1)}%, acima do Estado "
                          f"({formatar_numero(f['letalidade_estado'], 1)}%)")
        if f["pct_valor"] >= 20:
            sinais.append(f"responde por {formatar_numero(f['pct_valor'], 1)}% do valor hospitalar registrado")
        fora = anos_fora_do_padrao(serie_doenca(serie, cancer))
        recentes = fora[(fora["direcao"] == "acima") & (fora["ano"] >= ano_fim - 2) & (fora["ano"] < ano_fim)]
        for ano in recentes["ano"]:
            sinais.append(f"{ano} ficou acima do esperado")
        linhas.append({
            "tipo_cancer": cancer,
            "doenca": nome_doenca(cancer),
            "sinais": sinais,
            "crescimento": comp["ritmo_municipio"],
            "letalidade_relativa": _razao(f["letalidade"], f["letalidade_estado"]) if f["obitos"] >= 5 else None,
            "internacoes": f["internacoes"],
            "pressao": pressao_projetada(serie, cancer),
            "linha_de_acao": LINHAS_DE_ACAO.get(cancer),
        })
    return sorted(linhas, key=lambda l: -len(l["sinais"]))


# =====================================
# RADAR DO FUTURO: onde podemos ter problema?
# =====================================

NIVEIS_RADAR = ("alerta", "observar", "estavel")


def radar_futuro(serie, horizonte=3):
    """Se nada mudar, onde a cidade pode ter problema? Para cada câncer
    um nível -- "alerta", "observar" ou "estavel" -- com os sinais que
    o sustentam, a pressão projetada e a confiança.

    alerta   = cresce (>= 3% ao ano) E a tendência passou no teste de
               acerto E pelo menos um agravante: cresce mais rápido que
               o Estado, letalidade acima do Estado, mais dias de leito
               pela frente (>= 10% sobre o nível atual), ou é o câncer
               que mais soma internações até o fim do horizonte
               (volume pesa no planejamento mesmo no ritmo do Estado).
    observar = algum sinal sem o conjunto do alerta, ou números
               pequenos (nunca vira alerta com poucas internações).
    estavel  = nenhum sinal.

    A comparação do futuro é com o NÍVEL DA TENDÊNCIA hoje (a reta no
    último ano), não com o último ano -- a mesma regra do gráfico,
    para não ler um pico como base. "Investimento" aparece como
    capacidade (dias de leito), nunca como orçamento em reais."""
    ano_fim = int(serie["ano"].max())
    canceres = list(resumo_doencas(serie)["tipo_cancer"])

    def a_mais(cancer, coluna="internacoes"):
        """Projeção no fim do horizonte menos o nível da tendência hoje."""
        mun = serie_doenca(serie, cancer)
        hoje = float(tendencia_no_periodo(mun, coluna).iloc[-1][coluna])
        return float(projetar(mun, horizonte, coluna).iloc[-1][coluna]) - hoje, hoje

    maior_volume = max(canceres, key=lambda c: a_mais(c)[0]) if canceres else None
    linhas = []
    for cancer in canceres:
        mun = serie_doenca(serie, cancer)
        f = ficha_cancer(serie, cancer)
        comp = comparar_com_estado(serie, cancer)
        pressao = pressao_projetada(serie, cancer, horizonte)
        teste = testar_projecao(mun)
        confiavel = bool(teste and teste["erro_tendencia"] <= teste["erro_media"])
        pequeno = mun["internacoes"].mean() < MEDIA_PEQUENA

        mais_intern, hoje_intern = a_mais(cancer)
        mais_dias, hoje_dias = a_mais(cancer, "dias_permanencia")

        cresce = comp["ritmo_municipio"] >= 3
        agravantes, sinais = [], []
        if cresce:
            sinais.append(f"internações crescem {formatar_numero(comp['ritmo_municipio'], 1)}% ao ano")
        if comp["ritmo_estado"] is not None and comp["ritmo_municipio"] - comp["ritmo_estado"] > 1.5:
            agravantes.append(f"cresce mais rápido que o Estado ({formatar_numero(comp['ritmo_estado'], 1)}% ao ano)")
        if f["obitos"] >= 5 and f["letalidade"] > f["letalidade_estado"] * 1.2:
            agravantes.append(f"letalidade hospitalar de {formatar_numero(f['letalidade'], 1)}%, acima do Estado "
                              f"({formatar_numero(f['letalidade_estado'], 1)}%)")
        if cancer == maior_volume and mais_intern >= DIFERENCA_MINIMA:
            agravantes.append(f"é o que mais soma internações até {ano_fim + horizonte}: cerca de "
                              f"{formatar_numero(mais_intern)} a mais por ano (hoje, pela tendência, "
                              f"~{formatar_numero(hoje_intern)})")
        if hoje_dias > 0 and mais_dias >= max(0.10 * hoje_dias, DIFERENCA_MINIMA):
            agravantes.append(f"cerca de {formatar_numero(mais_dias)} dias de leito a mais por ano em "
                              f"{ano_fim + horizonte} (hoje, pela tendência, ~{formatar_numero(hoje_dias)})")
        sinais += agravantes

        if cresce and confiavel and agravantes and not pequeno:
            nivel = "alerta"
        elif sinais:
            nivel = "observar"
        else:
            nivel = "estavel"

        cuidados = []
        if pequeno:
            cuidados.append("poucas internações por ano: sinais podem ser acaso")
        if not confiavel:
            cuidados.append("no teste de acerto, a tendência não errou menos que repetir a média")
        ponta = leitura_ponta_projecao(mun, horizonte)

        linhas.append({
            "tipo_cancer": cancer,
            "doenca": nome_doenca(cancer),
            "nivel": nivel,
            "sinais": sinais,
            "cuidados": cuidados,
            "confiavel": confiavel,
            "ano": ano_fim + horizonte,
            "internacoes_hoje": hoje_intern,
            "internacoes_a_mais": mais_intern,
            "dias_hoje": hoje_dias,
            "dias_a_mais": mais_dias,
            "pressao": pressao,
            "ponta": ponta,
            "linha_de_acao": LINHAS_DE_ACAO.get(cancer),
            "crescimento": comp["ritmo_municipio"],
            "letalidade_relativa": _razao(f["letalidade"], f["letalidade_estado"]) if f["obitos"] >= 5 else None,
            "internacoes": f["internacoes"],
        })
    ordem = {n: i for i, n in enumerate(NIVEIS_RADAR)}
    return sorted(linhas, key=lambda l: (ordem[l["nivel"]], -len(l["sinais"]), -l["internacoes"]))



# =====================================
# FLUXO DE PACIENTES: quem vem de outros estados se tratar em SP
# =====================================
#
# Pergunta do gestor: quantas mulheres de outros estados a rede de SP
# atende, de onde vêm, para onde vão em SP, quanto leito ocupam e se
# isso cresce. Vale também para a cidade: quem é atendido nos hospitais
# dela e para onde vão as moradoras.
#
# O que os números significam: contam INTERNAÇÕES (uma mulher pode ter
# várias) e só enxergam hospitais de SP -- quem se trata em outro estado
# não aparece. Descrevem o fluxo; não explicam o motivo dele.

OUTRO_ESTADO = "OUTRO_ESTADO"  # mesmo rótulo da carga (etl/carga_todas_bases.py)

NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}

SQL_FLUXO_FORA = """
SELECT tipo_cancer, ano, uf_residencia, municipio_hospital, cnes,
       COUNT(*) AS internacoes,
       COALESCE(SUM(obito), 0) AS obitos,
       COALESCE(SUM(dias_permanencia), 0) AS dias_permanencia
FROM internacoes
WHERE origem = ? AND municipio = 'OUTRO_ESTADO'
GROUP BY tipo_cancer, ano, uf_residencia, municipio_hospital, cnes
"""

SQL_FLUXO_TOTAL = """
SELECT tipo_cancer, ano,
       COUNT(*) AS internacoes,
       COALESCE(SUM(dias_permanencia), 0) AS dias_permanencia
FROM internacoes
WHERE origem = ?
GROUP BY tipo_cancer, ano
"""

SQL_NOMES_MUNICIPIOS = "SELECT substr(CAST(codigo_ibge AS TEXT), 1, 6), nome FROM municipios"


# Centro aproximado de cada estado (latitude, longitude), só para posicionar
# a bolha no mapa do fluxo: não é fronteira nem medida.
CENTROS_UF = {
    "AC": (-9.0, -70.5), "AL": (-9.6, -36.6), "AM": (-4.2, -64.7), "AP": (1.4, -51.8), "BA": (-12.5, -41.7),
    "CE": (-5.2, -39.3), "DF": (-15.8, -47.8), "ES": (-19.6, -40.7), "GO": (-15.9, -49.6), "MA": (-5.1, -45.3),
    "MG": (-18.5, -44.6), "MS": (-20.5, -54.5), "MT": (-12.9, -55.9), "PA": (-3.9, -52.5), "PB": (-7.1, -36.8),
    "PE": (-8.4, -37.9), "PI": (-7.7, -42.7), "PR": (-24.6, -51.6), "RJ": (-22.2, -42.7), "RN": (-5.8, -36.6),
    "RO": (-10.9, -62.8), "RR": (2.1, -61.4), "RS": (-29.7, -53.2), "SC": (-27.2, -50.5), "SE": (-10.6, -37.4),
    "SP": (-22.3, -48.7), "TO": (-10.2, -48.3),
}


def pontos_mapa_fluxo(resumo):
    """Uma linha por estado de origem, com a posição no mapa. Estado sem
    posição conhecida fica de fora (e é contado em `sem_posicao`)."""
    ufs = resumo["ufs"]
    achados = ufs[ufs["uf"].isin(CENTROS_UF)].copy()
    achados["lat"] = [CENTROS_UF[u][0] for u in achados["uf"]]
    achados["lon"] = [CENTROS_UF[u][1] for u in achados["uf"]]
    return achados.reset_index(drop=True), int(ufs.loc[~ufs["uf"].isin(CENTROS_UF), "internacoes"].sum())


def nome_uf(sigla):
    return NOMES_UF.get(sigla, str(sigla))


def _pct(parte, todo):
    return 100.0 * parte / todo if todo else 0.0


def _banco_tem_fluxo(conexao):
    try:
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(internacoes)")}
    except Exception:
        return False
    return {"uf_residencia", "municipio_hospital"} <= colunas


def _nomes_municipios(conexao):
    try:
        return {str(c): str(n) for c, n in conexao.execute(SQL_NOMES_MUNICIPIOS).fetchall()}
    except Exception:
        return {}


def _nomes_hospitais(conexao):
    """CNES (7 dígitos) -> nome, da tabela `hospitais` (etl/criar_tabela_hospitais.py).
    Vazio se o banco ainda não tem a tabela: o painel então mostra o número."""
    try:
        return {str(c).strip().zfill(7): str(n) for c, n in conexao.execute(
            "SELECT cnes, nome FROM hospitais WHERE nome IS NOT NULL AND TRIM(nome) <> ''").fetchall()}
    except Exception:
        return {}


def nome_do_hospital_municipio(nomes, codigo6):
    return nomes.get(str(codigo6), f"município {codigo6}")


def carregar_fluxo(conexao, uf_referencia="SP"):
    """Dados do fluxo de mulheres de outros estados atendidas em SP, ou
    None se o banco foi carregado antes do fluxo (sem município do
    hospital) ou não tem nenhuma mulher de fora."""
    if not _banco_tem_fluxo(conexao):
        return None
    try:
        fora = pd.read_sql(SQL_FLUXO_FORA, conexao, params=(uf_referencia,))
        total = pd.read_sql(SQL_FLUXO_TOTAL, conexao, params=(uf_referencia,))
    except Exception:
        return None
    if fora.empty or fora["municipio_hospital"].isna().all():
        return None
    fora["uf_residencia"] = fora["uf_residencia"].fillna("?")
    fora["municipio_hospital"] = fora["municipio_hospital"].fillna("?")
    return {"fora": fora, "total": total, "nomes": _nomes_municipios(conexao),
            "hospitais": _nomes_hospitais(conexao),
            "meses": meses_por_ano(conexao, uf_referencia)}


def _filtrar_cancer(fluxo, cancer):
    fora, total = fluxo["fora"], fluxo["total"]
    if cancer:
        fora, total = fora[fora["tipo_cancer"] == cancer], total[total["tipo_cancer"] == cancer]
    return fora, total


def resumo_fluxo(fluxo, cancer=None):
    """Totais, estados de origem, municípios de destino e concentração.
    `cancer=None` soma os 7 cânceres."""
    fora, total = _filtrar_cancer(fluxo, cancer)
    n_fora, n_total = int(fora["internacoes"].sum()), int(total["internacoes"].sum())
    dias_fora, dias_total = int(fora["dias_permanencia"].sum()), int(total["dias_permanencia"].sum())

    por_uf = fora.groupby("uf_residencia")["internacoes"].sum().sort_values(ascending=False)
    ufs = pd.DataFrame({
        "uf": por_uf.index,
        "estado": [nome_uf(u) for u in por_uf.index],
        "internacoes": por_uf.values.astype(int),
        "pct": [_pct(v, n_fora) for v in por_uf.values],
    })

    por_destino = fora.groupby("municipio_hospital").agg(
        internacoes=("internacoes", "sum"), hospitais=("cnes", "nunique")
    ).sort_values("internacoes", ascending=False)
    destinos = pd.DataFrame({
        "codigo": por_destino.index,
        "municipio": [nome_do_hospital_municipio(fluxo["nomes"], c) for c in por_destino.index],
        "internacoes": por_destino["internacoes"].values.astype(int),
        "pct": [_pct(v, n_fora) for v in por_destino["internacoes"].values],
        "hospitais": por_destino["hospitais"].values.astype(int),
    })

    concentracao = None
    if not destinos.empty:
        acumulado = destinos["pct"].cumsum()
        concentracao = {
            "destino": destinos.iloc[0]["municipio"],
            "pct": float(destinos.iloc[0]["pct"]),
            "hospitais": int(destinos.iloc[0]["hospitais"]),
            "n_para_90": int((acumulado < 90).sum()) + 1,
        }
    return {
        "internacoes_fora": n_fora, "internacoes_total": n_total, "pct_fora": _pct(n_fora, n_total),
        "dias_fora": dias_fora, "dias_total": dias_total, "pct_dias_fora": _pct(dias_fora, dias_total),
        "permanencia_fora": dias_fora / n_fora if n_fora else 0.0,
        "permanencia_total": dias_total / n_total if n_total else 0.0,
        "n_ufs": len(ufs), "ufs": ufs, "destinos": destinos, "concentracao": concentracao,
    }


# ---------- perfil de um hospital (consulta por hospital, 10/2026) ----------
#
# Pergunta nova: "como é o atendimento de câncer feminino neste hospital?".
# Conta internações de TODAS as pacientes do hospital (de qualquer lugar),
# 7 cânceres somados, pelo número do CNES. Descreve; não ranqueia hospitais:
# a mesma taxa de óbito ou de urgência pode refletir pacientes diferentes
# (casos mais graves, hospital de referência), então não mede qualidade.

SQL_HOSPITAL = """
SELECT cnes, tipo_cancer, ano, municipio_hospital,
       CASE WHEN municipio = 'OUTRO_ESTADO' THEN 'fora'
            WHEN codigo_ibge IS NULL THEN 'sem_info'
            WHEN substr(CAST(codigo_ibge AS TEXT), 1, 6) = municipio_hospital THEN 'cidade'
            ELSE 'outra_cidade' END AS procedencia,
       COUNT(*) AS internacoes,
       COALESCE(SUM(obito), 0) AS obitos,
       COALESCE(SUM(dias_permanencia), 0) AS dias_permanencia,
       COALESCE(SUM(CASE WHEN TRIM(COALESCE(car_int, '')) IN ('02', '2') THEN 1 ELSE 0 END), 0) AS urgencia,
       COALESCE(SUM(CASE WHEN TRIM(COALESCE(car_int, '')) <> '' THEN 1 ELSE 0 END), 0) AS com_carater
FROM internacoes
WHERE origem = ? AND cnes IS NOT NULL AND TRIM(cnes) <> ''
GROUP BY cnes, tipo_cancer, ano, municipio_hospital, procedencia
"""

SQL_HOSPITAL_UF = """
SELECT cnes, tipo_cancer, uf_residencia, COUNT(*) AS internacoes
FROM internacoes
WHERE origem = ? AND municipio = 'OUTRO_ESTADO' AND cnes IS NOT NULL AND TRIM(cnes) <> ''
GROUP BY cnes, tipo_cancer, uf_residencia
"""


def carregar_hospitais(conexao, uf_referencia="SP"):
    """Dados para o perfil por hospital, ou None se o banco é antigo
    (sem CNES / município do hospital) ou não tem nenhum hospital."""
    if not _banco_tem_fluxo(conexao):
        return None
    try:
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(internacoes)")}
        if not {"cnes", "car_int", "codigo_ibge"} <= colunas:
            return None
        base = pd.read_sql(SQL_HOSPITAL, conexao, params=(uf_referencia,))
        ufs = pd.read_sql(SQL_HOSPITAL_UF, conexao, params=(uf_referencia,))
    except Exception:
        return None
    if base.empty:
        return None
    base["cnes"] = base["cnes"].astype(str).str.strip().str.zfill(7)
    ufs["cnes"] = ufs["cnes"].astype(str).str.strip().str.zfill(7)
    base["municipio_hospital"] = base["municipio_hospital"].fillna("?")
    return {"base": base, "ufs": ufs, "nomes": _nomes_municipios(conexao), "hospitais": _nomes_hospitais(conexao),
            "meses": meses_por_ano(conexao, uf_referencia)}


def _da_base(dados, cancer):
    base = dados["base"]
    return base[base["tipo_cancer"] == cancer] if cancer else base


def lista_hospitais(dados, cancer=None):
    """Os hospitais, do que mais interna para o que menos: cnes, hospital
    (nome ou 'CNES 0000000'), municipio, internacoes. `cancer` limita a um
    câncer (só entram os hospitais que internaram esse câncer)."""
    base = _da_base(dados, cancer)
    total = base.groupby("cnes")["internacoes"].sum().sort_values(ascending=False)
    cidade = (base.groupby(["cnes", "municipio_hospital"])["internacoes"].sum().reset_index()
              .sort_values("internacoes", ascending=False).drop_duplicates("cnes").set_index("cnes")["municipio_hospital"])
    nomes = dados.get("hospitais") or {}
    return pd.DataFrame({
        "cnes": list(total.index),
        "hospital": [nomes.get(c, f"CNES {c}") for c in total.index],
        "municipio": [nome_do_hospital_municipio(dados["nomes"], cidade[c]) for c in total.index],
        "internacoes": total.values.astype(int),
    })


def _indicadores_hospital(base):
    n = int(base["internacoes"].sum())
    com_carater = int(base["com_carater"].sum())
    return {
        "internacoes": n,
        "obitos": int(base["obitos"].sum()),
        "pct_obito": _pct(int(base["obitos"].sum()), n),
        "permanencia": float(base["dias_permanencia"].sum()) / n if n else 0.0,
        "pct_urgencia": _pct(int(base["urgencia"].sum()), com_carater) if com_carater else None,
    }


def internacoes_por_ano_hospital(dados, meu):
    """Por ano: internações registradas, na escala de 12 meses (média dos
    meses que a fonte oferece x 12, a mesma regra do resto do Escudo) e por
    procedência (moradoras da cidade do hospital, outras cidades de SP,
    outros estados). Os meses do ano vêm do Estado, não do hospital."""
    meses = dados.get("meses") or {}
    anos = sorted(set(meses) | {int(a) for a in meu["ano"].unique()})
    linhas = []
    for ano in anos:
        do_ano = meu[meu["ano"] == ano]
        m = meses.get(ano)
        fator = MESES_NO_ANO / m if m else 1.0
        por_proc = do_ano.groupby("procedencia")["internacoes"].sum()
        registrado = int(do_ano["internacoes"].sum())
        linhas.append({
            "ano": ano, "meses": m, "registrado": registrado, "ajustado": registrado * fator,
            "cidade": int(por_proc.get("cidade", 0)) * fator,
            "outra_cidade": int(por_proc.get("outra_cidade", 0)) * fator,
            "fora": int(por_proc.get("fora", 0)) * fator,
        })
    return pd.DataFrame(linhas, columns=["ano", "meses", "registrado", "ajustado", "cidade", "outra_cidade", "fora"])


def ficha_hospital(dados, cnes, cancer=None):
    """O perfil de um hospital: de onde vêm as pacientes, quais cânceres,
    urgência, permanência e óbitos na internação, com a referência do
    Estado. `cancer` limita tudo a um câncer, inclusive a referência do
    Estado. None se o hospital não internou (esse câncer)."""
    base = _da_base(dados, cancer)
    meu = base[base["cnes"] == cnes]
    if meu.empty:
        return None
    ind = _indicadores_hospital(meu)
    n = ind["internacoes"]
    por_proc = meu.groupby("procedencia")["internacoes"].sum()
    procedencia = {chave: int(por_proc.get(chave, 0)) for chave in ("cidade", "outra_cidade", "fora", "sem_info")}
    ufs = dados["ufs"]
    if cancer:
        ufs = ufs[ufs["tipo_cancer"] == cancer]
    ufs = ufs[ufs["cnes"] == cnes].groupby("uf_residencia", as_index=False)["internacoes"].sum()
    ufs = ufs.sort_values("internacoes", ascending=False)
    por_cancer = meu.groupby("tipo_cancer")["internacoes"].sum().sort_values(ascending=False)
    lista = lista_hospitais(dados, cancer)
    linha = lista[lista["cnes"] == cnes].iloc[0]
    return {
        "cnes": cnes, "hospital": linha["hospital"], "municipio": linha["municipio"], "tipo_cancer": cancer,
        "tem_nome": cnes in (dados.get("hospitais") or {}),
        **ind,
        "procedencia": procedencia,
        "pct_fora": _pct(procedencia["fora"], n),
        "ufs": [(nome_uf(u), int(v)) for u, v in zip(ufs["uf_residencia"], ufs["internacoes"])],
        "cancer": pd.DataFrame({
            "tipo_cancer": list(por_cancer.index),
            "doenca": [nome_doenca(c) for c in por_cancer.index],
            "internacoes": por_cancer.values.astype(int),
            "pct": [_pct(v, n) for v in por_cancer.values],
        }),
        "estado": _indicadores_hospital(base),
        "por_ano": internacoes_por_ano_hospital(dados, meu),
    }


def leitura_hospital_anos(ficha):
    """Frases do gráfico por ano. Descreve; não explica abertura, fechamento
    ou mudança de volume."""
    anos = ficha["por_ano"]
    com = anos[anos["registrado"] > 0]
    if len(com) < 2:
        return ["Só há um ano com internações registradas: não dá para ver mudança ao longo do tempo."]
    primeiro, ultimo = com.iloc[0], com.iloc[-1]
    pico = com.loc[com["ajustado"].idxmax()]
    frases = [f"Na escala de 12 meses, o hospital registrou {formatar_numero(primeiro['ajustado'])} internações em "
              f"{int(primeiro['ano'])} e {formatar_numero(ultimo['ajustado'])} em {int(ultimo['ano'])}; "
              f"o ponto mais alto foi {formatar_numero(pico['ajustado'])} em {int(pico['ano'])}."]
    if int(primeiro["ano"]) > int(anos["ano"].min()):
        frases.append(f"O primeiro ano com internações registradas foi {int(primeiro['ano'])}.")
    pa, pb = (100 * primeiro["fora"] / primeiro["ajustado"] if primeiro["ajustado"] else 0.0,
              100 * ultimo["fora"] / ultimo["ajustado"] if ultimo["ajustado"] else 0.0)
    if pa or pb:
        frases.append(f"A parcela de mulheres de outros estados foi {formatar_numero(pa, 1)}% em {int(primeiro['ano'])} "
                      f"e {formatar_numero(pb, 1)}% em {int(ultimo['ano'])}.")
    incompletos = [int(a) for a, m in zip(anos["ano"], anos["meses"]) if m and m < MESES_NO_ANO]
    if incompletos:
        quais = (", ".join(str(a) for a in incompletos) if len(incompletos) <= 4
                 else f"{len(incompletos)} dos {len(anos)} anos")
        frases.append("Anos com meses ausentes na fonte (" + quais
                      + ") estão na escala de 12 meses, pela média dos meses disponíveis; o valor registrado aparece "
                      "ao passar o mouse. Ano sem barra não tem internação registrada, o que não prova que não houve atendimento.")
    return frases


def leitura_hospital(ficha):
    """Frases do perfil de um hospital. Só descreve: não ranqueia nem explica."""
    if not ficha:
        return ["Hospital sem internações registradas."]
    n, p = ficha["internacoes"], ficha["procedencia"]
    assunto = cancer_de(ficha["tipo_cancer"]) if ficha.get("tipo_cancer") else "câncer feminino"
    frases = [f"{ficha['hospital']} ({ficha['municipio']}) registrou {formatar_numero(n)} internações por {assunto} "
              f"entre 2013 e 2025."]
    partes = [f"{formatar_numero(_pct(p['cidade'], n), 1)}% de moradoras de {ficha['municipio']}",
              f"{formatar_numero(_pct(p['outra_cidade'], n), 1)}% de outras cidades de SP",
              f"{formatar_numero(ficha['pct_fora'], 1)}% de outros estados"]
    frases.append("Quem foi internada: " + ", ".join(partes[:-1]) + " e " + partes[-1] + ".")
    if ficha["ufs"]:
        frases.append("Os estados que mais enviam para este hospital: "
                      + ", ".join(f"{nome} ({formatar_numero(v)})" for nome, v in ficha["ufs"][:3]) + ".")
    if len(ficha["cancer"]) > 1:
        top = ficha["cancer"].iloc[0]
        frases.append(f"O câncer com mais internações é {top['doenca'].lower()} "
                      f"({formatar_numero(top['pct'], 1)}%).")
    est = ficha["estado"]
    if ficha["pct_urgencia"] is not None and est["pct_urgencia"] is not None:
        frases.append(f"{formatar_numero(ficha['pct_urgencia'], 1)}% das internações foram de urgência "
                      f"(no Estado, {formatar_numero(est['pct_urgencia'], 1)}%) e a permanência média foi de "
                      f"{formatar_numero(ficha['permanencia'], 1)} dias (no Estado, "
                      f"{formatar_numero(est['permanencia'], 1)}).")
    else:
        frases.append(f"A permanência média foi de {formatar_numero(ficha['permanencia'], 1)} dias "
                      f"(no Estado, {formatar_numero(est['permanencia'], 1)}).")
    if n < 100:
        frases.append(f"Com {formatar_numero(n)} internações no período, os percentuais variam muito de um ano "
                      "para outro: leia com cautela.")
    frases.append("Não serve para comparar hospitais nem medir qualidade: hospitais de referência recebem pacientes "
                  "em situações diferentes. Conta internações, não pessoas.")
    return frases


def hospitais_fluxo(fluxo, cancer=None, n=10):
    """Os hospitais de SP que mais atendem mulheres de outros estados.
    `hospital` é o nome (tabela `hospitais`) ou 'CNES 0000000' se o nome
    ainda não foi carregado; `tem_nome` diz qual dos dois."""
    colunas = ["cnes", "hospital", "tem_nome", "municipio", "internacoes", "pct"]
    fora, _ = _filtrar_cancer(fluxo, cancer)
    n_fora = int(fora["internacoes"].sum())
    com = fora[fora["cnes"].notna() & (fora["cnes"].astype(str).str.strip() != "")]
    if com.empty:
        return pd.DataFrame(columns=colunas)
    total = com.groupby("cnes")["internacoes"].sum().sort_values(ascending=False)
    topo = total.head(n)
    cidade = (com.groupby(["cnes", "municipio_hospital"])["internacoes"].sum().reset_index()
              .sort_values("internacoes", ascending=False).drop_duplicates("cnes").set_index("cnes")["municipio_hospital"])
    nomes = fluxo.get("hospitais") or {}
    codigos = [str(c).strip().zfill(7) for c in topo.index]
    return pd.DataFrame({
        "cnes": codigos,
        "hospital": [nomes.get(c, f"CNES {c}") for c in codigos],
        "tem_nome": [c in nomes for c in codigos],
        "municipio": [nome_do_hospital_municipio(fluxo["nomes"], cidade[c]) for c in topo.index],
        "internacoes": topo.values.astype(int),
        "pct": [_pct(v, n_fora) for v in topo.values],
    })


def leitura_hospitais(fluxo, hospitais, cancer=None):
    """Frases sobre os hospitais que mais atendem mulheres de fora. Só descreve."""
    if hospitais is None or hospitais.empty:
        return ["As internações de mulheres de outros estados não trazem o número do hospital (CNES)."]
    primeiro = hospitais.iloc[0]
    frases = [f"{primeiro['hospital']} ({primeiro['municipio']}) registrou {formatar_numero(primeiro['internacoes'])} "
              f"internações de mulheres de outros estados: {formatar_numero(primeiro['pct'], 1)}% das internações de fora."]
    if len(hospitais) >= 3:
        frases.append(f"Os 3 hospitais que mais atendem reúnem "
                      f"{formatar_numero(hospitais['pct'].head(3).sum(), 1)}% das internações de fora.")
    fora, _ = _filtrar_cancer(fluxo, cancer)
    n_hosp = int(fora["cnes"].dropna().nunique())
    if n_hosp:
        frases.append(f"No total, {formatar_numero(n_hosp)} hospital{'is' if n_hosp != 1 else ''} de SP "
                      f"atendeu{'ram' if n_hosp != 1 else ''} mulheres de outros estados.")
    if not hospitais["tem_nome"].all():
        frases.append("Onde aparece só o número do CNES, o nome ainda não foi carregado "
                      "(rode py etl\\criar_tabela_hospitais.py).")
    frases.append("Conta internações, não pessoas. Descreve onde foram atendidas; não explica o motivo.")
    return frases


def evolucao_fluxo(fluxo, cancer=None):
    """Por ano: internações de fora, total e a parcela de fora. A parcela
    compara os MESMOS meses (numerador e denominador), então um ano com
    meses ausentes na fonte não a distorce; `fora_ajustado` põe o número
    absoluto na escala de 12 meses, como o resto do Escudo."""
    fora, total = _filtrar_cancer(fluxo, cancer)
    fora_ano = fora.groupby("ano")["internacoes"].sum()
    total_ano = total.groupby("ano")["internacoes"].sum()
    anos = sorted(int(a) for a in total_ano.index)
    meses = fluxo.get("meses") or {}
    linhas = []
    for ano in anos:
        n_fora, n_total = int(fora_ano.get(ano, 0)), int(total_ano.get(ano, 0))
        m = meses.get(ano)
        linhas.append({
            "ano": ano, "fora": n_fora, "total": n_total, "pct_fora": _pct(n_fora, n_total),
            "meses": m, "fora_ajustado": n_fora * MESES_NO_ANO / m if m else float(n_fora),
        })
    return pd.DataFrame(linhas, columns=["ano", "fora", "total", "pct_fora", "meses", "fora_ajustado"])


def ligacoes_fluxo(fluxo, cancer=None, n_ufs=8, n_destinos=6):
    """Ligações estado de origem -> município do hospital, para o gráfico de
    fluxo. O que passa do limite vira "Outros estados" / "Outros municípios"."""
    fora, _ = _filtrar_cancer(fluxo, cancer)
    cruz = fora.groupby(["uf_residencia", "municipio_hospital"])["internacoes"].sum().reset_index()
    top_ufs = list(cruz.groupby("uf_residencia")["internacoes"].sum().nlargest(n_ufs).index)
    top_dest = list(cruz.groupby("municipio_hospital")["internacoes"].sum().nlargest(n_destinos).index)
    cruz["origem"] = [nome_uf(u) if u in top_ufs else "Outros estados" for u in cruz["uf_residencia"]]
    cruz["destino"] = [nome_do_hospital_municipio(fluxo["nomes"], d) if d in top_dest else "Outros municípios de SP"
                       for d in cruz["municipio_hospital"]]
    ligacoes = cruz.groupby(["origem", "destino"], as_index=False)["internacoes"].sum()
    return ligacoes.rename(columns={"internacoes": "valor"}).sort_values("valor", ascending=False,
                                                                       ignore_index=True)


def por_cancer_fluxo(fluxo):
    """Uma linha por câncer: quanto vem de fora, de onde e para onde."""
    linhas = []
    for cancer in sorted(fluxo["total"]["tipo_cancer"].unique()):
        r = resumo_fluxo(fluxo, cancer)
        linhas.append({
            "tipo_cancer": cancer, "doenca": nome_doenca(cancer),
            "internacoes_fora": r["internacoes_fora"], "internacoes_total": r["internacoes_total"],
            "pct_fora": r["pct_fora"],
            "estado_principal": r["ufs"].iloc[0]["estado"] if not r["ufs"].empty else "-",
            "destino_principal": r["destinos"].iloc[0]["municipio"] if not r["destinos"].empty else "-",
        })
    return pd.DataFrame(linhas).sort_values("pct_fora", ascending=False, ignore_index=True)


def leitura_fluxo(resumo, evolucao):
    """Frases do que o fluxo mostra. Só descreve: nunca atribui causa."""
    n, t = resumo["internacoes_fora"], resumo["internacoes_total"]
    if n == 0:
        return ["Nenhuma internação de mulher de outro estado foi registrada nesta seleção."]
    frases = [f"Em hospitais de SP foram registradas {formatar_numero(n)} internações de mulheres que moram em "
              f"outros estados: {formatar_numero(resumo['pct_fora'], 1)}% das {formatar_numero(t)} internações."]
    ufs = resumo["ufs"].head(3)
    if len(ufs) >= 2:
        partes = [f"{r.estado} ({formatar_numero(r.pct, 1)}%)" for r in ufs.itertuples()]
        frases.append("Os estados que mais enviam: " + ", ".join(partes[:-1]) + f" e {partes[-1]}"
                      + f", entre {resumo['n_ufs']} estados de origem.")
    elif len(ufs) == 1:
        frases.append(f"Todas vêm de {ufs.iloc[0]['estado']}.")
    c = resumo["concentracao"]
    if c:
        hosp = f" (em {c['hospitais']} hospital{'is' if c['hospitais'] != 1 else ''})" if c["hospitais"] else ""
        frases.append(f"{formatar_numero(c['pct'], 1)}% foram atendidas em {c['destino']}{hosp}; "
                      f"{c['n_para_90']} município{'s' if c['n_para_90'] != 1 else ''} reúne"
                      f"{'m' if c['n_para_90'] != 1 else ''} 90% delas.")
    if resumo["dias_fora"]:
        frases.append(f"Ocuparam {formatar_numero(resumo['dias_fora'])} dias de leito "
                      f"({formatar_numero(resumo['pct_dias_fora'], 1)}% do total), com média de "
                      f"{formatar_numero(resumo['permanencia_fora'], 1)} dias por internação "
                      f"(todas as internações: {formatar_numero(resumo['permanencia_total'], 1)}).")
    if evolucao is not None and len(evolucao) >= 2:
        a, b = evolucao.iloc[0], evolucao.iloc[-1]
        frases.append(f"A parcela de mulheres de fora foi {formatar_numero(a['pct_fora'], 1)}% em {int(a['ano'])} "
                      f"e {formatar_numero(b['pct_fora'], 1)}% em {int(b['ano'])}.")
    frases.append("Conta internações, não pessoas, e só enxerga hospitais de SP: quem se trata em outro estado "
                  "não aparece. Descreve o fluxo; não explica o motivo dele.")
    return frases


def leitura_evolucao_fluxo(evolucao):
    """Frases do gráfico da parcela de mulheres de fora ao longo dos anos."""
    if evolucao is None or len(evolucao) < 2:
        return ["Poucos anos para comparar."]
    primeiro, ultimo = evolucao.iloc[0], evolucao.iloc[-1]
    pico = evolucao.loc[evolucao["pct_fora"].idxmax()]
    frases = [f"A parcela foi {formatar_numero(primeiro['pct_fora'], 1)}% em {int(primeiro['ano'])} e "
              f"{formatar_numero(ultimo['pct_fora'], 1)}% em {int(ultimo['ano'])}; "
              f"o ponto mais alto foi {formatar_numero(pico['pct_fora'], 1)}% em {int(pico['ano'])}."]
    incompletos = [int(a) for a, m in zip(evolucao["ano"], evolucao["meses"]) if m and m < MESES_NO_ANO]
    if incompletos:
        frases.append("A parcela compara os mesmos meses de cada ano (os de fora e o total), então os anos com "
                      "meses ausentes na fonte não a distorcem.")
    return frases


def fluxo_da_cidade(conexao, origem, codigo_ibge, uf_referencia="SP"):
    """Para a cidade escolhida: quem é atendido nos hospitais dela (moradoras,
    outras cidades de SP, outros estados) e onde as moradoras são atendidas.
    None se o banco ainda não guarda o município do hospital."""
    if not _banco_tem_fluxo(conexao):
        return None
    cod6 = str(codigo_ibge)[:6]
    try:
        quem = dict(conexao.execute(
            "SELECT CASE WHEN municipio = ? THEN 'da_cidade' WHEN municipio = 'OUTRO_ESTADO' "
            "THEN 'outros_estados' ELSE 'outras_cidades' END, COUNT(*) FROM internacoes "
            "WHERE origem = ? AND municipio_hospital = ? GROUP BY 1", (origem, uf_referencia, cod6)).fetchall())
        onde = conexao.execute(
            "SELECT municipio_hospital, COUNT(*) FROM internacoes WHERE origem = ? AND municipio = ? "
            "GROUP BY 1 ORDER BY 2 DESC", (uf_referencia, origem)).fetchall()
    except Exception:
        return None
    nomes = _nomes_municipios(conexao)
    com_hospital = [(c, int(n)) for c, n in onde if c is not None]
    moradoras = sum(n for _, n in com_hospital)
    na_cidade = sum(n for c, n in com_hospital if c == cod6)
    destinos = [(nome_do_hospital_municipio(nomes, c), n) for c, n in com_hospital if c != cod6]
    return {
        "atendimentos": sum(quem.values()),
        "da_cidade": int(quem.get("da_cidade", 0)),
        "outras_cidades": int(quem.get("outras_cidades", 0)),
        "outros_estados": int(quem.get("outros_estados", 0)),
        "moradoras": moradoras, "moradoras_na_cidade": na_cidade,
        "moradoras_fora": moradoras - na_cidade, "destinos": destinos[:5],
    }


def leitura_cidade(info, nome_cidade):
    """Frases sobre o fluxo da cidade. Só descreve."""
    if not info or (not info["atendimentos"] and not info["moradoras"]):
        return [f"Não há internações registradas em hospitais de {nome_cidade} nem de moradoras da cidade."]
    frases = []
    a = info["atendimentos"]
    if a:
        frases.append(
            f"Nos hospitais de {nome_cidade} foram registradas {formatar_numero(a)} internações: "
            f"{formatar_numero(_pct(info['da_cidade'], a), 1)}% de moradoras da cidade, "
            f"{formatar_numero(_pct(info['outras_cidades'], a), 1)}% de outras cidades de SP e "
            f"{formatar_numero(_pct(info['outros_estados'], a), 1)}% de outros estados.")
        if not info["outros_estados"]:
            frases.append(f"Nenhuma internação de mulher de outro estado foi registrada em {nome_cidade}: "
                          "elas se concentram em poucos municípios do Estado (veja o gráfico do Estado, acima).")
    else:
        frases.append(f"Nenhuma internação foi registrada em hospitais de {nome_cidade}.")
    m = info["moradoras"]
    if m:
        frases.append(
            f"Das {formatar_numero(m)} internações de moradoras de {nome_cidade}, "
            f"{formatar_numero(_pct(info['moradoras_na_cidade'], m), 1)}% foram na própria cidade e "
            f"{formatar_numero(info['moradoras_fora'])} em hospitais de outras cidades de SP"
            + (": " + ", ".join(f"{nome} ({formatar_numero(n)})" for nome, n in info["destinos"][:3])
               if info["destinos"] else "") + ".")
    saldo = info["outras_cidades"] + info["outros_estados"] - info["moradoras_fora"]
    frases.append(f"Saldo da cidade: {'+' if saldo > 0 else ''}{formatar_numero(saldo)} "
                  f"(internações de quem mora fora, atendidas aqui, menos moradoras atendidas fora). "
                  "Conta internações e só enxerga hospitais de SP.")
    return frases
