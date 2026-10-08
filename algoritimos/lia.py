from dataclasses import dataclass, field

from inteligencia import (
    anos_fora_do_padrao,
    anos_incompletos,
    anos_fora_todos,
    ano_atipico_no_estado,
    cancer_de,
    comparar_com_estado,
    comparar_faixas,
    confiabilidade,
    destaques_cancer,
    ficha_cancer,
    formatar_numero,
    hospitais_fluxo,
    leitura_cidade,
    leitura_faixas,
    leitura_ponta_projecao,
    MEDIA_PEQUENA,
    nome_doenca,
    pressao_projetada,
    radar_futuro,
    resumo_doencas,
    resumo_fluxo,
    serie_doenca,
    testar_projecao,
)

# =====================================
# LIA — a guia do Escudo Feminino (ver docs/LIA.md)
#
# Árvore de conversa com 3 níveis: caminhos -> câncer -> ação. Cada
# nó devolve uma Resposta com a fala, a expressão do rosto, os
# próximos botões, o destino no painel e os números usados ("por
# quê?"). As falas guiadas são DETERMINÍSTICAS: montadas com os
# números de inteligencia.py, sem IA -- rápidas, sem custo e sempre
# iguais para os mesmos dados. Não há caixa de texto livre no painel
# (saiu em 09/2026, decisão do autor: respondia o mesmo que os botões,
# com menos precisão); conversa.py continua fora do painel.
#
# A expressão vem dos dados: "cautelosa" quando a confiabilidade
# pede cuidado, "atenta" quando há sinal, "explicando" no resto.
# =====================================

EXPRESSOES = ("acolhedora", "explicando", "atenta", "cautelosa", "pensativa")


@dataclass
class Resposta:
    fala: str
    expressao: str = "explicando"
    botoes: list = field(default_factory=list)   # [(rótulo, ação)]
    destino: dict = None                         # {"aba":..., "cancer":..., "medida":..., "camadas": {...}}
    numeros: list = field(default_factory=list)  # o "por quê?"


@dataclass
class Contexto:
    serie: object
    cidade: str
    faixas: object = None      # DataFrame de inteligencia.carregar_faixas (opcional)
    duplicados: tuple = ()
    fluxo: object = None          # inteligencia.carregar_fluxo (None: banco antigo, sem o fluxo)
    fluxo_cidade: object = None   # inteligencia.fluxo_da_cidade


# ---------- ações (o que um botão faz) ----------

def caminho(nome):
    return {"tipo": "caminho", "id": nome}


def escolher_cancer(acao_seguinte):
    return {"tipo": "escolher_cancer", "depois": acao_seguinte}


def sobre(cancer, acao):
    return {"tipo": "cancer", "cancer": cancer, "acao": acao}


INICIO = {"tipo": "inicio"}

CAMINHOS = [
    ("O que mais aparece?", "mais_aparece"),
    ("Está aumentando?", "aumentando"),
    ("Onde podemos ter problema?", "atencao"),
    ("Valores hospitalares", "valores"),
    ("Comparar com São Paulo", "estado"),
    ("Mulheres de outros estados", "fluxo"),
    ("Olhar para frente", "futuro"),
    ("Anos fora do padrão", "fora_padrao"),
    ("Os dados estão completos?", "completude"),
    ("Como esses dados funcionam?", "metodo"),
]

ACOES_CANCER = [
    ("Evolução", "evolucao"),
    ("Óbitos", "obitos"),
    ("Valores", "valores"),
    ("Tempo de internação", "tempo"),
    ("Idade", "idade"),
    ("Comparar com SP", "estado"),
    ("Projeção", "projecao"),
    ("Por quê?", "porque"),
]


def _mais(cancer, *acoes):
    """Botões de próximo passo sobre um câncer."""
    rotulos = dict((a, r) for r, a in ACOES_CANCER)
    return [(rotulos[a], sobre(cancer, a)) for a in acoes]


def _canceres(ctx):
    return list(resumo_doencas(ctx.serie)["tipo_cancer"])


def _pequeno(ctx, cancer):
    return serie_doenca(ctx.serie, cancer)["internacoes"].mean() < MEDIA_PEQUENA


def _ano_em_investigacao(ctx):
    ano = int(ctx.serie["ano"].max())
    fora, total = ano_atipico_no_estado(ctx.serie, ano)
    return ano if total and fora >= total / 2 else None


