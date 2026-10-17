import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

# =====================================
# ENTENDIMENTO DA PERGUNTA (caixa "Pergunte à Lia", 10/2026)
#
# Por que existe: a caixa antiga (conversa.entender) pontuava palavras-
# chave e entendia só quem falava como o programador. "Tá piorando?",
# "morre muita gente?" ou "caroço no peito" não casavam com nada. O
# desenho abaixo vem do que deu certo no MISM3 (orientador de Rio Claro,
# docs/arquitetura_ia.md de lá), adaptado ao Escudo:
#
#   1. DESTINOS FECHADOS. A pergunta é ligada a uma de ~20 intenções que
#      o Escudo sabe responder (INTENCOES). Nunca inventa uma nova.
#   2. VOCABULÁRIO POPULAR escrito à mão para cada intenção (as frases
#      abaixo): é conhecimento do domínio, revisável linha a linha.
#   3. DOIS SINAIS somados: PALAVRAS (TF-IDF sobre radicais de 5 letras)
#      e LETRAS (TF-IDF sobre trechos de 3 a 5 letras, que aguenta erro
#      de digitação). Sem dependências além da biblioteca padrão.
#   4. CONFIANÇA. Nota alta e folga sobre a 2ª colocada: entende sozinho.
#      Senão, o Gemini recebe só a pergunta e a LISTA FECHADA e escolhe
#      uma (ou "nenhuma"); a escolha dele é conferida aqui. Sem Gemini,
#      ou sem confiança: devolve até 3 palpites para a pessoa escolher.
#      Nunca chuta.
#   5. SEGURANÇA primeiro: relato de violência, risco de vida ou
#      emergência de saúde não depende de nota nenhuma.
#
# Não usa LSA (MISM3 usa): com ~20 intenções o corpus é pequeno demais
# para aprender significado; esse papel fica com o Gemini na segunda
# chance. Medido por teste_entendimento.py contra a caixa antiga.
# =====================================


# ---------- texto ----------

