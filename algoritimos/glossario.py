import re
import unicodedata

# =====================================
# GLOSSÁRIO DA LIA (10/2026): o que significa cada termo técnico que aparece no painel e nas respostas.
#
# Pergunta que faltava (autor, 18/10/2026): "o que são APACs?", "qual o preço da diária?". Texto FIXO, escrito pelo projeto: a IA
# não improvisa definição. Cada termo diz o que ele é e como o Escudo o usa (inclusive o que o Escudo NÃO calcula).
# Entra por gatilho em entendimento.compreender (como tratamento/polos): só quando a pergunta pede o significado de um termo
# conhecido, então não muda o que a busca por assunto já respondia.
#
# Termos de que a resposta "Como esses dados funcionam?" já cuida (AIH, SIH, internação, caso novo, incidência, DATASUS,
# taxa por 100 mil) ficam fora daqui de propósito: o assunto `metodo` continua respondendo.
# =====================================


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


# id: (rótulo, [nomes que a pessoa pode usar], definição, como o Escudo usa)
TERMOS = {
    "apac": (
        "APAC",
        ["apac", "apacs", "autorizacao de procedimento ambulatorial", "autorizacao de procedimentos ambulatoriais",
         "autorizacao de procedimentos de alta complexidade", "autorizacao de procedimento de alta complexidade",
         "apac onco", "apac onco exclusiva"],
        "**APAC** (*Autorização de Procedimento Ambulatorial*; o nome aparece com pequenas variações nos documentos do Ministério da "
        "Saúde) é o documento que o SUS usa para **registrar os atendimentos e tratamentos feitos sem internação**, permitindo "
        "acompanhar e financiar esses procedimentos. Na oncologia, é por meio das APACs que se registram, por exemplo, a "
        "**quimioterapia** e a **radioterapia**. As APACs ficam no **SIA/SUS** (sistema de informações ambulatoriais), não no SIH "
        "(internações).",
        "Quando a Lia fala de APACs, são **registros, não mulheres**: a mesma mulher pode ter várias APACs ao longo do "
        "tratamento. Elas mostram o tratamento ambulatorial, que as internações do SIH não enxergam. Em 2026 o Ministério da "
        "Saúde também regulamentou a *APAC Onco Exclusiva*, que passa a registrar à parte os medicamentos oncológicos; a "
        "implantação é gradual e o Escudo ainda não usa esse registro. (Fonte da explicação: Instituto Oncoguia, 13/07/2026, "
        "sobre as portarias do Ministério da Saúde.)"),
    "sia": (
        "SIA/SUS",
        ["sia", "sia sus", "sistema de informacoes ambulatoriais"],
        "O **SIA/SUS** é o *Sistema de Informações Ambulatoriais* do SUS: registra o atendimento que **não exige internação**, como "
        "consultas, exames, mamografias, quimioterapia e radioterapia (estas, por meio das APACs).",
        "O Escudo usa o SIA só para o tratamento por quimio e radioterapia. A parte principal do painel vem do SIH, que registra "
        "internações."),
    "sim": (
        "SIM",
        ["sim", "sim sus", "sistema de informacoes sobre mortalidade", "sistema de informacao sobre mortalidade"],  # "sim" só com pedido de significado (ver AMBIGUOS)
        "O **SIM** é o *Sistema de Informações sobre Mortalidade*: reúne as **declarações de óbito**, aconteçam no hospital, em casa "
        "ou na rua.",
        "É diferente do que o painel mostra como *óbitos durante a internação*, que só contam mortes dentro do hospital. Os dois "
        "números não se subtraem: vêm de sistemas diferentes."),
    "cnes": (
        "CNES",
        ["cnes", "cadastro nacional de estabelecimentos de saude"],
        "O **CNES** é o *Cadastro Nacional de Estabelecimentos de Saúde*: o cadastro oficial de hospitais, postos, clínicas e "
        "laboratórios. Cada estabelecimento tem um código de 7 dígitos.",
        "O Escudo usa o código CNES para saber em qual hospital a internação aconteceu e para mostrar endereço e telefone dos "
        "serviços. Estar no cadastro não significa que há vaga ou que o serviço está funcionando hoje."),
    "cid": (
        "CID",
        ["cid", "cid 10", "cid10", "classificacao internacional de doencas"],
        "A **CID** é a *Classificação Internacional de Doenças*: o código que identifica o diagnóstico. O câncer de mama, por "
        "exemplo, fica na faixa C50.",
        "O Escudo agrupa as internações pelo diagnóstico principal registrado na internação (a CID), separando os 7 tipos de "
        "câncer que acompanha."),
    "valor_hospitalar": (
        "Valor hospitalar registrado",
        ["valor hospitalar", "valor hospitalar registrado", "valores hospitalares", "valores hospitalares registrados",
         "valor registrado", "val tot", "valor total da internacao", "valor das internacoes"],
        "O **valor hospitalar registrado** é a soma do valor total de cada internação (AIH) no SIH/SUS. Cada valor reúne serviços "
        "hospitalares, serviços profissionais e procedimentos.",
        "**Não é orçamento do município nem o custo total do tratamento**: não inclui, por exemplo, a quimioterapia e a "
        "radioterapia feitas sem internação. É o que o SIH registrou, nada mais."),
    "diaria": (
        "Diária de internação",
        ["diaria", "diarias", "diaria de internacao", "diarias de internacao", "preco da diaria", "valor da diaria",
         "custo da diaria", "quanto custa a diaria", "preco da diaria de internacao", "valor da diaria de internacao"],
        "A **diária de internação** é cada dia que a paciente passa internada.",
        "O Escudo mostra os **dias de permanência** e o **valor hospitalar registrado**, mas **não calcula nem informa o preço da "
        "diária**. O SUS não paga a internação só por diária: o valor de cada internação reúne serviços hospitalares, serviços "
        "profissionais e procedimentos. Dividir o valor pelos dias dá apenas uma **média** que mistura tudo isso; não é uma "
        "tabela de preço."),
    "permanencia": (
        "Dias de permanência",
        ["dias de permanencia", "permanencia media", "permanencia", "tempo de permanencia", "tempo medio de internacao",
         "media de dias"],
        "**Dias de permanência** são os dias em que a paciente ficou internada. A **permanência média** é o total de dias dividido "
        "pelo número de internações.",
        "É uma média: uma internação muito longa puxa o número para cima. Ela mostra quanto tempo de leito cada tipo de câncer "
        "costuma ocupar, não a gravidade de cada caso."),
    "letalidade": (
        "Letalidade hospitalar",
        ["letalidade", "letalidade hospitalar", "taxa de letalidade"],
        "A **letalidade hospitalar** é a parcela das internações que terminaram em **óbito durante a internação** (óbitos divididos "
        "por internações).",
        "**Não é a mortalidade da doença** nem o risco de uma mulher morrer de câncer: só conta o que aconteceu dentro do hospital, "
        "e quem morre em casa ou em outro serviço não aparece."),
    "obito_internacao": (
        "Óbito durante a internação",
        ["obito durante a internacao", "obitos durante a internacao", "obito na internacao", "obitos na internacao",
         "morte durante a internacao"],
        "**Óbito durante a internação** é a morte registrada no SIH, na própria internação.",
        "Não inclui mortes fora do hospital. Para as mortes por câncer em qualquer lugar existe o SIM, que mostra um retrato "
        "diferente."),
    "projecao": (
        "Projeção de tendência",
        ["projecao", "projecao de tendencia", "projecoes"],
        "A **projeção de tendência** continua para frente o ritmo observado nos anos anteriores e mostra uma faixa que vem do erro "
        "que o próprio método teve ao tentar acertar o passado.",
        "É um exercício, **não uma previsão de casos novos**: mostra para onde as *internações* caminhariam se nada mudasse. "
        "Quando o método não acerta melhor do que repetir o último ano, o Escudo avisa; sem anos suficientes, não projeta."),
    "fora_padrao": (
        "Ano fora do padrão",
        ["ano fora do padrao", "anos fora do padrao", "fora do padrao", "ano atipico", "anos atipicos", "atipico"],
        "**Ano fora do padrão** é um ano em que o número ficou muito acima ou muito abaixo do que a tendência esperava.",
        "O Escudo **aponta onde olhar, não explica o porquê**. Em ano com poucos meses na fonte, a estimativa é menos firme e "
        "o aviso aparece junto."),
    "ritmo": (
        "Ritmo de crescimento",
        ["ritmo de crescimento", "ritmo", "variacao ao ano", "crescimento ao ano", "crescimento anual"],
        "O **ritmo de crescimento** é o quanto o número varia, em média, por ano, ao longo do período.",
        "Serve para comparar a cidade com o Estado e com outras cidades sem depender do tamanho de cada uma."),
    "meses_ausentes": (
        "Meses ausentes",
        ["meses ausentes", "mes ausente", "meses que faltam", "meses faltando", "mes vazio", "meses nao oferecidos", "ajuste de meses"],
        "O DATASUS **não oferece todos os meses** de todos os anos. Um mês ausente na fonte **não é zero**: é um mês sem dado.",
        "Para comparar anos, o Escudo usa a média dos meses disponíveis multiplicada por 12; os totais do período usam só o que "
        "foi realmente registrado. Anos com poucos meses aparecem marcados na régua e nos avisos."),
    "residencia_hospital": (
        "Residência x hospital",
        ["municipio de residencia", "onde a mulher mora", "municipio do hospital", "residencia x hospital", "por residencia"],
        "O painel conta de duas formas: pela **cidade onde a mulher mora** (residência) e pela **cidade do hospital** onde foi "
        "atendida.",
        "A cidade escolhida usa a residência. Já o Estado conta o atendimento nos hospitais de SP, inclusive de mulheres de outros "
        "estados. Por isso uma cidade com hospital de referência pode tratar muito mais do que mora nela."),
    "unacon_cacon": (
        "UNACON e CACON",
        ["unacon", "unacons", "cacon", "cacons", "habilitacao em oncologia", "habilitado em oncologia", "hospital habilitado"],
        "**UNACON** (Unidade de Assistência de Alta Complexidade em Oncologia) e **CACON** (Centro de Assistência de Alta "
        "Complexidade em Oncologia) são habilitações do Ministério da Saúde para hospitais que tratam câncer pelo SUS. O CACON "
        "reúne mais serviços e é referência para os vários tipos de câncer.",
        "A lista oficial de SP tem 80 estabelecimentos habilitados (habilitação 2023). Estar na lista **não é ter vaga**: o "
        "acesso é pela regulação."),
    "rras_drs": (
        "RRAS e DRS",
        ["rras", "drs", "regiao de saude", "rede regional de atencao a saude", "departamento regional de saude"],
        "**RRAS** (Rede Regional de Atenção à Saúde) e **DRS** (Departamento Regional de Saúde) são as divisões do Estado de São "
        "Paulo em regiões de saúde. Elas organizam quais cidades se encaminham para quais hospitais.",
        "Rio Claro está na região de Piracicaba (RRAS 14). O Escudo não tem a lista completa de cidade por região e prefere "
        "não chutar a região de uma cidade."),
    "regulacao": (
        "Regulação",
        ["regulacao", "regulacao de vagas", "cross", "siresp", "central de regulacao"],
        "A **regulação** é o sistema que organiza as vagas de consultas, exames e tratamentos do SUS. O pedido feito pela unidade "
        "de saúde entra numa fila (no Estado, pelo SIRESP/CROSS) e a vaga é definida por critérios de necessidade.",
        "Por isso um hospital de referência não é porta de entrada: o caminho normal começa na unidade de saúde. O Apoio à mulher "
        "explica como acompanhar a fila."),
    "ubs_usf": (
        "UBS e USF",
        ["ubs", "usf", "unidade basica de saude", "unidade de saude da familia", "posto de saude"],
        "A **UBS** (Unidade Básica de Saúde) e a **USF** (Unidade de Saúde da Família) são os postos de saúde do bairro, a "
        "**porta de entrada do SUS**: consultas, preventivo, pedido de mamografia e encaminhamento.",
        "O Apoio à mulher e a página Onde ser atendida mostram as unidades da cidade, com telefone e como chegar quando o "
        "cadastro tem."),
    "sus": (
        "SUS",
        ["sus", "sistema unico de saude"],
        "O **SUS** é o *Sistema Único de Saúde*: o sistema público de saúde do Brasil, gratuito e para todas as pessoas.",
        "Todos os dados do painel são do SUS: internações pagas pelo SUS (SIH) e, em alguns assuntos, atendimentos ambulatoriais "
        "(SIA). Atendimento particular ou por convênio não aparece."),
    "ibge": (
        "IBGE",
        ["ibge", "instituto brasileiro de geografia e estatistica", "censo", "censo 2022"],
        "O **IBGE** é o *Instituto Brasileiro de Geografia e Estatística*, que faz o Censo e informa a população de cada município.",
        "O Escudo usa a população de mulheres do Censo 2022 para calcular as taxas **por 100 mil mulheres** e a localização do centro "
        "de cada município para as distâncias em linha reta."),
    "inca": (
        "INCA",
        ["inca", "instituto nacional de cancer"],
        "O **INCA** é o *Instituto Nacional de Câncer*, do Ministério da Saúde, referência em prevenção, rastreamento e controle do "
        "câncer no Brasil.",
        "O Escudo cita as páginas e orientações do INCA como fonte oficial; o que o painel calcula vem dos dados de internação."),
    "leito": (
        "Leito e dias de leito",
        ["leito", "leitos", "dias de leito", "dia de leito", "leito dia"],
        "**Leito** é a cama de hospital usada para internação. **Dias de leito** são os dias de internação somados.",
        "Quando o Escudo fala em mais dias de leito, é a soma dos dias de permanência das internações: mostra quanta ocupação "
        "hospitalar o número de internações representa, não a gravidade dos casos."),
    "teste_acerto": (
        "Teste de acerto (backtest)",
        ["teste de acerto", "backtest", "back test", "erro medido", "teste de acerto da projecao"],
        "O **teste de acerto** (*backtest*) esconde dos modelos os últimos anos, pede que eles projetem esses anos e compara com "
        "o que realmente aconteceu. O erro medido dá a faixa da projeção.",
        "O Escudo compara cada método com a regra simples de repetir o último ano; se não for melhor, avisa, e sem anos "
        "suficientes não projeta."),
    "estadiamento": (
        "Estadiamento",
        ["estadiamento", "estadio", "estagio do cancer", "estagio da doenca"],
        "**Estadiamento** é a classificação do quanto a doença está avançada quando é diagnosticada.",
        "O Escudo mostra apenas se o estadiamento foi **informado ou não** nos registros de quimio e radioterapia; ele não "
        "nomeia nem interpreta estágios."),
}