def _nota_meses(ctx):
    """Anos com meses que o DATASUS não oferece (inteligencia.ajustar_meses)."""
    incompletos = anos_incompletos(ctx.serie)
    if not incompletos:
        return ""
    pior = min(incompletos, key=incompletos.get)
    return (f"\n\n*Um cuidado: o DATASUS não oferece todos os meses de {len(incompletos)} anos "
            f"({pior} tem só {incompletos[pior]} de 12). Para comparar os anos, uso a média dos meses "
            f"disponíveis × 12.*")


def _nota_2025(ctx):
    """Cuidados que valem para toda fala que compara anos."""
    ano = _ano_em_investigacao(ctx)
    nota = (f"\n\n*Um cuidado: {ano} está em investigação — vários cânceres saltaram juntos no Estado "
            f"inteiro nesse ano, o que parece vir do registro, não do adoecimento.*") if ano else ""
    return nota + _nota_meses(ctx)


# ---------- nível 0 ----------

def saudacao(ctx):
    return Resposta(
        fala=(f"Olá, eu sou a **Lia**, pesquisadora do Escudo Feminino. Vamos olhar juntas os dados de "
              f"câncer em mulheres de **{ctx.cidade}**? O que você quer descobrir?"),
        expressao="acolhedora",
        botoes=[(r, caminho(c)) for r, c in CAMINHOS],
    )


def menu_cancer(ctx, acao_seguinte):
    rotulo = {"futuro": "olhar para frente"}.get(acao_seguinte, "")
    return Resposta(
        fala=f"Sobre qual câncer você quer {rotulo or 'saber mais'}?",
        expressao="acolhedora",
        botoes=[(nome_doenca(c), sobre(c, "projecao" if acao_seguinte == "futuro" else "menu"))
                for c in _canceres(ctx)],
    )


def menu_do_cancer(ctx, cancer):
    return Resposta(
        fala=f"Vamos olhar o **{cancer_de(cancer)}** em {ctx.cidade}. O que você gostaria de saber?",
        expressao="acolhedora",
        botoes=[(r, sobre(cancer, a)) for r, a in ACOES_CANCER],
        destino={"aba": "Panorama", "cancer": cancer},
    )


# ---------- nível 1: caminhos ----------

def mais_aparece(ctx):
    resumo = resumo_doencas(ctx.serie)
    total = resumo["internacoes"].sum()
    top = resumo.head(3)
    partes = [f"**{l['doenca']}** ({formatar_numero(l['internacoes'])} internações, "
              f"{formatar_numero(l['internacoes'] / total * 100)}%)" for _, l in top.iterrows()]
    primeiro = top.iloc[0]["tipo_cancer"]
    return Resposta(
        fala=(f"De {int(ctx.serie['ano'].min())} a {int(ctx.serie['ano'].max())}, as mulheres de {ctx.cidade} "
              f"tiveram **{formatar_numero(total)} internações** pelos cânceres que acompanho. Os que mais "
              f"aparecem são " + ", ".join(partes[:-1]) + " e " + partes[-1] + "."),
        botoes=[(f"Ver {nome_doenca(primeiro).lower()}", sobre(primeiro, "menu")),
                ("Onde podemos ter problema?", caminho("atencao")),
                ("Valores hospitalares", caminho("valores"))],
        destino={"aba": "Panorama", "cancer": primeiro, "medida": "Internações"},
        numeros=[f"{l['doenca']}: {formatar_numero(l['internacoes'])} internações" for _, l in resumo.iterrows()],
    )


def aumentando(ctx):
    linhas = []
    for c in _canceres(ctx):
        comp = comparar_com_estado(ctx.serie, c)
        linhas.append((comp["ritmo_municipio"], comp["ritmo_estado"] or 0, c))
    linhas.sort(reverse=True)
    crescem = [l for l in linhas if l[0] >= 3]
    mais_que_sp = [nome_doenca(c) for r, e, c in linhas if r - e > 1.5]
    if crescem:
        topo = crescem[0]
        fala = (f"Sim, na maioria dos casos. {len(crescem)} dos {len(linhas)} cânceres crescem pelo menos 3% ao ano. "
                f"O que mais cresce é o **{cancer_de(topo[2])}**: {formatar_numero(topo[0], 1)}% ao ano.")
    else:
        topo = linhas[0]
        fala = "Não há crescimento forte: nenhum câncer cresce 3% ao ano ou mais."
    if mais_que_sp:
        fala += f" Crescem mais rápido que no Estado de SP: {', '.join(mais_que_sp)}."
    pequenos = any(_pequeno(ctx, c) for _, _, c in crescem[:1])
    return Resposta(
        fala=fala + _nota_2025(ctx),
        expressao="cautelosa" if pequenos else ("atenta" if mais_que_sp else "explicando"),
        botoes=_mais(topo[2], "evolucao", "projecao") + [("Comparar com São Paulo", caminho("estado"))],
        destino={"aba": "Evolução", "cancer": topo[2], "camadas": {"ver_estado": True}},
        numeros=[f"{nome_doenca(c)}: {formatar_numero(r, 1)}% ao ano (Estado: {formatar_numero(e, 1)}%)"
                 for r, e, c in linhas],
    )


