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
    "mama": "mamografia exame da mama mamas caroço seio peito nódulo mastologista mastologia ultrassom das mamas rastreamento "
            "carreta mamografia gratuita sem pedido médico prevenção do câncer de mama",
    "colo": "papanicolau papanicolaou preventivo colo do útero hpv vacina hpv teste de dna colpo exame ginecológico "
            "prevenção do câncer do colo do útero ginecologista",
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
    "rc_carreta_hospital_de_amor": "carreta hospital de amor rio claro quando vem",
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


def buscar(pergunta, n=3):
    """[(id do item, nota)] dos n mais parecidos com a pergunta, do maior para o menor."""
    notas = INDICE.notas(pergunta)
    return sorted(notas.items(), key=lambda kv: -kv[1])[:n]


# ---------- respostas ----------

@dataclass
class RespostaApoio(Resposta):
    pergunta: str = None
    tipo: str = "itens"        # itens | palpites | nada | risco | sintoma | saudacao | vazio
    origem: str = "regras"     # regras | gemini
    selo: str = None
    candidatos: list = field(default_factory=list)   # ids dos itens oferecidos


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


def responder_pergunta(pergunta, classificar=None):
    """Entende a pergunta e devolve uma resposta do guia. `classificar`: função do Gemini
    (pergunta, opções, contexto=, com_cancer=) -> {"intencao"} ou None; só é chamada sem confiança."""
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

    achados = buscar(pergunta)
    (id1, n1), (_, n2) = achados[0], achados[1]

    direto = n1 >= ALTO and (n1 - n2) >= FOLGA
    parece_sintoma = (social.tipo == "intencao" and social.intencao == "sintoma") or (
        social.tipo == "palpites" and social.palpites and social.palpites[0][0] == "sintoma")
    if parece_sintoma and not direto:   # sem um item claro para o que ela descreve
        import assistente
        r = Resposta(fala=assistente.SINTOMA.replace("Na página **Apoio à mulher** está o caminho do cuidado (exames, rede oncológica, direitos). "
                                                     "Em **Onde ser atendida**, as unidades da sua cidade.",
                                                     "Aqui no guia estão o caminho do exame e o que fazer depois."),
                     expressao="acolhedora",
                     botoes=[("Caminho do exame", apoio.item("caminho_do_exame")), ("Exame alterado ou diagnóstico", apoio.caminho("diagnostico")),
                             ("Unidades de Saúde em Rio Claro", apoio.item("rc_unidades"))],
                     destino={"aba": apoio.LAMINAS["caminho"], "caminho": "diagnostico"})
        return _com_inicio(_de(r, tipo="sintoma", selo="Texto fixo. A IA não improvisa sobre sintomas.", **comum))
    # parece "previsão do tempo", não um item do guia; mas evidência clara de item vence esse sinal geral
    # ("o que é UNACON" lembra "o que é inflação")
    fora_do_assunto = social.tipo == "fora" and n1 < NOTA_FORA
    if not fora_do_assunto and direto:
        r = apoio.responder(apoio.item(id1))
        outros = [(f"Ver também: {apoio.POR_ID[i]['titulo']}", apoio.item(i)) for i, n in achados[1:] if n >= BAIXO][:2]
        resposta = _de(r, tipo="itens", selo=SELO_GUIA, candidatos=[id1], **comum)
        resposta.fala = "Pelo que você escreveu, isto parece ser o que você procura:\n\n" + r.fala
        resposta.botoes = outros + r.botoes
        return resposta
    if not fora_do_assunto and n1 >= BAIXO:
        candidatos = [i for i, n in achados if n >= BAIXO]
        linhas = "\n".join(f"- **{apoio.POR_ID[i]['titulo']}**: {apoio.POR_ID[i]['resumo']}." for i in candidatos)
        r = Resposta(fala="Não tenho certeza do que você procura. Encontrei estes itens do guia, e o primeiro é o que mais se parece:\n\n"
                          + linhas, expressao="explicando",
                     botoes=[(apoio.POR_ID[i]["titulo"], apoio.item(i)) for i in candidatos],
                     destino={"aba": apoio.LAMINAS["caminho"]})
        return _com_inicio(_de(r, tipo="palpites", selo=SELO_GUIA, candidatos=candidatos, **comum))

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
              "contra violência. Escolha uma porta, ou escreva de outro jeito. Se for sobre a sua saúde agora, procure a unidade "
              "de saúde; em emergência, ligue 192.")
    return _de(r, tipo="nada", selo="Nada foi inventado: o guia só mostra o que está no catálogo.", **comum)