_NOMES = []
for _id, (_rotulo, _nomes, _def, _uso) in TERMOS.items():
    for _n in _nomes:
        _NOMES.append((normalizar(_n), _id))
_NOMES.sort(key=lambda x: -len(x[0]))  # nomes longos primeiro ("valor hospitalar registrado" antes de "valor registrado")
_REGEX_NOMES = [(re.compile(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])"), i) for n, i in _NOMES]

PEDE_DEFINICAO = re.compile(
    r"\b(o que (e|sao|significa|significam|quer dizer|querem dizer|quer dizer a sigla)|que (e|sao) (isso|esse|essa|esses|essas|a sigla)"
    r"|significado|definicao|defina|define|qual (e )?o significado|me explica(r)? o que (e|sao)|explique o que (e|sao)"
    r"|nao sei o que (e|sao|significa)|nao entendi o que (e|sao|significa)|(significa|significam)( o que)?|sigla"
    r"|(qual|quais) (e |sao )?(a |as )?diferencas? entre"
    r"|(qual|quanto) (e )?(o )?(preco|valor|custo|custa) (da|das|de cada) diarias?|quanto custa (a|uma) diarias?)\b")
# Jeitos curtos de pedir o significado de uma SIGLA ("oq é unacon", "me explica cacon", "para que serve a APAC"). Só valem para siglas
# (SIGLAS_SOZINHAS): "me explica a tendência" é pergunta de dados e não pode virar definição.
PEDE_SIGLA = re.compile(r"\b(oq|oque|o q|que que|me explica(r)?|me explique|explica(r)?|explique|(para|pra) que serve|serve para que|quero saber|queria saber)\b")
LIGACOES = {"e", "ou", "x", "vs", "versus", "e/ou", "a", "o", "as", "os", "da", "do", "das", "dos", "uma", "um", "sigla", "siglas", "de"}
# Só estas siglas valem SOZINHAS ("APAC"): as outras expressões ("anos fora do padrão", "permanência média", "sim") também são
# perguntas de dados ou palavras comuns, e só viram definição quando a pessoa pede o significado ("o que é ...").
SIGLAS_SOZINHAS = {"apac", "apacs", "sia", "sia sus", "cnes", "cid", "cid 10", "cid10", "unacon", "unacons", "cacon", "cacons",
                   "rras", "drs", "ubs", "usf", "siresp", "sus", "ibge", "inca"}


def achar_termos(pergunta, maximo=3):
    """Ids dos termos do glossário cujo significado a pergunta pede ([] se não for esse tipo de pergunta).
    Pede significado quando há uma expressão como "o que é / significa / quer dizer" junto do termo, ou quando a pergunta é só o
    termo ("APAC")."""
    texto = normalizar(pergunta)
    if not texto:
        return []
    pede = bool(PEDE_DEFINICAO.search(texto))
    achados, nomes_achados, resto = [], set(), texto
    for (regex, id), nome in zip(_REGEX_NOMES, [n for n, _ in _NOMES]):
        m = regex.search(resto)
        if m:
            if id not in [a for _, a in achados]:
                achados.append((m.start(), id))
            nomes_achados.add(nome)
            resto = resto[:m.start()] + " " * (m.end() - m.start()) + resto[m.end():]  # não conta o mesmo trecho duas vezes
    if not achados:
        return []
    achados.sort()
    if pede or (nomes_achados <= SIGLAS_SOZINHAS and PEDE_SIGLA.search(texto)):
        return [id for _, id in achados][:maximo]
    # sem pedido explícito: só se a pergunta é a própria sigla, ou siglas ligadas por "e"/"ou" ("APAC", "UNACON e CACON")
    so_o_termo = (len(texto.split()) <= 6 and not [w for w in resto.split() if w not in LIGACOES]
                  and nomes_achados <= SIGLAS_SOZINHAS)
    return [id for _, id in achados][:maximo] if so_o_termo else []


def responder_termos(ids):
    """Texto da resposta (markdown) para uma lista de ids."""
    partes = []
    for id in ids:
        _, _, definicao, uso = TERMOS[id]
        partes.append(f"{definicao}\n\n**No Escudo:** {uso}")
    return "\n\n---\n\n".join(partes)


def rotulos(ids):
    return [TERMOS[i][0] for i in ids]