def atencao(ctx):
    """Onde podemos ter problema? O radar do futuro (inteligencia.radar_futuro)."""
    radar = radar_futuro(ctx.serie)
    alerta = [r for r in radar if r["nivel"] == "alerta"]
    observar = [r for r in radar if r["nivel"] == "observar"]
    ano = radar[0]["ano"] if radar else int(ctx.serie["ano"].max()) + 3
    if not alerta and not observar:
        return Resposta(
            fala=(f"Se nada mudar, não vejo onde {ctx.cidade} possa ter problema até {ano} pelos critérios do "
                  f"Escudo: nenhum câncer mostra sinal de alerta."),
            botoes=[("Está aumentando?", caminho("aumentando")), ("Olhar para frente", caminho("futuro"))],
            destino={"aba": "Planejamento"},
        )
    topo = (alerta or observar)[0]
    if alerta:
        fala = (f"Se nada mudar, é aqui que {ctx.cidade} pode ter problema até {ano}: "
                + ", ".join(f"**{r['doenca']}**" for r in alerta) + ". "
                f"O que mais reúne sinais é o **{cancer_de(topo['tipo_cancer'])}**: " + "; ".join(topo["sinais"]) + ".")
    else:
        fala = (f"Nenhum câncer chega a alerta, mas há sinais a acompanhar até {ano}. O primeiro é o "
                f"**{cancer_de(topo['tipo_cancer'])}**: " + "; ".join(topo["sinais"]) + ".")
    if observar and alerta:
        fala += f"\n\nPara acompanhar: {', '.join(r['doenca'] for r in observar)}."
    if topo["linha_de_acao"]:
        fala += f"\n\nOnde dá para agir antes: {topo['linha_de_acao']} (INCA)."
    fala += ("\n\nEu aponto onde preparar a rede, com as evidências; a decisão de quanto investir é da gestão."
             + _nota_2025(ctx))
    return Resposta(
        fala=fala,
        expressao="atenta",
        botoes=_mais(topo["tipo_cancer"], "porque", "projecao", "tempo"),
        destino={"aba": "Planejamento", "cancer": topo["tipo_cancer"]},
        numeros=[f"{r['doenca']} ({r['nivel']}): " + ("; ".join(r["sinais"]) or "sem sinal") for r in radar],
    )


def valores(ctx):
    resumo = resumo_doencas(ctx.serie)
    total_v, total_i = resumo["valor_total"].sum(), resumo["internacoes"].sum()
    resumo = resumo.assign(pv=resumo["valor_total"] / total_v * 100, pi=resumo["internacoes"] / total_i * 100)
    maior = resumo.sort_values("valor_total", ascending=False).iloc[0]
    desprop = resumo.assign(d=resumo["pv"] - resumo["pi"]).sort_values("d", ascending=False).iloc[0]
    fala = (f"No período, as internações por câncer de mulheres de {ctx.cidade} somaram "
            f"**R$ {formatar_numero(total_v)}** em valores hospitalares registrados no SIH/SUS. "
            f"O maior valor é do **{cancer_de(maior['tipo_cancer'])}** ({formatar_numero(maior['pv'])}% do total).")
    if desprop["pv"] - desprop["pi"] > 3:
        fala += (f" Chama atenção o **{cancer_de(desprop['tipo_cancer'])}**: é {formatar_numero(desprop['pi'])}% "
                 f"das internações, mas {formatar_numero(desprop['pv'])}% do valor.")
    fala += " Isso não é o orçamento do município nem o custo total do tratamento."
    return Resposta(
        fala=fala,
        expressao="explicando",
        botoes=_mais(desprop["tipo_cancer"], "valores", "tempo") + [("Onde podemos ter problema?", caminho("atencao"))],
        destino={"aba": "Panorama", "cancer": desprop["tipo_cancer"], "medida": "Valor hospitalar registrado"},
        numeros=[f"{l['doenca']}: R$ {formatar_numero(l['valor_total'])} ({formatar_numero(l['pv'], 1)}% do valor, "
                 f"{formatar_numero(l['pi'], 1)}% das internações)" for _, l in resumo.iterrows()],
    )


