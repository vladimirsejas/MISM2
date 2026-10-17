import json
import os

import pandas as pd

import assistente as asst
import entendimento as ent
import inteligencia as ti
from lia import Contexto, caminho, responder as lia_responder, sobre

# =====================================
# TESTE DO ASSISTENTE DA LIA (assistente.py, 10/2026)
#
# Usa a base pública de Rio Claro e um Gemini SIMULADO (a nuvem não alcança a
# chave do autor). Confere o que protege o Escudo:
#   - a caixa responde exatamente o que a Lia/painel responderiam (mesmos números);
#   - o texto da IA só passa se não trouxer número novo, promessa ("vai ficar") ou causa;
#   - segurança, sintoma e encaminhamentos nunca passam pela IA;
#   - sem IA, sem rede, com erro ou resposta vazia: a resposta direta aparece.
# =====================================

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, ".."))
MESES = {2013: 10, 2014: 10, 2015: 8, 2016: 9, 2017: 11, 2018: 6, 2019: 7, 2020: 8, 2021: 11, 2022: 10,
         2023: 11, 2024: 8, 2025: 12}
CODIGOS = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL", "Ovário": "OVARIO",
           "Pele não melanoma": "PELE_NAO_MELANOMA", "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}
ABAS = {"Panorama", "Evolução", "Investigar", "Planejamento", "Método"}
falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def contexto():
    real = pd.read_csv(os.path.join(RAIZ, "analises", "base_preditiva_2013_2025.csv"), sep=";")
    real["tipo_cancer"] = real["cancer"].map(CODIGOS)
    real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
    real["dias_permanencia"] = real["dias_internacao_total"]
    serie = ti.ajustar_meses(ti.completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                                                     "valor_total", "dias_permanencia"]]), MESES)
    faixas = pd.DataFrame([(c, a, f, 5 + a % 3) for c in CODIGOS.values() for a in range(2013, 2026)
                           for f in ("até 39 anos", "40 a 49", "50 a 69", "70 ou mais")],
                          columns=["tipo_cancer", "ano", "faixa", "internacoes"])
    return Contexto(serie=serie, cidade="Rio Claro", faixas=faixas)


class Gemini:
    """Dublê do Gemini: devolve o que o teste mandar e guarda o que recebeu."""

    def __init__(self, texto=None, erro=None, classe=None):
        self.texto, self.erro, self.classe, self.chamadas, self.classificacoes = texto, erro, classe, [], []

    def explicar(self, pergunta, base, perfil):
        self.chamadas.append((pergunta, base, perfil))
        if self.erro:
            raise self.erro
        return self.texto(base) if callable(self.texto) else self.texto

    def classificar(self, pergunta, opcoes):
        self.classificacoes.append(pergunta)
        return self.classe

    def ia(self):
        return asst.IA(explicar=self.explicar, classificar=self.classificar, ligada=True)