def sem_acento(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def normalizar(texto):
    return " ".join(re.findall(r"[a-z0-9]+", sem_acento(texto)))


EXPRESSOES = [(re.compile(r"\bpor causa (de|do|da|dos|das)\b"), "devido a"),  # preposição, não a pergunta "qual a causa?"
              (re.compile(r"\boutros? estados?\b"), "interestadual"),   # "outro estado" não é "o Estado de SP"
              (re.compile(r"\bsao paulo\b"), "sp")]


def preparar(texto):
    """Normaliza e junta expressões que mudam de sentido quando separadas."""
    texto = normalizar(texto)
    for padrao, troca in EXPRESSOES:
        texto = padrao.sub(troca, texto)
    return texto


PARADAS = set(
    "a o as os um uma uns umas de da do das dos em na no nas nos por para pra pro com sem sobre entre ate ao aos e ou "
    "mas que se sou sao ser estou esta estao foi fui vai vou ter tenho tem tinha minha meu minhas meus sua seu "
    "suas seus porque preciso precisa quero quer queria posso pode fazer faco faz "
    "aqui ali la isso isto esse essa muito muita mais menos ja nao sim tambem so ainda eu me te lhe nos ela "
    "ele eles elas dele dela ver ha hoje agora gostaria algum alguma coisa coisas to ta tao vcs vc ne pois "
    "cancer canceres lia escudo".split())


def raiz(palavra):
    if len(palavra) > 3 and palavra.endswith("s") and not palavra.endswith("ss"):
        palavra = palavra[:-1]
    return palavra[:5]


def fichas(texto):
    return [raiz(p) for p in preparar(texto).split() if p not in PARADAS and (len(p) >= 2 or p.isdigit())]


def trechos(texto):
    saida = []
    for palavra in preparar(texto).split():
        if palavra in PARADAS:
            continue
        p = f" {palavra} "
        for n in (3, 4, 5):
            saida.extend(p[i:i + n] for i in range(len(p) - n + 1))
    return saida


# ---------- as intenções e o vocabulário popular ----------
# Cada intenção: id, descrição (é lida pelo Gemini na segunda chance) e frases do jeito que a pessoa fala.

INTENCOES = [
    {"id": "mais_aparece",
     "descricao": "quais cânceres têm mais internações; visão geral e ranking dos tipos de câncer",
     "frases": [
         "quais os cânceres mais comuns", "qual câncer mais interna", "qual câncer mais aparece nas mulheres",
         "ranking dos cânceres", "o que mais afeta as mulheres da cidade", "câncer mais frequente",
         "qual tem mais casos", "quantas internações por câncer", "visão geral dos dados", "resumo geral",
         "panorama", "me mostra um resumo", "quais doenças pesam mais", "o que mais internou mulheres",
         "qual o mais comum aqui", "o que lota mais o hospital", "resumão da situação", "quantas mulheres foram internadas", "total de internações",
         "quais tipos de câncer vocês acompanham", "qual a doença mais frequente", "maior número de internações",
         "qual câncer lidera", "o que mais acontece", "me dá um panorama", "quantos cânceres existem no painel"]},
    {"id": "evolucao",
     "descricao": "se as internações estão aumentando ou diminuindo ao longo dos anos; evolução e tendência histórica",
     "frases": [
         "está aumentando", "as internações estão crescendo", "cresceu ou caiu", "como evoluiu",
         "evolução ao longo dos anos", "tendência histórica", "subiu muito", "diminuiu nos últimos anos",
         "melhorou ou piorou", "tá piorando", "piorou", "melhorou", "a situação piorou", "aumentou", "histórico ano a ano", "mudou ao longo do tempo", "as internações estão subindo ou descendo", "as mulheres internadas estão aumentando",
         "série histórica", "o número de casos tá subindo", "o que mudou desde 2013", "está crescendo",
         "está caindo", "tendência de alta", "tá aumentando muito", "cresce quanto por ano",
         "como foram os últimos anos", "quanto aumentou", "ritmo de crescimento", "o que acontece com o passar dos anos"]},
    {"id": "futuro",
     "descricao": "previsão e projeção para os próximos anos; modelo preditivo; como deve ficar no futuro",
     "frases": [
         "como vai ficar", "previsão para os próximos anos", "como vai estar", "o que esperar até 2028", "projeção",
         "daqui a três anos", "vai aumentar no futuro", "tendência futura", "quantas internações em 2027",
         "estimativa para 2028", "previsão com inteligência artificial", "modelo preditivo", "machine learning",
         "prever o futuro", "como estará", "cenário futuro", "o que vem por aí", "olhar para frente",
         "previsão de internações", "vai piorar nos próximos anos", "a situação vai piorar", "vai ter mais gente internada daqui a pouco", "qual a previsão", "quanto será em 2027",
         "projetar", "o que podemos esperar", "futuro dos números", "predição", "projeção até 2028"]},
    {"id": "obitos",
     "descricao": "óbitos e letalidade hospitalar: quantas internações terminam em morte; qual câncer mais mata no hospital",
     "frases": [
         "quantas morrem", "qual câncer mais mata", "óbitos", "mortalidade", "morreram no hospital", "letalidade",
         "morre muita gente", "taxa de morte", "quantas mulheres morreram", "falecimentos", "gravidade",
         "chance de morrer na internação", "quantas mortes", "morte por câncer", "mortes no hospital",
         "o mais letal", "mais perigoso", "quantas não sobrevivem", "morrem muito", "número de mortes"]},
    {"id": "valores",
     "descricao": "valores hospitalares registrados no SIH/SUS; custo das internações; quanto o SUS gastou",
     "frases": [
         "quanto custa", "gasto do SUS", "quanto o SUS gastou", "valor das internações", "custo das internações",
         "dinheiro gasto", "o governo gasta", "quanto gasta", "quanto se paga por internação", "valor médio por internação", "é caro", "em reais",
         "quanto foi pago", "valor hospitalar", "o que o SUS paga", "quanto custa um tratamento",
         "gasto com câncer", "custos", "preço da internação", "os valores", "quais os valores", "valores do câncer", "quanto vale", "quanto sai cada internação", "financeiro"]},
    {"id": "tempo",
     "descricao": "tempo de internação, dias de permanência no hospital e ocupação de leitos",
     "frases": [
         "quanto tempo ficam internadas", "dias de internação", "permanência hospitalar", "ocupação de leitos",
         "tempo médio no hospital", "quantos dias no leito", "demora a internação", "leitos", "fica quantos dias", "as internações são longas", "internação demorada",
         "tempo de hospital", "quanto tempo dura uma internação", "dias no hospital", "tempo de permanência",
         "quantos dias de leito", "internadas por quanto tempo"]},
    {"id": "idade",
     "descricao": "faixa etária e idade das mulheres internadas, e como mudou ao longo dos anos",
     "frases": [
         "idade das mulheres", "faixa etária", "quem é mais afetada por idade", "mulheres jovens",
         "acima de 50 anos", "qual a idade média", "em que idade aparece", "idosas", "40 a 49 anos",
         "mudou a idade", "com quantos anos", "as mais novas", "mulheres mais velhas", "qual a idade",
         "grupo de idade", "jovens estão sendo internadas", "idade das internadas", "a partir de que idade"]},
    {"id": "estado",
     "descricao": "comparação da cidade com o Estado de São Paulo (ritmo de crescimento)",
     "frases": [
         "e o estado de são paulo", "comparado com SP", "estamos pior que o estado", "como estamos em relação ao estado",
         "ritmo do estado", "cidade e estado", "média estadual", "estamos acima da média de SP", "cresce mais rápido que o estado",
         "comparar com o resto do estado", "e em São Paulo", "comparação com o estado", "o estado cresce mais que a cidade",
         "somos diferentes do estado", "pior ou melhor que SP", "referência estadual", "como está o estado"]},
    {"id": "atencao",
     "descricao": "onde a cidade pode ter problema, o que merece atenção e prioridade no planejamento; radar do futuro; investimento",
     "frases": [
         "onde pode ter problema", "o que merece atenção", "prioridade", "onde investir", "quanto investir",
         "orçamento ideal", "planejamento", "o que devemos priorizar", "alerta", "radar", "onde agir",
         "para onde direcionar recursos", "preocupante", "políticas públicas", "o que a secretaria deve fazer",
         "gestão", "o que fazer a respeito", "onde a prefeitura deve olhar com mais cuidado", "o que a secretaria precisa priorizar", "qual câncer preocupa mais", "em que focar", "sinais de alerta",
         "devemos nos preocupar", "onde está o risco", "recomendação para a gestão", "ação para a prefeitura",
         "onde podemos ter problema nos próximos anos", "problema nos próximos anos", "quanto gastar", "onde colocar dinheiro", "o que precisa de atenção", "plano de ação"]},
    {"id": "fora_padrao",
     "descricao": "anos fora do padrão, picos, saltos e anomalias nos números",
     "frases": [
         "ano fora do padrão", "anomalia", "pico", "salto", "ano atípico", "algo estranho nos dados",
         "ano estranho", "deu um pulo", "outlier", "valores atípicos", "o que aconteceu em 2025",
         "teve algum ano diferente", "dispararam", "ano fora do normal", "por que um ano disparou", "o que aconteceu em um ano específico", "aumento repentino", "queda brusca",
         "algum ano acima do esperado", "ano anormal", "oscilação grande"]},
    {"id": "fluxo",
     "descricao": "mulheres de outros estados atendidas em SP e para onde vão as moradoras; fluxo de pacientes entre cidades e hospitais",
     "frases": [
         "mulheres de outros estados", "vêm de fora para se tratar", "pacientes de outras cidades",
         "para onde vão as moradoras", "quem vem de Minas", "Barretos recebe", "fluxo de pacientes",
         "migração para tratamento", "se tratam fora da cidade", "turismo de saúde", "referência regional",
         "atendem gente de fora", "mulheres que moram em outro estado", "vêm de outro estado se tratar", "pacientes de outros estados em São Paulo", "pacientes de outros estados", "de onde vêm as pacientes",
         "quantas vêm de fora", "tratamento em outra cidade", "pessoas de fora", "atendimento a quem mora fora",
         "os hospitais atendem mulheres de onde", "moradoras que se tratam em outras cidades"]},
    {"id": "completude",
     "descricao": "se os dados estão completos; meses que faltam na fonte; qualidade e confiabilidade dos números",
     "frases": [
         "os dados estão completos", "faltam meses", "falta dado", "dados incompletos", "ano incompleto",
         "qualidade dos dados", "posso confiar nos dados", "2025 está completo", "tem erro nos dados",
         "meses ausentes", "faltou mês", "o datasus não tem", "dá para confiar", "são confiáveis", "tem buraco nos dados",
         "faltam informações", "os números estão certos", "confiabilidade", "dados faltando",
         "por que alguns anos têm menos meses"]},
    {"id": "metodo",
     "descricao": "como os números são calculados, de onde vêm os dados, o que significa internação, limites da análise",
     "frases": [
         "como são calculados", "de onde vêm os dados", "qual a fonte", "metodologia", "o que significa internação",
         "é caso novo", "incidência", "o que é AIH", "o que é SIH", "datasus", "limitações", "como ler os gráficos",
         "como funciona o cálculo", "de onde tiram esses números", "fonte dos dados", "o que são internações",
         "internação é o mesmo que caso", "como foi feito", "explique o método", "sobre os dados",
         "o que esses dados não dizem", "o que mede", "o que essa análise não permite concluir", "taxa por 100 mil mulheres", "proporção da população", "por habitante", "per capita"]},
    {"id": "sobre_ia",
     "descricao": "como a inteligência artificial do Escudo funciona; o que é a Lia; que tecnologia o projeto usa",
     "frases": [
         "que IA vocês usam", "como funciona a inteligência artificial", "você é uma IA", "usa gemini",
         "como a Lia funciona", "quem é a Lia", "o que é machine learning aqui", "como você me entende",
         "você é um robô", "a Lia é um robô", "quem é você", "o gemini participa de que parte do sistema", "tecnologia usada", "o projeto usa IA", "que tipo de inteligência", "qual inteligência artificial", "você é uma pessoa", "quem criou você",
         "inteligência artificial do sistema", "como a previsão é feita", "o que é o modelo de previsão",
         "como você responde", "você inventa respostas", "você é confiável"]},
    {"id": "comparar_cidades",
     "descricao": "comparar a cidade com outra cidade ou com cidades parecidas",
     "frases": [
         "comparar com Campinas", "comparar cidades", "outra cidade", "cidades parecidas", "ranking de municípios",
         "como Rio Claro se compara", "comparar com Piracicaba", "cidades semelhantes", "e as outras cidades",
         "comparar com outro município", "somos melhores que a cidade vizinha", "como estão as cidades da região",
         "contra outra cidade", "como estão as cidades vizinhas", "comparar com municípios da região",
         "e a cidade ao lado", "como estamos perto das outras cidades"]},
    {"id": "onde_atendida",
     "descricao": "onde procurar atendimento: postos de saúde, hospitais, UPA, endereços e telefones de serviços da cidade",
     "frases": [
         "onde fazer mamografia", "onde tem hospital", "posto de saúde perto", "UBS", "qual hospital atende câncer",
         "unidades de saúde", "telefone do hospital", "como chegar no hospital", "UPA", "onde marcar exame",
         "centro de saúde", "CAPS", "pronto socorro", "endereço do posto", "endereço da unidade", "onde fica a UPA", "onde ser atendida",
         "onde posso me tratar", "onde procurar atendimento", "hospital mais perto", "onde fazer o preventivo",
         "onde consigo atendimento", "serviços de saúde da cidade", "onde fica o hospital", "clínica pelo SUS"]},
    {"id": "apoio",
     "descricao": "apoio a quem tem ou teve câncer: direitos, caminho do tratamento pelo SUS, rede oncológica, carretas, regulação, acesso a exames e cirurgia",
     "frases": [
         "recebi o diagnóstico", "recebi o resultado da biópsia", "fui diagnosticada e agora", "minha mãe vai começar a quimio e o que o SUS cobre", "meus direitos como paciente", "estou com câncer o que faço", "como conseguir tratamento pelo SUS", "meus direitos",
         "carreta da mamografia", "rede oncológica", "encaminhamento", "regulação", "FGTS", "quimioterapia",
         "como marcar mamografia pelo SUS", "exame preventivo gratuito", "apoio psicológico", "ajuda para mulher com câncer",
         "transporte para tratamento", "cirurgia de reconstrução da mama", "fui encaminhada e agora", "como prevenir",
         "tenho câncer", "minha mãe está com câncer", "quero fazer o exame", "tratamento do câncer",
         "estou em tratamento", "auxílio doença", "benefício para quem tem câncer", "preciso de ajuda com o tratamento",
         "como funciona o tratamento", "lista de espera para cirurgia", "como prevenir o câncer de mama",
         "como evitar o câncer",
         "acabei de descobrir um câncer", "descobri que tenho câncer e agora", "qual o primeiro passo depois do diagnóstico",
         "recebi a notícia de que é câncer", "minha mãe acabou de ser diagnosticada", "qual o caminho depois de descobrir o câncer",
         "como começar o tratamento", "por onde começo o tratamento do câncer", "fui diagnosticado com câncer",
         "hospital especializado em câncer", "hospital de referência para câncer", "contato de hospital oncológico",
         "onde fazer o tratamento do câncer", "hospital de referência em oncologia"]},
    {"id": "sintoma",
     "descricao": "pessoa descrevendo sintoma ou pedindo diagnóstico pessoal (caroço, nódulo, sangramento, dor); o Escudo não faz diagnóstico",
     "frases": [
         "estou com um caroço no seio", "será que é câncer", "senti um nódulo", "sangramento depois da menopausa",
         "tenho dor na mama", "quais os sintomas", "como saber se tenho câncer", "isso é câncer", "meu preventivo deu alterado",
         "caroço no peito", "corrimento estranho", "ferida que não cicatriza", "sinais do câncer", "apareceu uma mancha",
         "meu exame deu alterado", "estou com medo de ter câncer", "acho que estou com câncer", "mama endurecida",
         "mancha na pele que cresce", "sangramento fora da menstruação", "tosse que não passa", "me diga se é grave"]},
    {"id": "causa",
     "descricao": "pergunta pelo motivo ou causa de uma mudança, diferença ou resultado nos números; o Escudo detecta padrões mas não explica causas",
     "frases": [
         "qual a causa disso", "o que causa isso", "motivo dessa mudança", "qual o motivo", "o que justifica esses números",
         "de quem é a culpa", "o que provocou a mudança", "qual a razão", "o que está por trás disso",
         "isso acontece por quê", "o que está causando isso", "o que justifica essa diferença",
         "qual o fator responsável", "por que isso mudou", "por que mudou tanto", "por que isso aconteceu",
         "por que acontece", "qual a origem dessa diferença", "o que levou a isso", "causa do problema"]},
    {"id": "sem_dados",
     "descricao": "informação que o Escudo não tem: cor ou raça, renda, escolaridade, estadiamento, sobrevida, doenças associadas, HIV, tratamento ambulatorial",
     "frases": [
         "cor ou raça das pacientes", "qual a raça das mulheres", "etnia das internadas", "escolaridade das mulheres",
         "renda das pacientes", "estadiamento do tumor", "em que estágio chegam", "sobrevida depois do diagnóstico",
         "quantas sobreviveram", "taxa de sobrevivência", "mulheres com HIV", "doenças associadas", "obesidade e tabagismo das pacientes",
         "plano de saúde ou SUS", "quimioterapia e radioterapia ambulatorial", "tempo de espera para consulta", "diagnóstico precoce",
         "mutação genética BRCA", "tipo de tumor", "histórico familiar", "estado civil das pacientes", "profissão das internadas",
         "ranking de cidades com mais casos", "câncer proporcional ao número de habitantes",
         "casos por habitante", "qual cidade tem mais câncer proporcionalmente", "cidades com maior proporção de casos"]},
    {"id": "ajuda",
     "descricao": "pedido de ajuda para usar a caixa; o que a Lia sabe responder; o que perguntar",
     "frases": [
         "o que você faz", "como usar", "como funciona esta caixa", "ajuda", "me ajuda", "o que posso perguntar",
         "não sei o que perguntar", "quais perguntas posso fazer", "como te usar", "tutorial", "menu", "opções",
         "o que você sabe", "o que você consegue responder", "para que serve", "o que tem aqui", "por onde começo", "me explica como funciona"]},
]

# Exemplos do que NÃO é assunto do Escudo e que se parece com algum assunto dele (previsão do
# tempo x previsão de internações; cotação x custo). Entram na busca como a intenção "fora".
FORA = {"id": "fora", "descricao": "assunto que não tem relação com câncer feminino nem com o Escudo", "frases": [
    "previsão do tempo", "vai chover amanhã", "qual a temperatura hoje", "resultado do jogo", "quem ganhou o campeonato",
    "cotação do dólar", "preço da gasolina", "receita de bolo", "como fazer um prato", "me conta uma piada",
    "horóscopo de hoje", "qual signo combina comigo", "indicação de filme", "música para ouvir", "notícias de política",
    "em quem votar", "dever de casa de matemática", "como consertar o celular", "passagem de ônibus", "reserva de hotel",
    "como emagrecer rápido", "dieta da moda", "quanto custa um carro", "preço do aluguel", "traduzir uma frase",
    "melhor time de futebol", "tabela do campeonato", "que horas são", "que dia é hoje", "aprender a programar",
    "criar um site ou aplicativo", "declaração de imposto de renda", "o que é inflação", "taxa de juros", "eleições",
    "partido político", "religião e fé", "receita de comida", "restaurante perto", "série ou novela", "jogo de videogame"]}

IDS = [i["id"] for i in INTENCOES]
DESCRICOES = {i["id"]: i["descricao"] for i in INTENCOES}

# Rótulos curtos para os botões de palpite.
ROTULOS = {
    "mais_aparece": "O que mais aparece?", "evolucao": "Está aumentando?", "futuro": "Olhar para frente",
    "obitos": "Óbitos na internação", "valores": "Valores hospitalares", "tempo": "Tempo de internação",
    "idade": "Idade das mulheres", "estado": "Comparar com São Paulo", "atencao": "Onde podemos ter problema?",
    "fora_padrao": "Anos fora do padrão", "fluxo": "Mulheres de outros estados",
    "completude": "Os dados estão completos?", "metodo": "Como esses dados funcionam?",
    "sobre_ia": "Como a IA funciona?", "comparar_cidades": "Comparar com outra cidade",
    "onde_atendida": "Onde ser atendida", "apoio": "Apoio à mulher", "sintoma": "Estou com um sintoma",
    "ajuda": "O que posso perguntar?", "causa": "Por que mudou?", "sem_dados": "O que os dados não têm",
}
ROTULOS_POR_GATILHO = {"tratamento": "Quimio e radioterapia", "mortalidade_real": "Mortes por câncer (todas)", "polos": "Cidades que mais tratam"}  # fora do índice (ver _por_gatilho)
ROTULOS_TODOS = {**ROTULOS, **ROTULOS_POR_GATILHO}


# ---------- índice (palavras + letras) ----------

def _tfidf(contagem, idf):
    vetor = {t: (1 + math.log(c)) * idf.get(t, 0.0) for t, c in contagem.items() if t in idf}
    norma = math.sqrt(sum(v * v for v in vetor.values())) or 1.0
    return {t: v / norma for t, v in vetor.items()}


def _cos(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b[t] for t, v in a.items() if t in b)


class Indice:
    """Palavras e letras de cada frase do vocabulário. Pesos (palavras 0,45 / letras 0,55)
    e o peso da melhor frase x o texto inteiro da intenção foram escolhidos no conjunto de
    desenvolvimento de gabarito_perguntas.json."""

    PESO_PALAVRAS = 0.45
    PESO_FRASE = 0.3

    def __init__(self, intencoes):
        self.ids, self.frases = [], []
        self.todos = [item["id"] for item in intencoes]  # o universo deste índice (o do Escudo, o do Apoio...)
        for item in intencoes:
            for frase in item["frases"]:
                self.ids.append(item["id"])
                self.frases.append(frase)
        n = len(self.frases)
        df_p, df_c = Counter(), Counter()
        for frase in self.frases:
            df_p.update(set(fichas(frase)))
            df_c.update(set(trechos(frase)))
        self.idf_p = {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df_p.items()}
        self.idf_c = {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df_c.items()}
        self.frase_p = [_tfidf(Counter(fichas(f)), self.idf_p) for f in self.frases]
        self.frase_c = [_tfidf(Counter(trechos(f)), self.idf_c) for f in self.frases]
        self.doc_p, self.doc_c = {}, {}
        for item in intencoes:
            texto = " ".join(item["frases"])
            self.doc_p[item["id"]] = _tfidf(Counter(fichas(texto)), self.idf_p)
            self.doc_c[item["id"]] = _tfidf(Counter(trechos(texto)), self.idf_c)

    def notas(self, pergunta):
        """{intenção: nota de 0 a 1}. Mistura a melhor frase parecida com a intenção inteira."""
        qp = _tfidf(Counter(fichas(pergunta)), self.idf_p)
        qc = _tfidf(Counter(trechos(pergunta)), self.idf_c)
        if not qp and not qc:
            return {i: 0.0 for i in self.todos}
        melhor = {i: 0.0 for i in self.todos}
        for i, fp, fc in zip(self.ids, self.frase_p, self.frase_c):
            nota = self.PESO_PALAVRAS * _cos(qp, fp) + (1 - self.PESO_PALAVRAS) * _cos(qc, fc)
            if nota > melhor[i]:
                melhor[i] = nota
        saida = {}
        for i in self.todos:
            inteira = self.PESO_PALAVRAS * _cos(qp, self.doc_p[i]) + (1 - self.PESO_PALAVRAS) * _cos(qc, self.doc_c[i])
            saida[i] = self.PESO_FRASE * melhor[i] + (1 - self.PESO_FRASE) * inteira
        return saida


INDICE = Indice(INTENCOES + [FORA])

# Limiares escolhidos no conjunto de desenvolvimento (ver teste_entendimento.py).
NOTA_ALTA = 0.35       # a partir daqui, e com folga, entende sozinho
FOLGA = 0.07           # diferença mínima para a 2ª colocada
NOTA_BAIXA = 0.20      # abaixo disto não há palpite que valha
BONUS_OUTRA_CIDADE = 0.25
BONUS_ANO_FUTURO = 0.25
BONUS_POR_QUE = 0.12
NOTA_UNICA = 0.27      # candidato único: só uma intenção se parece com a pergunta, e com esta nota


# ---------- câncer, ano, tema ----------

CANCERES = [  # a ordem importa: "colo retal" antes de "colo do útero"
    ("COLORRETAL", r"colorretal|colo ?retal|intestin\w*|\bretos?\b|retal|\bcolon\b|colonoscopia"),
    ("COLO_UTERO", r"colo( do| de| uterino)? ?uter\w*|\buter\w*|cervical|cervix|\bcolo\b|preventivo|papanicola\w*|\bhpv\b"),
    ("MAMA", r"\bmamas?\b|mamograf\w*|\bseios?\b|\bpeitos?\b|mamari\w*"),
    ("PELE_NAO_MELANOMA", r"\bpele( nao melanoma)?\b|cutane\w*|\bnao melanoma\b"),
    ("PULMAO", r"pulm\w+"),
    ("OVARIO", r"ovari\w*"),
    ("TIREOIDE", r"tir?eoid\w*|tiroid\w*"),
]

# Cânceres que o Escudo NÃO acompanha: a pergunta é entendida, mas a resposta diz isso.
NAO_ACOMPANHADOS = {
    "melanoma": "melanoma", "estomago": "estômago", "figado": "fígado", "leucemia": "leucemia",
    "endometrio": "endométrio", "pancreas": "pâncreas", "cerebro": "cérebro", "bexiga": "bexiga",
    "rim": "rim", "boca": "boca", "esofago": "esôfago", "linfoma": "linfoma", "osso": "osso", "ossos": "osso",
    "garganta": "garganta", "laringe": "laringe", "vagina": "vagina", "vulva": "vulva", "prostata": "próstata",
    "sangue": "sangue", "cabeca": "cabeça e pescoço",
}


def detectar_cancer(pergunta, disponiveis=None):
    """(códigos citados na ordem em que aparecem, nome de câncer não acompanhado ou None).
    O trecho já reconhecido sai do texto antes de procurar o próximo: "colo retal" não
    vira também "colo do útero"."""
    texto = " " + normalizar(pergunta) + " "
    achados, restante = [], texto
    for codigo, padrao in CANCERES:
        m = re.search(padrao, restante)
        if m:
            achados.append((m.start(), codigo))
            restante = restante[:m.start()] + " " * (m.end() - m.start()) + restante[m.end():]
    achados.sort()
    codigos = []
    for _, c in achados:
        if c not in codigos and (disponiveis is None or c in disponiveis):
            codigos.append(c)
    nao = None
    for termo, nome in NAO_ACOMPANHADOS.items():
        if re.search(r"(?<![a-z])" + termo + r"(?![a-z])", restante):  # "pele não melanoma" já saiu do texto: não é melanoma
            nao = nome
            break
    return codigos, nao


def detectar_ano(pergunta):
    anos = re.findall(r"(?<![0-9])(20[1-3][0-9])(?![0-9])", normalizar(pergunta))
    return int(anos[0]) if anos else None


FOCO = re.compile(r"\b(esse|este|desse|deste|nesse|neste|dele|nele|isso|dessa|nessa|esta|essa)\b")


def cita_o_foco(pergunta):
    """'e esse câncer?' / 'desse câncer' -> a pessoa fala do que está em foco no painel."""
    return bool(FOCO.search(normalizar(pergunta))) and "cancer" in normalizar(pergunta).split()


# ---------- segurança e conversa social ----------

RISCOS = [
    ("suicidio", r"quero morrer|vou me matar|me matar|queria sumir|dormir e nao acordar|nao vale a pena viver|nao quero estar aqui|tirar (a )?minha vida|tirar a propria vida|acabar com (a )?minha vida|"
                 r"nao quero mais viver|nao aguento mais viver|melhor morrer|suicid\w+"),
    ("violencia", r"(marido|companheiro|namorado|ex|pai|padrasto|meu parceiro|ele) (me )?(bate|bateu|agride|agrediu|ameaca|ameacou|"
                  r"machuca|machucou|estuprou|abusa|abusou|persegue|esgana|enforcou|espancou)|"
                  r"me bate|me bateu|apanho|apanhei|apanhando|estou sofrendo violencia|sofro violencia|sofri violencia|"
                  r"fui estuprada|fui agredida|fui abusada|abusaram de mim|tenho medo do meu (marido|companheiro|namorado|ex)|"
                  r"me ameaca de morte|vai me matar|"
                  # formas que o teste humano de 17/10/2026 mostrou faltar: gerúndio, "tá me agredindo", voz passiva, "violência doméstica"
                  r"\b(marido|companheiro|namorado|ex|pai|padrasto|parceiro|esposo|noivo|ele)\b( \w+){0,4} (me )?(bat\w+|agred\w+|agress\w+|"
                  r"ameac\w+|machuc\w+|estupr\w+|abus\w+|persegu\w+|esgan\w+|enforc\w+|espanc\w+|xing\w+|humilh\w+)|"
                  r"\b(estou|to|ta|esta|fui|sendo|estava)\b( \w+){0,2} (agredid\w+|espancad\w+|estuprad\w+|abusad\w+|ameacad\w+|violentad\w+|perseguid\w+)|"
                  r"violencia domestica|tenho medo d(ele|o meu \w+)|me sinto em perigo em casa"),
    ("emergencia", r"passando mal|desmai\w+|convuls\w+|inconsciente|parou de respirar|sangramento (muito |bem )?(forte|intenso)|"
                   r"nao consigo respirar|falta de ar (forte|agora)|dor forte no peito|\binfarto\b|\bavc\b|(estou|esta|ta) sangrando (muito|bastante)|"
                   r"sangrando muito|engasgou|engasgad\w+|overdose"),
]

SOCIAL = set("oi oii oie ola opa bom boa dia tarde noite tudo bem td blz e ai obrigad obrigado obrigada valeu vlw tchau ate logo "
             "mais breve ok okay certo beleza legal entendi show perfeito muito muitissimo gracas a deus lia".split())
AGRADECIMENTO = re.compile(r"\bpel[ao]s? (ajuda|atencao|resposta|explicacao|paciencia)\b")


def eh_saudacao(texto):
    """Só conversa social ("olá lia, tudo bem?", "muito obrigada pela ajuda"): nenhuma palavra de conteúdo."""
    palavras = AGRADECIMENTO.sub(" ", texto).split()
    return bool(palavras) and len(palavras) <= 8 and all(p in SOCIAL for p in palavras)


def detectar_risco(pergunta):
    texto = normalizar(pergunta)
    for tipo, padrao in RISCOS:
        if re.search(padrao, texto):
            return tipo
    return None


# ---------- decisão ----------

@dataclass
class Entendimento:
    tipo: str                 # intencao | palpites | fora | risco | saudacao | vazio
    intencao: str = None
    cancer: str = None        # citado na pergunta (ou herdado, no seguimento)
    ano: int = None
    origem: str = "regras"    # regras | seguimento | explicar | composta | comparar_canceres | gemini | gemini_sem_apoio (só o Gemini apontou: vira palpite)
    nota: float = 0.0
    palpites: list = field(default_factory=list)   # [(intenção, nota)] da maior para a menor
    risco: str = None
    nao_acompanhado: str = None
    varios_canceres: bool = False
    cancer_citado: bool = False
    foco: bool = False        # "esse câncer": usar o câncer em foco no painel
    tambem: str = None        # pedido composto ("está aumentando e o que esperar?"): o segundo assunto, respondido junto


# ---------- conversa: "me explica isso melhor" e pedidos compostos ----------

# Assuntos de dados: os únicos que têm uma explicação simples (os de texto fixo já são texto fixo).
COM_NUMEROS = {"mais_aparece", "evolucao", "futuro", "obitos", "valores", "tempo", "idade", "estado", "atencao",
               "fora_padrao", "fluxo", "completude", "metodo", "tratamento", "mortalidade_real", "polos"}
# Pares que cabem juntos numa resposta segura. Outras combinações continuam virando palpites para a pessoa escolher.
PARES_SEGUROS = {frozenset(p) for p in (("evolucao", "futuro"), ("obitos", "valores"), ("evolucao", "estado"))}
CONFUSAO = re.compile(r"^(eu )?(nao entendi|nao compreendi|nao ficou claro|como assim|nao sei o que (isso )?quer dizer)\b")
PEDE_EXPLICAR = re.compile(r"\b(explica\w*|explique|detalha\w*|repete\w*)\b.*\b(isso|melhor|de novo|outro jeito|simples)\b"
                           r"|\b(quer dizer|significa)\b.*\bisso\b|\bo que isso (quer dizer|significa)\b"
                           r"|\b(fala|diz|conta|explica) de novo\b|\b(de outro jeito|mais simples)\b")


# Palavras que só pedem explicação. Qualquer outra palavra de conteúdo ("tendência", "AIH", "pulmão") significa que a
# frase traz um assunto próprio e não é "explica o que você acabou de dizer".
PALAVRAS_DE_EXPLICAR = set("""me eu a o e de do da que isso esse essa esses essas aquilo melhor novo outro jeito mais simples
    simples por favor pode poderia voce voces vc pra para um uma pouco explica explicar explique detalha detalhar detalhe repete
    repetir fala falar diz dizer conta contar quer significa nao entendi entender compreendi compreender ficou claro como assim
    resposta anterior disse falou sei em com ainda se tem tu""".split())


COMPARA_CANCERES = re.compile(r"\b(compar\w*|diferenca\w*|versus|vs|contra)\b")
PALAVRAS_DE_LUGAR = re.compile(r"\b(estado|sao paulo|sp|cidade|cidades|municipio|campinas|piracicaba|ribeirao)\b")


def _pede_comparar_canceres(texto, base, ano):
    """"Compare câncer de mama com o de colo do útero" / "mama com melanoma": comparar cânceres entre si (não cidades) é
    olhar todos lado a lado. O lugar na frase ("com o Estado") tira a pergunta daqui."""
    varios = base["varios_canceres"] or (base["cancer_citado"] and bool(base["nao_acompanhado"]))
    return bool(varios and ano is None and COMPARA_CANCERES.search(texto) and not PALAVRAS_DE_LUGAR.search(texto))


def _pede_explicacao(texto, nota_topo):
    """'me explica isso melhor', 'não entendi', 'como assim?': pedido curto de explicar a resposta anterior. Se a frase já
    traz um assunto por conta própria ("explica melhor como calculam a tendência"), não é isto."""
    palavras = texto.split()
    if len(palavras) > 9 or any(p not in PALAVRAS_DE_EXPLICAR for p in palavras):
        return False
    return bool(CONFUSAO.search(texto)) or (nota_topo < NOTA_ALTA and bool(PEDE_EXPLICAR.search(texto)))


def _seguimento(pergunta, memoria, codigos, ano):
    """'e de mama?', 'e em 2027?': pergunta curta que só traz um câncer ou um ano
    continua o assunto anterior."""
    if not memoria or not memoria.get("intencao"):
        return False
    return len(fichas(pergunta)) <= 4 and (len(codigos) == 1 or ano is not None)


def sem_nomes_de_cidade(pergunta, cidade=None, outras=()):
    """O nome da cidade do painel não diz o assunto ("como Rio Claro está?" não é "comparar
    cidades"): sai da pergunta. O nome de OUTRA cidade vira "cidade", que é o que importa
    ("comparar com Campinas" = "comparar com cidade")."""
    texto = " " + normalizar(pergunta) + " "
    citou_outra = False
    for nome in sorted(outras, key=len, reverse=True):
        chave = " " + normalizar(nome) + " "
        if chave.strip() and chave in texto:
            texto = texto.replace(chave, " cidade ")
            citou_outra = True
    if cidade:
        texto = texto.replace(" " + normalizar(cidade) + " ", " ")
    return texto.strip(), citou_outra


# Dois assuntos que entram só por gatilho explícito (não pelo índice de palavras): "morrem de câncer" e "quantas mulheres" são frases
# de óbitos e de internações, e um vocabulário compartilhado tiraria acertos dos assuntos antigos (medido: 6 perguntas mudavam).
# tratamento = quimio/radio ambulatoriais (SIA); mortalidade_real = mortes por câncer em qualquer lugar (SIM).
GATILHO_TRATAMENTO = re.compile(r"\b(quimio\w*|radio(terapia)?|apacs?|ambulatorial)\b")
CONTA_TRATAMENTO = re.compile(r"\b(quantas|quantos|volume|numero de|total de|sessoes|estagio|estadiamento|raca|cor)\b")
PESSOAL_TRATAMENTO = re.compile(r"\b(minha|meu|vou|vai comecar|cobre|direito\w*|peruca|onde (fazer|faco)|preciso|medo|dor|efeito\w*)\b")
GATILHO_MORTES = re.compile(r"\b(fora do hospital|em casa|via publica|na rua|declaracao de obito|todos os lugares|mortalidade real|"
                            r"dentro e fora|(pelo|no|do) sim)\b")
GATILHO_POLOS = re.compile(r"\b((cidades?|municipios?) que mais (tratam|atendem|recebem|internam)|polos? de (tratamento|atendimento)|"
                           r"onde (mais )?(se )?(tratam|internam|atendem)|cidades? de referencia|"
                           r"(casos|pacientes|mulheres) (tratad\w+|atendid\w+) (nas|nos|em) cidades)\b")
PALAVRA_MORTE = re.compile(r"\b(morr\w+|obito\w*|mort\w+|mortalidade)\b")


def _por_gatilho(texto):
    """'tratamento' ou 'mortalidade_real' quando a pergunta traz o gatilho dele; None nos outros casos."""
    norm = normalizar(texto)
    if GATILHO_TRATAMENTO.search(norm) and CONTA_TRATAMENTO.search(norm) and not PESSOAL_TRATAMENTO.search(norm):
        return "tratamento"
    if GATILHO_MORTES.search(norm) and PALAVRA_MORTE.search(norm):
        return "mortalidade_real"
    if GATILHO_POLOS.search(norm):
        return "polos"
    return None


def compreender(pergunta, disponiveis=None, memoria=None, classificar=None, cidade=None, outras_cidades=(),
                ano_dados=None):
    """Entende a pergunta. `disponiveis`: cânceres que a cidade tem. `memoria`:
    {"intencao","cancer"} da resposta anterior. `classificar`: função do Gemini
    (pergunta, opções) -> {"intencao", "cancer"} ou None; só é chamada se as regras
    não bastarem. `cidade` e `outras_cidades`: nomes, ver sem_nomes_de_cidade. `ano_dados`: último ano
    com dados; uma pergunta com ano depois dele é sobre o futuro."""
    if not pergunta or not pergunta.strip():
        return Entendimento("vazio")
    risco = detectar_risco(pergunta)
    if risco:
        return Entendimento("risco", risco=risco, origem="regras")
    texto = normalizar(pergunta)
    if eh_saudacao(texto):
        return Entendimento("saudacao")

    codigos, nao = detectar_cancer(pergunta, disponiveis)
    ano = detectar_ano(pergunta)
    base = dict(cancer=codigos[0] if len(codigos) == 1 else None, ano=ano, nao_acompanhado=nao,
                varios_canceres=len(codigos) > 1, cancer_citado=bool(codigos), foco=cita_o_foco(pergunta))
    texto_busca, citou_outra = sem_nomes_de_cidade(pergunta, cidade, outras_cidades)
    if (memoria and memoria.get("cancer") and base["cancer"] is None and not base["varios_canceres"] and not base["foco"]
            and len(fichas(pergunta)) <= 4 and re.match(r"^\s*(e|mas|agora|tambem|entao)\b", sem_acento(pergunta))):
        base["cancer"] = memoria["cancer"]  # "e no estado?" depois de uma resposta sobre a mama continua na mama
    notas = INDICE.notas(texto_busca)
    if citou_outra and "estado" not in texto_busca.split():
        notas["comparar_cidades"] += BONUS_OUTRA_CIDADE  # citar outra cidade quase sempre é comparar
    if ano is None and re.match(r"^\s*(por que|porque|pq|por qu[eê])\b", sem_acento(pergunta)):
        notas["causa"] += BONUS_POR_QUE  # "por que ...?" sem ano é pergunta de causa, não de números
    if ano and ano_dados and ano > ano_dados:
        notas["futuro"] += BONUS_ANO_FUTURO  # "em 2028" depois de dados até 2025 só pode ser projeção
    if (memoria and memoria.get("intencao") in COM_NUMEROS and not codigos and ano is None
            and _pede_explicacao(texto, max(v for k, v in notas.items() if k != "fora"))):
        # "me explica isso melhor" depois de uma resposta de dados: explica a resposta anterior (a mesma, em palavras simples)
        return Entendimento("intencao", intencao=memoria["intencao"], origem="explicar",
                            **{**base, "cancer": memoria.get("cancer")})
    if _pede_comparar_canceres(texto, base, ano):
        return Entendimento("intencao", intencao="mais_aparece", origem="comparar_canceres", **base)
    gatilho = _por_gatilho(texto)
    if gatilho:
        return Entendimento("intencao", intencao=gatilho, origem="regras", **base)
    nota_fora = notas.pop("fora")
    ordem = sorted(notas.items(), key=lambda kv: -kv[1])
    (primeira, n1), (_, n2) = ordem[0], ordem[1]
    palpites = [(i, round(n, 3)) for i, n in ordem[:3] if n >= NOTA_BAIXA]
    if nota_fora > n1 and not base["cancer_citado"]:  # parece mais com "previsão do tempo" do que com qualquer assunto
        return Entendimento("fora", nota=n1, palpites=[], **base)

    # 1) seguimento: só um câncer ou um ano, depois de uma resposta -> mesmo assunto
    if n1 < NOTA_ALTA and _seguimento(pergunta, memoria, codigos, ano):
        return Entendimento("intencao", intencao=memoria["intencao"], origem="seguimento", nota=n1,
                            palpites=palpites, **{**base, "cancer": base["cancer"] or memoria.get("cancer")})

    # 2) as regras entendem sozinhas: nota alta e folga, ou um candidato único
    if (n1 >= NOTA_ALTA and (n1 - n2) >= FOLGA) or (n1 >= NOTA_UNICA and n2 < NOTA_BAIXA):
        return Entendimento("intencao", intencao=primeira, nota=n1, palpites=palpites, **base)

    # 2b) pedido composto ("está aumentando e o que posso esperar?"): dois assuntos que cabem juntos e mais nada perto
    if (len(ordem) >= 3 and frozenset((ordem[0][0], ordem[1][0])) in PARES_SEGUROS and ordem[1][1] >= NOTA_UNICA
            and ordem[2][1] <= ordem[1][1] - FOLGA):
        return Entendimento("intencao", intencao=ordem[0][0], tambem=ordem[1][0], origem="composta", nota=n1,
                            palpites=palpites, **base)

    # 3) segunda chance com o Gemini (lista fechada); o que ele devolver é conferido
    if classificar is not None:
        try:
            resposta = classificar(pergunta, [(i, DESCRICOES[i]) for i in IDS])
        except Exception:
            resposta = None
        if isinstance(resposta, dict):
            escolhida = resposta.get("intencao")
            if escolhida in IDS:
                cancer = base["cancer"]
                if cancer is None and not base["varios_canceres"]:
                    sugerido = resposta.get("cancer")
                    if isinstance(sugerido, str) and sugerido in dict(CANCERES) and (disponiveis is None or sugerido in disponiveis):
                        cancer = sugerido
                dados = {**base, "cancer": cancer, "cancer_citado": base["cancer_citado"]}
                if escolhida in {i for i, _ in palpites}:  # o Gemini e a busca local apontam o mesmo assunto: responde
                    return Entendimento("intencao", intencao=escolhida, origem="gemini", nota=n1, palpites=palpites, **dados)
                # Só o Gemini apontou (a busca local não tem esse assunto entre os palpites, ou não achou nada parecido):
                # um id válido ainda pode ser o assunto errado, e resposta errada sem aviso é o pior erro. Pergunta à pessoa.
                sugestoes = [(escolhida, 0.0)] + palpites
                return Entendimento("palpites", origem="gemini_sem_apoio", nota=n1, palpites=sugestoes[:3], **dados)
            if escolhida in ("nenhuma", "nenhum", None):
                return Entendimento("fora", nota=n1, palpites=[], **base)

    # 4) sem confiança: palpites para a pessoa escolher; sem nada parecido, fora do assunto
    if palpites and n1 >= NOTA_BAIXA:
        return Entendimento("palpites", nota=n1, palpites=palpites, **base)
    return Entendimento("fora", nota=n1, palpites=[], **base)