def estado(ctx):
    linhas = []
    for c in _canceres(ctx):
        comp = comparar_com_estado(ctx.serie, c)
        linhas.append((comp["ritmo_municipio"] - (comp["ritmo_estado"] or 0), c, comp))
    linhas.sort(reverse=True)
    acima = [nome_doenca(c) for d, c, _ in linhas if d > 1.5]
    abaixo = [nome_doenca(c) for d, c, _ in linhas if d < -1.5]
    fala = f"Comparando o ritmo de crescimento de {ctx.cidade} com o do Estado de SP: "
    fala += (f"crescem mais rápido aqui {', '.join(acima)}" if acima else "nenhum câncer cresce claramente mais rápido aqui")
    fala += (f"; mais devagar, {', '.join(abaixo)}." if abaixo else ".")
    fala += " Comparo ritmo, não volume, porque ainda não tenho a população de cada cidade."
    topo = linhas[0][1]
    return Resposta(
        fala=fala,
        expressao="atenta" if acima else "explicando",
        botoes=_mais(topo, "estado", "evolucao") + [("Está aumentando?", caminho("aumentando"))],
        destino={"aba": "Evolução", "cancer": topo, "camadas": {"ver_estado": True}},
        numeros=[f"{nome_doenca(c)}: {formatar_numero(comp['ritmo_municipio'], 1)}% x "
                 f"{formatar_numero(comp['ritmo_estado'] or 0, 1)}% ao ano no Estado" for _, c, comp in linhas],
    )


def fluxo(ctx):
    """De onde vêm as mulheres de outros estados atendidas em SP e onde as
    moradoras da cidade se tratam. Só descreve (nada de causa); usa as
    mesmas frases do painel, para a Lia nunca dizer outra coisa."""
    if ctx.fluxo is None:
        return Resposta(
            fala=("Ainda não consigo mostrar este fluxo: o banco foi carregado sem o município do hospital e o "
                  "estado de residência. Quando a carga for rodada de novo (py etl\\carga_todas_bases.py), eu passo "
                  "a mostrar de onde vêm as mulheres de outros estados atendidas em SP."),
            expressao="cautelosa",
            botoes=[("Como esses dados funcionam?", caminho("metodo"))],
            destino={"aba": "Investigar"},
        )
    r = resumo_fluxo(ctx.fluxo)
    if not r["internacoes_fora"]:
        fala = "Não há internações de mulheres de outros estados registradas nos hospitais de SP."
        numeros = []
    else:
        c = r["concentracao"]
        ufs = r["ufs"].head(3)
        fala = (f"Em todo o Estado de SP, **{formatar_numero(r['pct_fora'], 1)}%** das internações por câncer "
                f"feminino são de mulheres que moram em outros estados "
                f"({formatar_numero(r['internacoes_fora'])} de {formatar_numero(r['internacoes_total'])}). "
                f"Os estados que mais enviam: "
                + ", ".join(f"{u.estado} ({formatar_numero(u.pct, 1)}%)" for u in ufs.itertuples())
                + f". {formatar_numero(c['pct'], 1)}% foram atendidas em {c['destino']}.")
        if isinstance(ctx.fluxo, dict):
            hospitais = hospitais_fluxo(ctx.fluxo, n=1)
            if not hospitais.empty and hospitais.iloc[0]["tem_nome"]:
                fala += (f" O hospital que mais recebe é {hospitais.iloc[0]['hospital']} "
                         f"({formatar_numero(hospitais.iloc[0]['pct'], 1)}% das internações de fora).")
        numeros = [f"{u.estado}: {formatar_numero(u.internacoes)} internações ({formatar_numero(u.pct, 1)}%)"
                   for u in r["ufs"].head(5).itertuples()]
    if ctx.fluxo_cidade:
        fala += f"\n\nSobre {ctx.cidade}: " + " ".join(leitura_cidade(ctx.fluxo_cidade, ctx.cidade)[:2])
    fala += ("\n\nIsso conta internações, não pessoas, e só enxerga hospitais de SP. Eu descrevo o fluxo; "
             "o motivo dele precisa ser investigado.")
    return Resposta(
        fala=fala,
        expressao="atenta" if r["internacoes_fora"] else "explicando",
        botoes=[("Comparar com São Paulo", caminho("estado")), ("Os dados estão completos?", caminho("completude")),
                ("Como esses dados funcionam?", caminho("metodo"))],
        destino={"aba": "Investigar"},
        numeros=numeros,
    )