def main():
    ctx = contexto()
    foco = "MAMA"

    def perguntar(texto, ia=None, memoria=None, perfil="TECNICO"):
        return asst.responder_pergunta(ctx, texto, foco, memoria=memoria, perfil=perfil, ia=ia,
                                       outras_cidades=["Campinas", "Piracicaba"])

    # ---- 1. numeros_novos / conferir ----
    checar("1. números: 1.668, 1668 e '1 668' contam como o mesmo; 5,3 = 5.3",
           asst.numeros_novos("foram 1668 e 5,3%", "total de 1.668 internações, 5.3% ao ano") == [])
    checar("1. número novo é apontado (e o de 1 dígito é ignorado)",
           asst.numeros_novos("foram 2.000 em 2030, 3 casos", "foram 1.668 em 2025") == ["2000", "2030"])
    checar("1. 5,3 NÃO é 53: a vírgula decimal não some na comparação (e 0,5 não é 50)",
           asst.numeros_novos("A taxa foi de 53%", "A taxa foi de 5,3%") == ["53"]
           and asst.numeros_novos("A taxa foi de 5,3%", "A taxa foi de 53%") == ["5.3"]
           and asst.numeros_novos("0,5 por cento", "50 por cento") == ["0.5"])
    checar("1. milhar e decimal certos: 1,668 = 1.668 = 1668; 1.234.567 = 1234567; 5,30 = 5,3",
           asst.numeros_novos("1,668 e 1668", "1.668 casos") == []
           and asst.numeros_novos("1.234.567", "1234567") == []
           and asst.numeros_novos("5,30%", "5,3%") == [])
    checar("1. a conferência barra o texto da IA que troca 5,3 por 53",
           asst.conferir("Cresce 53% ao ano.", "Cresce 5,3% ao ano.", "x") is not None
           and asst.conferir("Cresce 5,3% ao ano.", "Cresce 5,3% ao ano.", "x") is None)
    checar("1. o ano que a pessoa escreveu na pergunta pode ser repetido", asst.conferir("Em 2030 a tendência aponta 40.", "40 internações", "e em 2030?") is None)
    checar("1. 'vai ficar' e 'vai aumentar' são barrados", asst.conferir("A mama vai aumentar em 40.", "40", "x") is not None
           and asst.conferir("Vai ficar em 40.", "40", "x") is not None)
    checar("1. explicação de causa é barrada ('por causa de', 'devido ao')",
           asst.conferir("Subiu por causa do envelhecimento: 40.", "40", "x") is not None
           and asst.conferir("Subiu devido ao rastreamento: 40.", "40", "x") is not None
           and asst.conferir("A tendência aponta 40, sem indicar causa.", "40", "x") is None)

    checar("1. link na resposta da IA é barrado (a injeção de texto não vira atalho para site externo)",
           asst.conferir("Veja [aqui](http://exemplo.com) os 40.", "40", "x") is not None
           and asst.conferir("Acesse www.exemplo.com: 40.", "40", "x") is not None)

    # ---- 2. cada assunto responde sem IA, com a mesma voz da Lia ----
    amostras = {
        "mais_aparece": "qual câncer mais interna?", "evolucao": "o câncer de mama tá aumentando?",
        "futuro": "como vai estar a mama em 2028?", "obitos": "quantas mulheres morrem de câncer de mama?",
        "valores": "quanto o sus gasta com câncer de pulmão?", "tempo": "quantos dias ficam internadas com colorretal?",
        "idade": "qual a idade das mulheres com câncer de mama?", "estado": "estamos pior que o resto de são paulo?",
        "atencao": "onde a prefeitura deveria olhar com mais cuidado?", "fora_padrao": "teve algum ano esquisito nos dados?",
        "fluxo": "tem mulher de outro estado se tratando em são paulo?", "completude": "os dados de 2025 estão completos?",
        "metodo": "de onde vocês tiraram esses dados?", "sobre_ia": "vocês usam inteligência artificial de verdade?",
        "comparar_cidades": "quero comparar com campinas", "onde_atendida": "onde faço mamografia aqui perto?",
        "apoio": "fui diagnosticada com câncer de mama e agora?", "sintoma": "senti um caroço no peito, o que pode ser",
        "ajuda": "o que eu posso te perguntar?"}
    for intencao, pergunta in amostras.items():
        r = perguntar(pergunta)
        ok = (isinstance(r, asst.RespostaIA) and r.fala.strip() and r.intencao == intencao and r.tipo == "intencao"
              and (r.destino is None or r.destino.get("aba") in ABAS | {None})
              and any(a.get("tipo") == "inicio" for _, a in r.botoes))
        checar(f"2. {intencao}: '{pergunta}' -> responde" + ("" if ok else f" (veio {r.tipo}/{r.intencao})"), ok)

    # a voz é a mesma: sem IA, a resposta da caixa É a resposta da Lia
    r = perguntar("o câncer de mama tá aumentando?")
    checar("2. sem IA, 'mama aumentando?' é exatamente a fala da Lia para Mama > Evolução",
           r.fala == lia_responder(ctx, sobre("MAMA", "evolucao")).fala and r.destino == lia_responder(ctx, sobre("MAMA", "evolucao")).destino)
    r = perguntar("onde podemos ter problema nos próximos anos?")
    checar("2. sem IA, 'onde pode ter problema' é exatamente a fala do radar da Lia",
           r.fala == lia_responder(ctx, caminho("atencao")).fala and r.selo.startswith("Resposta direta"))
    r = perguntar("e os valores do câncer de pulmão?")
    checar("2. valores de pulmão: 'valor hospitalar registrado', nunca 'orçamento'",
           "valores hospitalares registrados" in r.fala and "Não é o orçamento do município" in r.fala)

    # ---- 3. previsão ----
    r = perguntar("como vai estar a mama em 2028?")
    checar("3. previsão da mama: 'tendência aponta', testou modelos, destino no gráfico com projeção ligada",
           "tendência aponta" in r.fala and "modelos" in r.fala and r.destino["camadas"] == {"ver_projecao": True}
           and r.destino["aba"] == "Evolução" and "2028" in r.fala)
    r = perguntar("quantas internações de mama em 2031?")
    checar("3. ano além do horizonte: diz até quando projeta", "Só projeto até 2028" in r.fala)
    r = perguntar("quantas internações de mama em 2020?")
    registrado = int(ctx.serie[(ctx.serie.tipo_cancer == "MAMA") & (ctx.serie.grupo == "MUNICIPIO") & (ctx.serie.ano == 2020)]["internacoes_reg"].iloc[0])
    checar("3. 'quantas de mama em 2020?': dá o número REGISTRADO daquele ano e avisa que a fonte tem só 8 de 12 meses",
           f"Em 2020, foram registradas {registrado} internações por câncer de mama" in r.fala and "8 de 12 meses" in r.fala
           and r.intencao == "evolucao")
    r = perguntar("quantas internações de mama em 2012?")
    checar("3. ano sem dados: diz de quando a quando vão os dados", "Não tenho dados de 2012" in r.fala)
    r = perguntar("tem previsão pros próximos anos?")
    checar("3. previsão sem câncer: compara todos, avisa fragilidade e oferece botões por câncer",
           "frágil" in r.fala and len(r.botoes) >= 4 and r.destino["aba"] == "Planejamento")
    checar("3. nenhuma resposta sem IA promete ('vai ficar/aumentar')",
           all(not asst.PROMETE.search(perguntar(q).fala) for q in ("como vai estar a mama em 2028?", "tem previsão pros próximos anos?",
                                                                      "o pulmão vai piorar nos próximos anos?")))

    # ---- 4. todos os cânceres quando não se cita ----
    r = perguntar("qual câncer é o mais letal")
    checar("4. 'mais letal' sem câncer compara todos (letalidade hospitalar) e diz que não é mortalidade da população",
           "maior letalidade hospitalar" in r.fala and "não a mortalidade" in r.fala and r.cancer is None)
    r = perguntar("as internações são demoradas?")
    checar("4. tempo sem câncer compara todos", "internação mais longa" in r.fala and r.cancer is None)
    r = perguntar("e a idade? as mais novas")
    checar("4. idade sem câncer usa o câncer em foco e avisa", "câncer em foco no painel" in r.fala and r.cancer == "MAMA")
    r = perguntar("e a letalidade desse câncer?")
    checar("4. 'desse câncer' = o em foco, dito na resposta", r.cancer == "MAMA" and "em foco no painel" in r.fala)
    r = perguntar("quantas morrem de câncer de estômago?")
    checar("4. câncer que não acompanho: diz isso e mostra os que acompanho", "Ainda não acompanho o câncer de estômago" in r.fala)
    r = perguntar("e o câncer de estômago?")
    checar("4. só o nome de um câncer não acompanhado: lista os acompanhados com botões", "Ainda não acompanho" in r.fala and len(r.botoes) >= 5)

    # ---- 5. memória (seguimento) ----
    r1 = perguntar("quantas morrem de câncer de mama?")
    r2 = perguntar("e de pulmão?", memoria={"intencao": r1.intencao, "cancer": r1.cancer})
    checar("5. 'e de pulmão?' continua em óbitos, agora de pulmão",
           (r2.intencao, r2.cancer, r2.origem) == ("obitos", "PULMAO", "seguimento") and "pulmão" in r2.fala.lower())

    # ---- 6. segurança: nunca passa pela IA ----
    g = Gemini(texto="NÃO DEVERIA APARECER")
    for pergunta, marcas in (("meu marido me bate", ("190", "180")), ("quero morrer", ("188", "192")),
                             ("estou passando mal agora", ("192",))):
        r = perguntar(pergunta, ia=g.ia())
        checar(f"6. segurança: '{pergunta}' -> {'/'.join(marcas)}, link para o Apoio, sem IA",
               r.tipo == "risco" and all(m in r.fala for m in marcas) and asst.LINK_APOIO in r.links and not r.usou_ia)
    r = perguntar("senti um caroço no peito, será que é câncer?", ia=g.ia())
    checar("6. sintoma: texto fixo ('não faço diagnóstico'), UBS, 192, links; a IA não improvisa",
           "Eu não faço diagnóstico" in r.fala and "UBS" in r.fala and "192" in r.fala and len(r.links) == 2 and not r.usou_ia)
    for pergunta in ("onde faço mamografia aqui perto?", "meus direitos como paciente de câncer", "quero comparar com campinas", "o que você consegue responder?"):
        perguntar(pergunta, ia=g.ia())
    checar("6. apoio, onde ser atendida, comparar cidades e ajuda: a IA nem é chamada",
           g.chamadas == [] and g.classificacoes == [])

    # ---- 7. a IA redigindo, com conferência ----
    boa = Gemini(texto=lambda base: "Em Rio Claro, a tendência aponta para o aumento das internações por câncer de mama: "
                                     "veja os números abaixo, que são os calculados pelo Escudo.")
    r = perguntar("o câncer de mama tá aumentando?", ia=boa.ia())
    checar("7. texto bom da IA aparece, com selo, e a resposta determinística fica guardada em 'base'",
           r.usou_ia and r.fala.startswith("Em Rio Claro, a tendência aponta") and "Gemini" in r.selo
           and r.base == lia_responder(ctx, sobre("MAMA", "evolucao")).fala and r.ia_motivo is None)
    pergunta_recebida, base_recebida, perfil_recebido = boa.chamadas[0]
    checar("7. o Gemini recebeu a pergunta original, a fala da Lia como base e o perfil",
           pergunta_recebida == "o câncer de mama tá aumentando?" and lia_responder(ctx, sobre("MAMA", "evolucao")).fala in base_recebida
           and perfil_recebido == "TECNICO")
    perguntar("o câncer de mama tá aumentando?", ia=boa.ia(), perfil="SIMPLES")
    checar("7. perfil 'Simples' chega ao Gemini", boa.chamadas[-1][2] == "SIMPLES")

    base_lia = lia_responder(ctx, sobre("MAMA", "evolucao")).fala
    for nome, texto, esperado in (
            ("número inventado", "Foram 98765 internações por câncer de mama.", "número"),
            ("promessa", "As internações vão aumentar bastante em Rio Claro.", "prometeu"),
            ("causa", "O aumento ocorre por causa do envelhecimento da população.", "causa"),
            ("texto vazio", "   ", "vazio")):
        g2 = Gemini(texto=texto)
        r = perguntar("o câncer de mama tá aumentando?", ia=g2.ia())
        checar(f"7. IA com {nome}: descartada, a resposta direta da Lia aparece (motivo: '{(r.ia_motivo or '')[:45]}')",
               not r.usou_ia and r.fala == base_lia and esperado in (r.ia_motivo or "") and "conferência" in r.selo)
    for nome, erro in (("sem rede", ConnectionError("sem rede")), ("cota esgotada", RuntimeError("429 RESOURCE_EXHAUSTED"))):
        r = perguntar("o câncer de mama tá aumentando?", ia=Gemini(erro=erro).ia())
        checar(f"7. IA com erro ({nome}): resposta direta, aviso discreto, nada quebra",
               not r.usou_ia and r.fala == base_lia and "não respondeu agora" in r.selo)
    r = perguntar("o câncer de mama tá aumentando?", ia=asst.IA())
    checar("7. sem chave/IA desligada: resposta direta e selo claro", not r.usou_ia and r.fala == base_lia and "sem IA" in r.selo)

    # a IA também pode ajudar a ENTENDER (segunda chance), e o resultado é redigido normalmente
    g3 = Gemini(texto=lambda base: "A tendência aponta variações; veja os números abaixo.", classe={"intencao": "metodo", "cancer": None})
    r = perguntar("me explica o negócio dos números do hospital das moças", ia=g3.ia())
    checar("7. pergunta obscura: o Gemini sozinho (sem apoio da busca local) vira palpite para confirmar, não resposta direta",
           g3.classificacoes and r.tipo == "palpites" and r.origem == "gemini_sem_apoio" and not r.usou_ia
           and r.botoes and r.botoes[0][0] == ent.ROTULOS["metodo"])
    r2 = asst.responder_escolha(ctx, r.botoes[0][1], foco)
    checar("7. clicar no palpite do Gemini responde o assunto escolhido (origem 'escolha')",
           r2.tipo == "intencao" and r2.intencao == "metodo" and r2.origem == "escolha" and r2.fala.strip())
    g4 = Gemini(texto="x", classe={"intencao": "invencao"})
    r = perguntar("me explica o negócio dos números do hospital das moças", ia=g4.ia())
    checar("7. Gemini devolve assunto que não existe: vira palpites/fora, nunca resposta chutada", r.tipo in ("palpites", "fora"))

    # ---- 7b. conversa: "me explica isso melhor" e pedido composto ----
    memoria_ev = {"intencao": "evolucao", "cancer": "MAMA"}
    base_ev = perguntar("o câncer de mama tá aumentando?")
    r = perguntar("me explica isso melhor", memoria=memoria_ev)
    checar("7b. 'me explica isso melhor' retoma a evolução da mama: explicação simples + os mesmos números + como ler",
           (r.tipo, r.intencao, r.cancer, r.origem) == ("intencao", "evolucao", "MAMA", "explicar")
           and "Vou explicar de outro jeito" in r.fala and asst.EXPLICACAO_SIMPLES["evolucao"] in r.fala
           and base_ev.fala in r.fala and asst.COMO_LER in r.fala)
    checar("7b. a explicação simples é texto fixo, sem chamar a IA, e o painel acompanha o assunto anterior",
           not r.usou_ia and "Texto fixo" in r.selo and r.destino == base_ev.destino)
    g5 = Gemini(texto="x", classe={"intencao": "metodo"})
    r5 = perguntar("não entendi", memoria=memoria_ev, ia=g5.ia())
    checar("7b. mesmo com o Gemini ligado, 'não entendi' não gasta chamada de IA e continua explicando o assunto anterior",
           r5.origem == "explicar" and not g5.classificacoes and not r5.usou_ia)
    r = perguntar("me explica isso melhor")
    checar("7b. sem resposta anterior, 'me explica isso melhor' não inventa: oferece palpites ou pergunta",
           r.tipo in ("palpites", "fora") and r.origem != "explicar")
    textos = list(asst.EXPLICACAO_SIMPLES.values()) + [asst.COMO_LER]
    checar("7b. todas as explicações simples cobrem os 13 assuntos de dados, sem número, sem 'vai ficar' e sem atribuir causa",
           set(asst.EXPLICACAO_SIMPLES) == asst.SO_DADOS and not any(any(c.isdigit() for c in t) for t in textos)
           and not any(asst.PROMETE.search(t) or asst.CAUSA_ATRIBUIDA.search(t) for t in textos))
    for pergunta_c, par in (("está aumentando e o que posso esperar para frente?", ("evolucao", "futuro")),
                            ("morrem muito e quanto o SUS gasta com isso", ("valores", "obitos"))):
        rc = perguntar(pergunta_c)
        sozinhas = [asst.responder_escolha(ctx, asst.acao(i, rc.cancer, pergunta_c), foco) for i in par]
        checar(f"7b. composto '{pergunta_c}': responde os dois, com os mesmos números das respostas separadas",
               (rc.tipo, rc.origem, rc.intencao) == ("intencao", "composta", par[0])
               and all(s.fala in rc.fala for s in sozinhas) and "dois pedidos" in rc.selo and not rc.usou_ia)
    checar("7b. composto: botões de cada assunto e um só 'Início'",
           sum(1 for _, a in rc.botoes if a.get("tipo") == "inicio") == 1)

    # ---- 7c. recusa explicativa: ranking ou proporção entre cidades depende da população ----
    r = perguntar("quais as cidades que mais têm câncer de mama proporcionalmente?")
    checar("7c. ranking proporcional entre cidades: a Lia diz que falta a população, por que importa e o que dá para ver hoje",
           (r.tipo, r.intencao) == ("intencao", "sem_dados") and r.fala.startswith(asst.SEM_POPULACAO[:60])
           and "população de cada cidade" in r.fala and "parcela de cada câncer" in r.fala and not r.usou_ia)
    checar("7c. a recusa oferece 'Comparar com outra cidade' (o que existe hoje) e não inventa ranking",
           any(rot == "Comparar com outra cidade" for rot, _ in r.botoes) and "R$" not in r.fala
           and not any(c.isdigit() for c in asst.SEM_POPULACAO) and not asst.PROMETE.search(asst.SEM_POPULACAO)
           and not asst.CAUSA_ATRIBUIDA.search(asst.SEM_POPULACAO))
    r2 = perguntar("qual a raça das mulheres internadas?")
    checar("7c. outra falta de dado (raça) continua com a recusa geral, sem o texto da população",
           r2.intencao == "sem_dados" and r2.fala.startswith(asst.SEM_DADOS[:60]) and "proporcionalmente" not in r2.fala)

    # ---- 7d. lacunas do 2º teste com uma pessoa ----
    r = perguntar("Compare câncer de mama com o de colo do útero")
    checar("7d. comparar dois cânceres: a Lia avisa que mostra todos lado a lado e responde com os números",
           r.intencao == "mais_aparece" and r.fala.startswith("Para comparar cânceres") and "internaç" in r.fala.lower())
    r = perguntar("Compare câncer de mama com o de melanoma")
    checar("7d. melanoma não é acompanhado: a Lia diz isso e mostra os que acompanha",
           "Ainda não acompanho o câncer de melanoma" in r.fala and r.intencao == "mais_aparece")
    r = perguntar("estou com dor de cabeça e um caroço no seio")
    checar("7d. sintoma não ganha o aviso de 'câncer não acompanhado' (texto fixo de segurança, sem ruído)",
           r.intencao == "sintoma" and "Eu não faço diagnóstico" in r.fala and "Ainda não acompanho" not in r.fala)
    r = perguntar("o câncer de pele não melanoma está aumentando?")
    checar("7d. pele não melanoma é acompanhado: sem o falso aviso de melanoma", "Ainda não acompanho" not in r.fala)
    r = perguntar("quero contato de hospital especializado em câncer")
    checar("7d. hospital especializado em câncer: a Lia aponta a lâmina 'Hospitais no Estado' do Apoio à mulher",
           r.intencao == "apoio" and "Hospitais no Estado" in r.fala)
    r = perguntar("endereço de algum hospital de câncer")
    checar("7d. endereço de hospital (cadastro da cidade) também aponta o 'Hospitais no Estado' para câncer",
           "Hospitais no Estado" in r.fala and any(a == "pages/onde_ser_atendida.py" for _, a in r.links))

    # ---- 7e. com a população do IBGE no banco, a Lia responde o ranking proporcional de verdade ----
    import pandas as _pd
    rk = _pd.DataFrame([(f"35{i:04d}", f"Cidade {i}", 50_000, 100, 10.0, 80.0 - 10 * i, i + 1) for i in range(4)] +
                       [("354390", "Rio Claro", 106_123, 50, 10.0, 22.6, 5)],
                       columns=["codigo6", "municipio", "populacao", "internacoes", "media_anual", "taxa", "posicao"])
    ctx_pop = Contexto(serie=ctx.serie, cidade="Rio Claro", faixas=ctx.faixas, codigo_ibge=3543907, ranking={"MAMA": rk, None: rk})
    r = asst.responder_pergunta(ctx_pop, "quais as cidades que mais têm câncer de mama proporcionalmente?", foco,
                                ia=asst.IA(), outras_cidades=["Campinas"])
    checar("7e. com a população: a Lia mostra o ranking por 100 mil mulheres, a posição de Rio Claro e que não é incidência",
           r.intencao == "sem_dados" and "por **100 mil mulheres**" in r.fala and "Cidade 0: 80,0" in r.fala
           and "posição **5** de 5" in r.fala and "Não é incidência" in r.fala and not r.usou_ia)
    checar("7e. o ranking sai dos cálculos: sem número inventado, sem causa, sem 'vai', e continua oferecendo comparar cidades",
           not asst.PROMETE.search(r.fala) and not asst.CAUSA_ATRIBUIDA.search(r.fala)
           and any(rot == "Comparar com outra cidade" for rot, _ in r.botoes))
    r = asst.responder_pergunta(ctx_pop, "quais as cidades que mais têm câncer proporcionalmente?", foco, ia=asst.IA())
    checar("7e. sem citar câncer usa os 7 somados", "os 7 cânceres somados" in r.fala)
    r = asst.responder_pergunta(ctx, "quais as cidades que mais têm câncer de mama proporcionalmente?", foco, ia=asst.IA())
    checar("7e. sem a população no banco (ctx sem ranking) a Lia volta a dizer o que falta, sem ranking inventado",
           r.fala.startswith(asst.SEM_POPULACAO[:60]) and "por 100 mil" not in r.fala.split("população")[0])

    # ---- 7f. hospital de câncer e a cidade que a pessoa cita (teste humano de 17/10/2026: Catanduva, "Hospikital") ----
    for q in ("preciso dde um hospital que atenda cande de ovario eu moro em Catanduva",
              "Hospikital perto de mim que atenda paciente de cancer moro em Catanduva"):
        r = asst.responder_pergunta(ctx, q, foco, ia=asst.IA())
        checar(f"7f. '{q[:40]}...': não empurra Rio Claro nem o cadastro local; aponta a lâmina Hospitais no Estado e a região",
               r.intencao == "onde_atendida" and "Catanduva" in r.fala and "Hospitais no Estado" in r.fala and "região" in r.fala
               and "Santa Casa de Rio Claro" not in r.fala and not r.usou_ia)
    r = asst.responder_pergunta(ctx, "moro em Rio Claro, qual hospital trata câncer de mama?", foco, ia=asst.IA())
    checar("7f. moradora de Rio Claro recebe os hospitais de câncer do catálogo da cidade",
           r.intencao == "onde_atendida" and "Santa Casa de Rio Claro" in r.fala)
    r = asst.responder_pergunta(ctx, "hospital de cancer, moro em Araraquara", foco, ia=asst.IA())
    checar("7f. cidade citada que aparece no catálogo (Araraquara): mostra o hospital ligado a ela, não só Rio Claro",
           r.intencao == "onde_atendida" and "Araraquara" in r.fala and "Hospitais do catálogo" in r.fala)
    r = asst.responder_pergunta(ctx, "onde ser atendida em Rio Claro, posto de saúde", foco, ia=asst.IA())
    checar("7f. posto de saúde (sem câncer) continua com o texto de Onde ser atendida", r.intencao == "onde_atendida" and "Onde ser atendida" in r.fala)

    # ---- 7g. quimio/radio (SIA) e mortalidade real (SIM): só descrevem, e sem as tabelas dizem o que falta ----
    trat = _pd.DataFrame(
        [("QUIMIO", 2022, m, "354390", "MAMA", "50 a 69", "2", "01", 10) for m in range(1, 13)]
        + [("QUIMIO", 2022, m, "355030", "MAMA", "50 a 69", "2", "01", 90) for m in range(1, 13)]
        + [("RADIO", 2022, 1, "354390", "MAMA", "50 a 69", "", "03", 4), ("RADIO", 2022, 1, "354390", "MAMA", "50 a 69", "2", "99", 6)],
        columns=["modalidade", "ano", "mes", "codigo6", "tipo_cancer", "faixa", "estadiamento", "raca_cor", "apacs"])
    rt = ti.resumo_tratamento(trat, 3543907)
    checar("7g. resumo do tratamento: 120 APACs de quimio em 2022 na cidade, 1.200 no Estado (12 meses, sem compensação)",
           rt["QUIMIO"]["apacs_ultimo"] == 120 and rt["QUIMIO"]["estado_ultimo"] == 1200 and rt["QUIMIO"]["ultimo_ano"] == 2022)
    checar("7g. radio com 1 mês na fonte é compensada x12 (10 APACs no mês = 120 no ano)", abs(rt["RADIO"]["apacs_ultimo"] - 120) < 1e-9)
    checar("7g. estadiamento informado em 60% e raça informada em 40% das APACs de radio (conta à mão)",
           abs(rt["RADIO"]["pct_estadiamento"] - 60) < 1e-9 and abs(rt["RADIO"]["pct_raca_informada"] - 40) < 1e-9)
    sim = _pd.DataFrame([(2023, "354390", "MAMA", "50 a 69", "1", "1", 30), (2023, "354390", "MAMA", "50 a 69", "3", "1", 10),
                         (2023, "355030", "MAMA", "50 a 69", "1", "1", 960)],
                        columns=["ano", "codigo6", "tipo_cancer", "faixa", "local_obito", "raca_cor", "obitos"])
    rm = ti.resumo_mortalidade(sim, 3543907, serie=ctx.serie[ctx.serie["grupo"] == "MUNICIPIO"])
    checar("7g. SIM: 40 óbitos na cidade e 1.000 no Estado; 75% no hospital e 25% em casa", rm["obitos_ultimo"] == 40
           and rm["estado_ultimo"] == 1000 and abs(rm["onde"]["no hospital"] - 75) < 1e-9 and abs(rm["onde"]["em casa"] - 25) < 1e-9)
    ctx_novo = Contexto(serie=ctx.serie, cidade="Rio Claro", faixas=ctx.faixas, codigo_ibge=3543907, tratamento=trat, obitos_sim=sim)
    r = asst.responder_pergunta(ctx_novo, "quantas mulheres fazem quimioterapia na cidade?", foco, ia=asst.IA())
    checar("7g. a Lia responde a quimio e radio com APAC (não mulheres), sem causa, sem 'vai', sem IA",
           r.intencao == "tratamento" and "APAC" in r.fala and "não é número de mulheres" in r.fala
           and not asst.PROMETE.search(r.fala) and not asst.CAUSA_ATRIBUIDA.search(r.fala) and not r.usou_ia)
    r = asst.responder_pergunta(ctx_novo, "quantas mulheres morreram de câncer no total, dentro e fora do hospital?", foco, ia=asst.IA())
    checar("7g. a Lia responde a mortalidade real explicando que SIM e SIH não se subtraem",
           r.intencao == "mortalidade_real" and "SIM" in r.fala and "SIH" in r.fala and "não se subtraem" in r.fala
           and not asst.PROMETE.search(r.fala) and not asst.CAUSA_ATRIBUIDA.search(r.fala))
    r = asst.responder_pergunta(ctx, "quantas mulheres fazem quimioterapia na cidade?", foco, ia=asst.IA())
    checar("7g. sem as tabelas no banco a Lia diz o que falta e como trazer, sem inventar número",
           r.intencao == "tratamento" and "carregar_tudo_pysus" in r.fala)
    r = asst.responder_pergunta(ctx, "qual a cor ou raça das internadas?", foco, ia=asst.IA())
    checar("7g. raça das INTERNADAS continua 'não tenho' (só o ambulatorial tem), apontando a pergunta certa",
           r.intencao == "sem_dados" and "quimioterapia" in r.fala)

    # ---- 8. palpites e botões ----
    r = perguntar("me explica o negócio dos números do hospital das moças")
    ok_palpites = r.tipo in ("palpites", "fora")
    checar("8. sem IA, pergunta obscura vira palpites ou fora, com botões", ok_palpites and r.botoes)
    if r.tipo == "palpites":
        a = r.botoes[0][1]
        r2 = asst.responder_escolha(ctx, a, foco)
        checar("8. clicar num palpite responde o assunto escolhido (origem 'escolha')", r2.tipo == "intencao" and r2.origem == "escolha" and r2.fala.strip())
    r = asst.responder_escolha(ctx, asst.acao("futuro", "PULMAO", "como fica o pulmão?"), foco)
    checar("8. botão de exemplo com câncer: responde a previsão do pulmão", r.intencao == "futuro" and r.cancer == "PULMAO")
    r = perguntar("qual a previsão do tempo amanhã")
    checar("8. fora do assunto: diz o que sabe fazer e oferece exemplos", r.tipo == "fora" and len(r.botoes) >= 4 and "foge do que sei" in r.fala)
    r = perguntar("oi")
    checar("8. saudação: a Lia se apresenta e mostra os caminhos", r.tipo == "saudacao" and "Lia" in r.fala and len(r.botoes) >= 8)
    r = perguntar("")
    checar("8. pergunta vazia: ajuda", r.tipo == "vazio" and r.fala.strip())

    # ---- 8b. causa, falta de dados, contexto, fonte ----
    r = perguntar("qual o motivo desse aumento todo?")
    checar("8b. pergunta de causa: texto fixo honesto ('não explica por quê'), com caminhos do que os dados permitem",
           r.intencao == "causa" and "não explica por quê" in r.fala and len(r.botoes) >= 4 and not r.usou_ia)
    r = perguntar("quantas sobreviveram cinco anos depois do diagnóstico?")
    checar("8b. informação que não existe (sobrevida): 'eu não tenho', diz o que a base tem, não inventa",
           r.intencao == "sem_dados" and "eu não tenho" in r.fala and "SIH/SUS" in r.fala)
    r1 = perguntar("como evoluíram as internações por câncer de mama?")
    r2 = perguntar("e no estado?", memoria={"intencao": r1.intencao, "cancer": r1.cancer})
    r3 = perguntar("e o de colo do útero?", memoria={"intencao": r2.intencao, "cancer": r2.cancer})
    checar("8b. contexto: 'e no estado?' mantém a mama; 'e o de colo do útero?' mantém o assunto (estado) e troca o câncer",
           (r1.intencao, r1.cancer) == ("evolucao", "MAMA") and (r2.intencao, r2.cancer) == ("estado", "MAMA")
           and (r3.intencao, r3.cancer) == ("estado", "COLO_UTERO"))
    r4 = perguntar("e o de colo do útero?")
    checar("8b. sem contexto anterior, 'e o de colo do útero?' não inventa assunto", r4.tipo in ("palpites", "fora", "intencao") and r4.origem != "seguimento")
    r = perguntar("o câncer de mama tá aumentando?")
    checar("8b. resposta de dados traz fonte, cidade, período e o limite (não é caso novo)",
           r.fonte and "SIH/SUS" in r.fonte and "Rio Claro" in r.fonte and "2013–2025" in r.fonte and "não é caso novo" in r.fonte)
    checar("8b. resposta fixa (apoio, sintoma, segurança) não leva linha de fonte de dados",
           all(perguntar(q).fonte is None for q in ("meu marido me bate", "senti um caroço no peito", "fui diagnosticada e agora?")))

    # ---- 9. sobre a IA diz a verdade ----
    desligada = perguntar("vocês usam inteligência artificial de verdade?")
    ligada = perguntar("vocês usam inteligência artificial de verdade?", ia=boa.ia())
    checar("9. 'como a IA funciona' diz se o Gemini está ligado ou desligado, e fala dos limites",
           "desligada" in desligada.fala and "ligada" in ligada.fala and "não faço diagnóstico" in ligada.fala.lower()
           and f"{len(ti.MODELOS_PREVISAO)} modelos" in ligada.fala)

    # ---- 10. fumaça: o gabarito inteiro, sem IA e com IA quebrada, nunca derruba ----
    gabarito = json.load(open(os.path.join(AQUI, "gabarito_perguntas.json"), encoding="utf-8"))
    problemas = []
    quebrada = Gemini(erro=RuntimeError("falha"), classe=None).ia()
    for g_ in gabarito:
        for ia in (None, quebrada):
            try:
                r = perguntar(g_["pergunta"], ia=ia)
                if not r.fala.strip() or asst.PROMETE.search(r.fala):
                    problemas.append(g_["pergunta"])
            except Exception as erro:  # noqa: BLE001
                problemas.append(f"{g_['pergunta']} -> {type(erro).__name__}: {erro}")
    checar(f"10. as {len(gabarito)} perguntas do gabarito respondem sem IA e com IA quebrada, sem erro"
           + (f" (problemas: {problemas[:3]})" if problemas else ""), not problemas)

    if falhas:
        print(f"\n{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("\nTodas as checagens do assistente passaram.")


if __name__ == "__main__":
    main()