def fora_padrao(ctx):
    todos = anos_fora_todos(ctx.serie)
    if todos.empty:
        return Resposta(fala=f"Não encontrei anos fora do padrão em {ctx.cidade}.",
                        botoes=[("Está aumentando?", caminho("aumentando"))],
                        destino={"aba": "Investigar"})
    itens = [f"{l['doenca']} em {l['ano']} ({l['direcao']} do esperado"
             + (", poucos casos" if l["numeros_pequenos"] else "") + _cuidado_ano(ctx, l["ano"]) + ")"
             for _, l in todos.iterrows()]
    fala = "Encontrei estes anos fora do padrão: " + "; ".join(itens) + "."
    repetido = todos["ano"].value_counts()
    if repetido.iloc[0] >= 2:
        fala += (f" {repetido.index[0]} aparece para vários cânceres ao mesmo tempo — quando muitos mudam juntos, "
                 f"vale checar o registro antes de concluir.")
    fala += " Eu detecto; a causa precisa ser investigada."
    primeiro = todos.iloc[-1]
    codigo = dict((nome_doenca(c), c) for c in _canceres(ctx))[primeiro["doenca"]]
    return Resposta(
        fala=fala,
        expressao="cautelosa" if todos["numeros_pequenos"].any() or repetido.iloc[0] >= 2 else "atenta",
        botoes=_mais(codigo, "evolucao", "porque") + (
            [("Os dados estão completos?", caminho("completude"))] if anos_incompletos(ctx.serie)
            else [("Como esses dados funcionam?", caminho("metodo"))]),
        destino={"aba": "Investigar"},
        numeros=[f"{l['doenca']} {l['ano']}: {formatar_numero(l['observado'])} internações, esperado "
                 f"~{formatar_numero(l['esperado'])}" for _, l in todos.iterrows()],
    )


def _cuidado_ano(ctx, ano):
    """' (ano com 7 de 12 meses na fonte: leia com cautela)' se o ano
    for incompleto; '' se não."""
    meses = anos_incompletos(ctx.serie).get(int(ano))
    return f" — ano com {meses} de 12 meses na fonte: leia com cautela" if meses else ""


def completude(ctx):
    """Os dados estão completos? Responde com os meses que a fonte
    oferece, antes de qualquer interpretação de tendência. Regras:
    mês ausente não é zero; ano incompleto não é ano normal."""
    serie = ctx.serie
    anos = sorted(int(a) for a in serie["ano"].unique())
    if "meses" not in serie or serie["meses"].isna().all():
        return Resposta(
            fala=("Ainda não consigo dizer: esta base foi carregada sem o mês de cada internação. Quando a carga "
                  "for rodada de novo (py etl\\carga_todas_bases.py), eu passo a mostrar quais meses a fonte "
                  "oferece em cada ano."),
            expressao="cautelosa",
            botoes=[("Como esses dados funcionam?", caminho("metodo"))],
            destino={"aba": "Método"},
        )
    incompletos = anos_incompletos(serie)
    if not incompletos:
        return Resposta(
            fala=f"Sim: todos os anos de {anos[0]} a {anos[-1]} têm os 12 meses na fonte.",
            expressao="explicando",
            botoes=[("Está aumentando?", caminho("aumentando")), ("Como esses dados funcionam?", caminho("metodo"))],
            destino={"aba": "Método"},
        )
    pior = min(incompletos, key=incompletos.get)
    lista = "; ".join(f"{a}: {m} de 12" for a, m in sorted(incompletos.items()))
    faltam = sum(12 - m for m in incompletos.values())
    fala = (f"**Não.** O DATASUS, fonte oficial do SIH/SUS, não disponibiliza todos os meses: **{len(incompletos)} "
            f"dos {len(anos)} anos estão incompletos** ({faltam} meses no total). {lista}."
            f"\n\nConferimos duas vezes — nos arquivos baixados e consultando de novo a fonte oficial: esses meses "
            f"não foram disponibilizados, então não há o que recuperar. Não é falha do Escudo."
            f"\n\nPor isso eu sigo duas regras: **mês ausente não é zero** e **ano incompleto não é ano normal**. "
            f"Para comparar anos, uso a média dos meses disponíveis × 12; os totais do período são o que foi "
            f"registrado. Anos com poucos meses, como {pior} ({incompletos[pior]} de 12), são estimativas menos "
            f"firmes: nenhuma queda ou salto nesses anos deve ser lido como fato sem cautela.")
    return Resposta(
        fala=fala,
        expressao="cautelosa",
        botoes=[("Está aumentando?", caminho("aumentando")), ("Anos fora do padrão", caminho("fora_padrao")),
                ("Como esses dados funcionam?", caminho("metodo"))],
        destino={"aba": "Método"},
        numeros=[f"{a}: {m} de 12 meses na fonte" for a, m in sorted(incompletos.items())],
    )


def metodo(ctx):
    return Resposta(
        fala=("Eu leio internações de mulheres no SUS (SIH/SUS, DATASUS). **Internação não é caso novo**: a mesma "
              "mulher pode ser internada mais de uma vez, e quem se trata só no ambulatório ou pelo plano não "
              "aparece. O ano é o do processamento da internação. O DATASUS não oferece todos os meses de "
              "alguns anos; para comparar anos, uso a média dos meses disponíveis × 12. Minhas tendências são "
              "retas calculadas sobre "
              "todos os anos, e a projeção só prolonga essa reta — com faixa de incerteza e teste de acerto. "
              "Os dados **não** permitem dizer causas, casos novos, orçamento ideal nem comparar cidades de "
              "tamanhos diferentes (falta a população)."),
        expressao="pensativa",
        botoes=[("O que mais aparece?", caminho("mais_aparece")), ("Anos fora do padrão", caminho("fora_padrao"))],
        destino={"aba": "Método"},
    )


# ---------- nível 3: ações sobre um câncer ----------

def _evolucao(ctx, c):
    mun = serie_doenca(ctx.serie, c)
    comp = comparar_com_estado(ctx.serie, c)
    ano_fim, ultimo = int(mun["ano"].max()), mun["internacoes"].iloc[-1]
    ritmo = comp["ritmo_municipio"]
    verbo = "crescem" if ritmo > 1 else ("caem" if ritmo < -1 else "ficam estáveis")
    meses_fim = anos_incompletos(ctx.serie).get(ano_fim)
    fala = (f"**O que aconteceu:** em {ano_fim} foram {formatar_numero(ultimo)} internações por {cancer_de(c)}"
            + (f" (estimado: a fonte só tem {meses_fim} de 12 meses desse ano)" if meses_fim else "") + ". "
            f"\n\n**O que está acontecendo:** desde {int(mun['ano'].min())}, as internações {verbo} "
            f"{formatar_numero(abs(ritmo), 1)}% ao ano em média")
    if comp["ritmo_estado"] is not None:
        fala += f" (no Estado, {formatar_numero(comp['ritmo_estado'], 1)}%)"
    fala += "."
    fora = anos_fora_do_padrao(mun)
    if not fora.empty:
        fala += (" Anos fora do padrão: " + ", ".join(f"{a} ({d}{_cuidado_ano(ctx, a)})"
                                                     for a, d in zip(fora["ano"], fora["direcao"])) + ".")
    if _pequeno(ctx, c):
        fala += " São poucas internações por ano, então variações podem ser acaso."
    return Resposta(
        fala=fala + _nota_2025(ctx),
        expressao="cautelosa" if _pequeno(ctx, c) else ("atenta" if ritmo - (comp["ritmo_estado"] or 0) > 1.5 else "explicando"),
        botoes=_mais(c, "projecao", "estado", "obitos"),
        destino={"aba": "Evolução", "cancer": c, "camadas": {"ver_estado": True, "ver_fora": True}},
    )


def _obitos(ctx, c):
    f = ficha_cancer(ctx.serie, c)
    fala = (f"Das {formatar_numero(f['internacoes'])} internações por {cancer_de(c)}, "
            f"**{formatar_numero(f['obitos'])} terminaram em óbito** — {formatar_numero(f['letalidade'], 1)}%. "
            f"No Estado, {formatar_numero(f['letalidade_estado'], 1)}%.")
    poucos = f["obitos"] < 10
    if poucos:
        fala += " São poucos óbitos, então a comparação é frágil."
    fala += " Isso mede óbitos no hospital, não a mortalidade da doença na população."
    acima = f["obitos"] >= 5 and f["letalidade"] > f["letalidade_estado"] * 1.2
    return Resposta(fala=fala, expressao="cautelosa" if poucos else ("atenta" if acima else "explicando"),
                    botoes=_mais(c, "evolucao", "idade", "porque"),
                    destino={"aba": "Panorama", "cancer": c, "medida": "Óbitos na internação"})


def _valores(ctx, c):
    f = ficha_cancer(ctx.serie, c)
    fala = (f"As internações por {cancer_de(c)} somaram **R$ {formatar_numero(f['valor'])}** em valores "
            f"hospitalares registrados no SIH/SUS — {formatar_numero(f['pct_valor'], 1)}% do valor de todos os "
            f"cânceres, para {formatar_numero(f['pct_internacoes'], 1)}% das internações. Em média, "
            f"R$ {formatar_numero(f['valor_medio'])} por internação (no Estado, R$ {formatar_numero(f['valor_medio_estado'])}). "
            f"Não é o orçamento do município nem o custo total do tratamento.")
    return Resposta(fala=fala, expressao="explicando", botoes=_mais(c, "tempo", "projecao", "evolucao"),
                    destino={"aba": "Panorama", "cancer": c, "medida": "Valor hospitalar registrado"})


def _tempo(ctx, c):
    f = ficha_cancer(ctx.serie, c)
    fala = (f"As internações por {cancer_de(c)} somaram **{formatar_numero(f['dias'])} dias** no hospital: "
            f"em média {formatar_numero(f['permanencia'], 1)} dias por internação "
            f"(no Estado, {formatar_numero(f['permanencia_estado'], 1)}).")
    return Resposta(fala=fala, expressao="explicando", botoes=_mais(c, "valores", "projecao", "evolucao"),
                    destino={"aba": "Panorama", "cancer": c, "medida": "Dias de internação"})


def _idade(ctx, c):
    if ctx.faixas is None:
        return Resposta(fala="Não tenho as idades carregadas agora.", expressao="cautelosa",
                        botoes=_mais(c, "evolucao"), destino={"aba": "Investigar", "cancer": c})
    tabela, periodos = comparar_faixas(ctx.faixas, c)
    if periodos is None:
        return Resposta(fala=f"Não há idade registrada para {cancer_de(c)}.", expressao="cautelosa",
                        botoes=_mais(c, "evolucao"), destino={"aba": "Investigar", "cancer": c})
    frases = leitura_faixas(tabela, periodos)
    return Resposta(fala=f"Comparei a idade das mulheres internadas por {cancer_de(c)} em {periodos[0]} e "
                         f"{periodos[1]}. " + " ".join(frases),
                    expressao="cautelosa" if len(frases) > 1 else "explicando",
                    botoes=_mais(c, "evolucao", "obitos"),
                    destino={"aba": "Investigar", "cancer": c})


def _estado_cancer(ctx, c):
    comp = comparar_com_estado(ctx.serie, c)
    dif = comp["ritmo_municipio"] - (comp["ritmo_estado"] or 0)
    situacao = "mais rápido que" if dif > 1.5 else ("mais devagar que" if dif < -1.5 else "no mesmo ritmo que")
    fala = (f"Em {ctx.cidade}, as internações por {cancer_de(c)} variam {formatar_numero(comp['ritmo_municipio'], 1)}% "
            f"ao ano; no Estado de SP, {formatar_numero(comp['ritmo_estado'] or 0, 1)}%. Ou seja, a cidade anda "
            f"**{situacao}** o Estado. No gráfico, a linha cinza é o Estado na escala da cidade.")
    return Resposta(fala=fala, expressao="atenta" if dif > 1.5 else "explicando",
                    botoes=_mais(c, "evolucao", "projecao"),
                    destino={"aba": "Evolução", "cancer": c, "camadas": {"ver_estado": True}})


def _quanto(v, unidade="", prefixo=""):
    """"cerca de X"; quando a reta bate no zero, "poucos" com a faixa --
    "cerca de 0 dias" soa como erro (ex.: pele não melanoma quase não
    usa leito, e a tendência dos dias é de queda)."""
    if v["previsto"] < 1:
        return (f"poucos{unidade} (faixa de {prefixo}{formatar_numero(v['minimo'])} a "
                f"{prefixo}{formatar_numero(v['maximo'])})")
    return f"cerca de {prefixo}{formatar_numero(v['previsto'])}{unidade}"


def _projecao(ctx, c):
    mun = serie_doenca(ctx.serie, c)
    p = pressao_projetada(ctx.serie, c)
    comp = comparar_com_estado(ctx.serie, c)
    i = p["internacoes"]
    ano_fim = int(mun["ano"].max())
    fala = (f"**O que aconteceu:** em {ano_fim}, {formatar_numero(i['atual'])} internações por {cancer_de(c)}. "
            f"\n\n**O que está acontecendo:** a tendência é de {formatar_numero(comp['ritmo_municipio'], 1)}% ao ano. "
            f"\n\n**O que pode acontecer:** se esse comportamento continuar, a tendência aponta para "
            f"**{formatar_numero(i['minimo'])} a {formatar_numero(i['maximo'])} internações em {i['ano']}** (em torno de "
            f"{formatar_numero(i['previsto'])}), com {_quanto(p['dias_permanencia'], ' dias')} "
            f"de internação e {_quanto(p['valor_total'], '', 'R$ ')} em valores hospitalares registrados.")
    teste = testar_projecao(mun)
    fragil = not i["tendencia_acerta_mais"] or _pequeno(ctx, c)
    if teste:
        fala += (f" Testei o método prevendo anos que já conheço: ele errou "
                 f"{'menos' if i['tendencia_acerta_mais'] else 'mais'} do que simplesmente repetir a média.")
    ponta = leitura_ponta_projecao(mun)
    if ponta:  # último ano longe da reta: explica por que a projeção parece "cair"
        fala += "\n\n" + ponta
    fala += (" É uma **projeção de tendência**, não previsão de casos novos. Serve de sinal para discutir "
             "planejamento e acompanhar a demanda.")
    return Resposta(
        fala=fala + _nota_2025(ctx),
        expressao="cautelosa" if fragil or _ano_em_investigacao(ctx) else "explicando",
        botoes=_mais(c, "porque", "valores") + [("Onde podemos ter problema?", caminho("atencao"))],
        destino={"aba": "Evolução", "cancer": c, "camadas": {"ver_projecao": True}},
        numeros=[f"{nome}: {formatar_numero(v['minimo'])} a {formatar_numero(v['maximo'])} em {v['ano']} "
                 f"(atual: {formatar_numero(v['atual'])})"
                 for nome, v in (("Internações", p["internacoes"]), ("Dias", p["dias_permanencia"]),
                                 ("Valor registrado (R$)", p["valor_total"]))],
    )


def _porque(ctx, c):
    destaques = destaques_cancer(ctx.serie, c)
    avisos = [t for nivel, t in confiabilidade(ctx.serie, c, ctx.duplicados) if nivel == "atencao"]
    fala = (f"Destaquei o **{cancer_de(c)}** por estes números: " + " ".join(destaques))
    if avisos:
        fala += " Cuidados com esta informação: " + " ".join(avisos)
    return Resposta(fala=fala, expressao="pensativa",
                    botoes=_mais(c, "evolucao", "projecao") + [("Como esses dados funcionam?", caminho("metodo"))],
                    destino={"aba": "Panorama", "cancer": c}, numeros=destaques)


ACOES = {"evolucao": _evolucao, "obitos": _obitos, "valores": _valores, "tempo": _tempo, "idade": _idade,
         "estado": _estado_cancer, "projecao": _projecao, "porque": _porque}

CAMINHOS_FUNCOES = {"completude": completude, "mais_aparece": mais_aparece, "aumentando": aumentando, "atencao": atencao,
                    "valores": valores, "estado": estado, "fluxo": fluxo, "fora_padrao": fora_padrao, "metodo": metodo}


def responder(ctx, acao):
    """Executa um botão. Toda resposta termina com [Começar de novo]."""
    tipo = acao.get("tipo")
    if tipo == "inicio":
        return saudacao(ctx)
    if tipo == "caminho":
        if acao["id"] == "futuro":
            r = menu_cancer(ctx, "futuro")
        else:
            r = CAMINHOS_FUNCOES[acao["id"]](ctx)
    elif tipo == "escolher_cancer":
        r = menu_cancer(ctx, acao.get("depois"))
    elif tipo == "cancer":
        if acao["cancer"] not in _canceres(ctx):
            return saudacao(ctx)  # câncer que não existe nesta cidade: volta ao começo
        r = menu_do_cancer(ctx, acao["cancer"]) if acao["acao"] == "menu" else ACOES[acao["acao"]](ctx, acao["cancer"])
    else:
        return saudacao(ctx)
    r.botoes = r.botoes + [("Começar de novo", INICIO)]
    return r
