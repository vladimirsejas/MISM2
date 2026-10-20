from lia import INICIO, Resposta

# =====================================
# APOIO À MULHER — "Encontre um caminho" (combinado com o autor, 09/2026)
#
# Outras lâminas, SEPARADAS do painel de estudo da doença
# (dashboard/app.py continua igual). Aqui a pergunta é outra: "onde a
# mulher encontra ajuda?". A lógica, de cima para baixo:
#   Estado de SP (portal da Saúde, rede oncológica, regulação,
#   carretas) -> o que é útil de verdade para a mulher -> a Lia
#   apresenta, por 8 portas (Câncer de mama, Colo do útero,
#   Diagnóstico, Regulação, Tratamento, Rede oncológica, Direitos e
#   acesso, Preciso de ajuda -- "em que ponto você está?").
# Hospitais e Carretas são recursos, com lâmina própria. Cidades NÃO
# viram lâmina: Campinas, Ribeirão Preto, Rio Preto, Piracicaba etc.
# são fontes de itens. Exceções combinadas com o autor: Rio Claro (a
# cidade do trabalho, com mais detalhe) e Barretos (Hospital de Amor).
#
# Regras deste catálogo:
#   - cada item tem FONTE (página oficial), data em que foi conferido
#     e, quando for o caso, o que ainda falta confirmar ("confirmar");
#   - nada de endereço, telefone ou regra inventada; na dúvida, o item
#     sai ou entra marcado para confirmar;
#   - cada item tem UMA casa (a lâmina dele); os caminhos só apontam
#     para os itens de Rio Claro e Barretos, sem repetir;
#   - a Lia não é médica: mostra onde procurar; quem orienta o caso é
#     a equipe de saúde. As falas são montadas daqui, sem IA.
# Pesquisa feita em 24/09/2026 pela busca na web (trechos das páginas
# oficiais); o ambiente de trabalho não abria os sites do governo, por
# isso vários itens pedem confirmação na própria página.
# =====================================

CONFERIDO = "24/09/2026"
CIDADE = "Rio Claro"
REGIAO = "DRS X Piracicaba / RRAS 14"
URL_CARRETAS_SP_POR_TODAS = "https://www.spportodas.sp.gov.br/sp-por-todas/saude"
URL_CARRETAS_POUPATEMPO = "https://www.poupatempo.sp.gov.br/carta/B7ED6C20-6D1B-481B-8693-35AD62D16E42"

LAMINAS = {"caminho": "Encontre um caminho", "hospitais": "Hospitais no Estado", "carretas": "Carretas",
           "rio_claro": "Rio Claro", "barretos": "Barretos", "sobre": "Sobre estas informações"}

# As 8 portas da Lia (combinadas com o autor, 09/2026): a Lia deixa de ser
# um menu de links e vira uma ponte entre a mulher e a rede de saúde.
# Hospitais e Carretas são RECURSOS (lâminas próprias), não portas.
# (id, rótulo, o que tem dentro, frase da Lia ao abrir)
CAMINHOS = [
    ("mama", "Câncer de mama", "mamografia, diagnóstico e tratamento",
     "Câncer de mama no SUS: onde fazer a mamografia, quando precisa de pedido médico, a faixa de idade, e os "
     "serviços de mastologia e de referência."),
    ("colo", "Colo do útero", "Papanicolau, teste de HPV e vacina",
     "O câncer do colo do útero pode ser evitado: vacina contra o HPV, exame preventivo (Papanicolau ou teste de "
     "HPV) na unidade de saúde e acompanhamento quando algo aparece."),
    ("outros", "Outros cânceres", "intestino, ovário, pele, pulmão, tireoide e corpo do útero",
     "Cada câncer tem os seus sinais, exames e cuidados. Aqui estão o intestino (colorretal), o ovário, a pele, o "
     "pulmão, a tireoide e o corpo do útero (endométrio), com onde buscar atendimento pelo SUS. Sinais e exames "
     "mostrados aqui são informação geral: não servem para diagnosticar."),
    ("tratamento", "Tratamento pelo SUS", "onde se tratar, prazos e apoio",
     "Com o diagnóstico confirmado, o tratamento pelo SUS tem prazo em lei e acontece nos hospitais habilitados em "
     "oncologia. A unidade de saúde (e a regulação do Estado, que a paciente não opera: quem pede a vaga é a equipe de "
     "saúde) encaminha ao hospital de referência. Aqui estão o caminho, os prazos, a fila que dá para acompanhar, os "
     "hospitais e o apoio durante o tratamento."),
    ("direitos", "Direitos e acesso", "benefícios, transporte e como o SUS funciona",
     "Quem recebe um diagnóstico de câncer tem direitos garantidos por lei e um caminho no SUS. Aqui, em "
     "linguagem simples."),
    ("ajuda", "Preciso de ajuda", "em que ponto você está?",
     "Me conta em que ponto você está, que eu mostro o próximo passo na rede de saúde."),
]
NOME_CAMINHO = {c: r for c, r, _, _ in CAMINHOS}
# O próximo passo de cada porta (a jornada da mulher na rede).
# Valor "etapa:<id>" leva a uma situação do Preciso de ajuda (o assunto Diagnóstico foi unido a "Meu exame deu alterado", 20/10/2026).
PROXIMO = {"mama": "etapa:alterado", "colo": "etapa:alterado", "outros": "etapa:alterado", "tratamento": "direitos"}
# A rede oncológica em passos (porta Rede oncológica): (passo, o que é, porta)
FLUXO_REDE = [
    ("Unidade de saúde", "consulta, preventivo e pedido de mamografia", "mama"),
    ("Exame alterado", "exames complementares e biópsia", "etapa:alterado"),
    ("Vaga no especialista", "a unidade de saúde pede a vaga (regulação do Estado); você acompanha a fila", "etapa:encaminhada"),
    ("Especialista", "consulta no hospital de referência", "hospitais"),
    ("Tratamento", "cirurgia, quimioterapia, radioterapia", "tratamento"),
    ("Acompanhamento", "direitos, transporte e apoio", "direitos"),
]


def _item(id, caminho, lamina, onde, titulo, resumo, fonte, link, para_quem=None, como=None, levar=None,
          contato=None, confirmar=None, cuidado=None, grupo=None, tambem=(), tambem_caminhos=(), conferido=None,
          cancer=(), topicos=(), cnes=None, mais_links=()):
    """caminho=None: item que não é passo da jornada da mulher (ensino,
    pesquisa, a região no Estado) -- mora só na lâmina dele. grupo: o
    tema (Barretos) ou a região (Hospitais no Estado) do item na lâmina.
    tambem: [(lâmina, grupo)] onde o item também aparece, em cartão
    curto, sem repetir o texto (a casa dele continua sendo uma só).
    tambem_caminhos: outras portas onde o item aparece em cartão curto.
    cancer: tipos de câncer a que o item é ESPECÍFICO (chaves de TIPOS_CANCER); vazio = serve a qualquer câncer
    (rede, direitos, regulação...). A busca usa isto para nunca levar quem citou um câncer ao conteúdo de outro.
    topicos: [(rótulo, texto)] lidos no cartão depois de "Para quem" (o que é, sinais, exames, tratamento...).
    cnes: código CNES do hospital, SÓ se foi conferido no banco real (hospitais + internacoes); nunca de lista de terceiros.
    Não aparece no cartão: serve para cruzar com os dados do Escudo (SIH/SIA).
    mais_links: [(rótulo, url)] outros botões do cartão, ao lado do principal (cada página oficial fala de uma coisa só)."""
    return {"id": id, "caminho": caminho, "lamina": lamina, "onde": onde, "titulo": titulo, "resumo": resumo,
            "para_quem": para_quem, "como": como, "levar": levar, "contato": contato, "fonte": fonte,
            "link": link, "confirmar": confirmar, "cuidado": cuidado, "grupo": grupo, "tambem": list(tambem),
            "conferido": conferido or CONFERIDO,
            "tambem_caminhos": list(tambem_caminhos), "cancer": tuple(cancer), "topicos": list(topicos), "cnes": cnes, "mais_links": list(mais_links)}


ITENS = [
    # ---------------- PREVENIR ----------------
    _item("mulheres_de_peito", "mama", "caminho", "Estado de SP",
          "Mamografia gratuita pelo Programa Mulheres de Peito",
          "mamografia gratuita em mais de 300 serviços do Estado; de 50 a 69 anos, sem pedido médico",
          "Governo do Estado de SP (Programa Mulheres de Peito) e Poupatempo",
          "https://www.poupatempo.sp.gov.br/carta/4CC55F40-E724-4158-BD99-EE33B4D9B29E",
          para_quem="Foco nas mulheres de 50 a 69 anos, que não precisam de pedido médico.",
          como="Agendar pela central da Secretaria da Saúde, 0800 779 0000 (segunda a sexta, 8h às 17h), ou pelo "
               "Poupatempo (site ou aplicativo). O exame é feito em AMEs, hospitais estaduais e clínicas conveniadas.",
          confirmar="A página do programa que a busca mostrou não tinha data visível: confirme o telefone e a faixa "
                    "de idade ao agendar."),
    _item("colo_utero", "colo", "caminho", "SUS (todo o Brasil)",
          "Exame preventivo do colo do útero (Papanicolau e teste de DNA-HPV)",
          "marque na unidade de saúde do seu bairro (UBS ou USF), de 25 a 64 anos; leve o Cartão SUS e um documento com foto",
          "Ministério da Saúde",
          "https://bvsms.saude.gov.br/papanicolau-exame-preventivo-de-colo-de-utero/",
          para_quem="Mulheres de 25 a 64 anos que já iniciaram vida sexual.",
          como="Onde ir: a UBS ou USF do seu bairro (veja unidades, telefones e como chegar pelo link no topo da página). "
               "Como marcar: na recepção da unidade ou com a agente comunitária de saúde, pergunte os dias de coleta do preventivo. "
               "Em Rio Claro, a consulta também pode ser marcada pelo Cadu (0800 019 0505). "
               "O que levar: Cartão SUS e documento com foto; algumas unidades pedem comprovante de residência. "
               "Com que frequência: o Papanicolau se repete a cada 3 anos, depois de dois exames anuais normais. O SUS está "
               "trocando, aos poucos, o Papanicolau pelo teste de DNA-HPV, que é mais sensível; São Paulo está entre os estados "
               "que já têm o teste. Com o teste de DNA-HPV negativo, o próximo exame é em 5 anos.",
          confirmar="A troca é gradual: pergunte na sua unidade qual exame ela faz hoje. Em Rio Claro, a disponibilidade do teste de "
                    "DNA-HPV deve ser confirmada com a equipe da sua UBS."),
    _item("vacina_hpv", "colo", "caminho", "SUS (todo o Brasil)",
          "Vacina contra o HPV",
          "dose única de 9 a 14 anos; protege contra o vírus que causa o câncer do colo do útero",
          "Ministério da Saúde",
          "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/h/hpv",
          para_quem="Meninas e meninos de 9 a 14 anos, em dose única. Houve um resgate para jovens de 15 a 19 anos "
                    "não vacinados, prorrogado até o 1º semestre de 2026.",
          como="Nas unidades de saúde (e em ações em escolas e outros locais).",
          confirmar="Confirme na unidade se o resgate de 15 a 19 anos ainda está valendo."),

    # ---------------- DESCOBRIR ----------------
    _item("caminho_do_exame", "mama", "caminho", "Estado de SP",
          "O caminho do exame pelo SUS começa na unidade de saúde",
          "consulta na unidade → pedido do exame → regulação do município agenda o serviço",
          "Secretaria de Estado da Saúde de SP",
          "https://saude.sp.gov.br/coordenadoria-de-controle-de-doencas/noticias/10102024-outubro-rosa-veja-como-"
          "agendar-exame-de-mamografia-em-sp-de-forma-gratuita",
          como="Procure a UBS mais próxima e passe por uma consulta. Se o exame for indicado, o encaminhamento é "
               "feito no sistema de regulação do município, que agenda o serviço."),
    _item("lei_30_dias", "direitos", "caminho", "SUS (todo o Brasil)",
          "Direito: investigação diagnóstica em até 30 dias, quando a lei se aplica",
          "quando câncer é a principal hipótese diagnóstica, os exames necessários à investigação devem ser feitos em até 30 dias, com pedido médico fundamentado",
          "Lei federal 13.896/2019 (Câmara dos Deputados)",
          "https://www2.camara.leg.br/legin/fed/lei/2019/lei-13896-30-outubro-2019-789326-norma-pl.html",
          para_quem="Pessoas atendidas no SUS quando a principal hipótese diagnóstica seja câncer.",
          como="A Lei 13.896/2019 prevê até 30 dias para os exames necessários à investigação quando câncer é a "
               "principal hipótese diagnóstica e o médico responsável faz uma solicitação fundamentada. Se não "
               "souber se esse critério se aplica ao seu caso, peça à equipe de saúde que explique."),
    _item("mater_ribeirao", "mama", "caminho", "Ribeirão Preto",
          "MATER – Centro de Referência da Saúde da Mulher",
          "mamografia alterada vai rápido para biópsia; atende os 26 municípios da região de Ribeirão Preto",
          "MATER / FAEPA – HC da Faculdade de Medicina de Ribeirão Preto (USP)",
          "https://mater.faepa.br/",
          para_quem="Mulheres com alteração na mama dos 26 municípios da região de Ribeirão Preto.",
          como="Encaminhamento rápido de mamografias alteradas para biópsia, tratamento dos casos benignos e "
               "encaminhamento ao serviço de referência quando o câncer se confirma. O acesso é pela rede pública da "
               "região.",
          contato="Rua Wanderley Taffo, 330 – Quintino Facci II, Ribeirão Preto.",
          cuidado="Vale para a região de Ribeirão Preto; quem mora em outra região segue a referência da sua.",
          tambem=[("hospitais", "Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)")]),

    # ---------------- TRATAR ----------------
    _item("lei_60_dias", "tratamento", "caminho", "SUS (todo o Brasil)",
          "Direito: começar o tratamento em até 60 dias",
          "com o câncer confirmado, o tratamento pelo SUS deve começar em até 60 dias do laudo",
          "Lei federal 12.732/2012 (Planalto)",
          "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12732.htm",
          para_quem="Pacientes com câncer diagnosticado no SUS.",
          como="A lei dá prazo máximo de 60 dias, contados do laudo patológico, para começar o tratamento (cirurgia, "
               "quimioterapia ou radioterapia). O prazo de até 30 dias para exames de investigação tem critérios "
               "próprios: câncer deve ser a principal hipótese diagnóstica e o médico responsável precisa fazer uma "
               "solicitação fundamentada. Os prazos têm marcos e critérios diferentes; a equipe de saúde pode explicar "
               "qual se aplica ao seu caso.",
          tambem_caminhos=["direitos"]),
    _item("rede_oncologica", "tratamento", "caminho", "Estado de SP",
          "Rede de Atenção Oncológica do Estado de São Paulo",
          "a lista oficial dos hospitais habilitados para tratar câncer pelo SUS, por região",
          "Fundação Oncocentro de São Paulo (FOSP)",
          "https://fosp.saude.sp.gov.br/fosp/diretoria-adjunta-de-informacao-e-epidemiologia/rede-de-atencao-"
          "oncologica-do-estado-de-sao-paulo/",
          como="Os hospitais são habilitados como CACON (alta complexidade) ou UNACON, com ou sem radioterapia e "
               "hematologia. O acesso é pela regulação: a unidade de saúde ou o especialista encaminha. A lista "
               "serve para saber quais são as referências da sua região."),

    # ---------------- ACOMPANHAR ----------------
    _item("lista_regulacao", "tratamento", "caminho", "Estado de SP",
          "Lista de Regulação de Oncologia",
          "quem aguarda a consulta especializada em oncologia pelo SUS-SP consulta a própria fila",
          "Secretaria de Estado da Saúde de SP e Poupatempo (Lei estadual 17.745/2023)",
          "https://servicos.sp.gov.br/fcarta/4F97BB19-93B6-4198-A5C2-ED4265E7F724",
          para_quem="Pacientes com diagnóstico ou suspeita forte de câncer, atendidas no SUS-SP, que aguardam o "
                    "agendamento da consulta especializada em oncologia.",
          como="Consultar pelo Poupatempo (site ou aplicativo) ou pelo portal Saúde Digital da Secretaria "
               "(saudedigital.saude.sp.gov.br). A lista traz os pedidos registrados no SIRESP, o sistema de "
               "regulação usado pelo Estado e pelos municípios.",
          levar="Nenhum documento; é gratuito e na hora."),

    # ---------------- IR ATÉ VOCÊ ----------------
    _item("carretas_estado", "mama", "carretas", "Estado de SP",
          "Carretas da Mamografia (Programa Mulheres de Peito)",
          "atendimento gratuito a partir de 35 anos, sem mamografia nos últimos 12 meses; consulte o itinerário oficial",
          "Poupatempo / Secretaria de Estado da Saúde de SP",
          "https://www.poupatempo.sp.gov.br/carta/B7ED6C20-6D1B-481B-8693-35AD62D16E42",
          para_quem="Mulheres a partir de 35 anos que não fizeram mamografia nos últimos 12 meses.",
          levar="De 50 a 74 anos: RG e cartão SUS. De 35 a 49 e acima de 74 anos: também o pedido médico do SUS.",
          como="Consultar o itinerário no Poupatempo (site ou aplicativo). Atendimento de segunda a sexta, das 8h às "
               "17h, e aos sábados, das 8h às 12h, com senhas limitadas. Gratuito.",
          grupo="Carretas da Mamografia do Estado"),

    # ---------------- ENCONTRAR REFERÊNCIA ----------------
    _item("santa_casa_piracicaba", "tratamento", "hospitais", "Piracicaba (região de Rio Claro)",
          "Santa Casa de Piracicaba",
          "UNACON com radioterapia, na mesma região de saúde de Rio Claro",
          "FOSP – boletim da RRAS 14 (DRS Piracicaba)",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS14.pdf",
          como="Hospital habilitado como UNACON com serviço de radioterapia. Faz parte da RRAS 14, a mesma de Rio "
               "Claro. O acesso é pela regulação do SUS.",
          grupo="Rio Claro e Piracicaba (RRAS 14)"),
    _item("fornecedores_cana", "tratamento", "hospitais", "Piracicaba (região de Rio Claro)",
          "Hospital dos Fornecedores de Cana de Piracicaba",
          "UNACON com radioterapia e hematologia, na mesma região de saúde de Rio Claro",
          "FOSP – boletim da RRAS 14 (DRS Piracicaba)",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS14.pdf",
          como="Hospital habilitado como UNACON com radioterapia e hematologia. Faz parte da RRAS 14, a mesma de Rio "
               "Claro. O acesso é pela regulação do SUS.",
          grupo="Rio Claro e Piracicaba (RRAS 14)"),
    _item("santa_casa_limeira", "tratamento", "hospitais", "Limeira (região de Rio Claro)",
          "Santa Casa de Limeira",
          "citada como UNACON com radioterapia na região de Rio Claro (a confirmar)",
          "FOSP – boletim da RRAS 14 (DRS Piracicaba)",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS14.pdf",
          como="O acesso é pela regulação do SUS.",
          confirmar="Não consegui abrir o boletim da FOSP inteiro para confirmar a habilitação de Limeira.",
          grupo="Rio Claro e Piracicaba (RRAS 14)"),
    _item("caism_unicamp", "tratamento", "hospitais", "Campinas",
          "CAISM Unicamp – Hospital da Mulher",
          "maior hospital de saúde da mulher do interior; câncer ginecológico e de mama; só SUS",
          "CAISM – Unicamp",
          "https://www2.caism.unicamp.br/",
          para_quem="Pacientes do SUS que chegam encaminhadas pela rede pública (a página do hospital fala em "
                    "atendimento a pacientes \"referenciadas\").",
          topicos=[
              ("O que o hospital informa sobre si (site do CAISM)",
               "Inaugurado em março de 1986 como o Hospital da Mulher da Unicamp, atende exclusivamente pelo SUS e "
               "presta assistência em ginecologia, obstetrícia, oncologia e neonatologia. É a maior unidade "
               "hospitalar de saúde da mulher do interior do Estado de São Paulo e se apresenta como referência "
               "para o tratamento do câncer ginecológico e de mama. Tem 130 leitos e fez cerca de 70 mil atendimentos "
               "ambulatoriais em 2023."),
              ("O que a paciente encontra",
               "Equipes médicas, de enfermagem, fisioterapia, assistência social, psicologia, nutrição e farmácia, "
               "com exames de imagem e de laboratório. No hospital funcionam radioterapia, quimioterapia e as "
               "unidades de internação de oncologia cirúrgica, oncologia clínica e ginecologia."),
              ("Onde fica", "No Campus da Unicamp, em Campinas, na esquina das ruas Alexandre Fleming e Avenida "
                            "Adolfo Lutz (o Bloco A reúne as internações). O site tem a página \"Atendimento ao "
                            "paciente\" para quem vai ao hospital."),
          ],
          como="Atende só pelo SUS. Tem ambulatórios de oncologia ginecológica (vulva, vagina, colo e corpo do útero, "
               "ovário) e de mastologia, referência para Campinas e região. As consultas são agendadas pelas "
               "unidades básicas de saúde e pela rede pública.",
          cuidado="O acesso é por encaminhamento da rede pública; para quem mora em Rio Claro, o caminho começa "
                  "na referência da própria região.",
          grupo="Campinas",
          conferido="18/10/2026",
          tambem_caminhos=["mama", "colo"]),
    _item("hospital_base_rio_preto", "tratamento", "hospitais", "São José do Rio Preto",
          "Hospital de Base – Centro de Oncologia",
          "um dos hospitais que mais diagnosticam câncer no Estado; atende SUS com encaminhamento",
          "Hospital de Base de São José do Rio Preto",
          "https://hospitaldebase.com.br/servicos/centro-de-oncologia",
          como="Atende gratuitamente pacientes do SUS encaminhados pela unidade básica de saúde da cidade de origem, "
               "pela Central de Agendamento de Consultas. Equipe com médicos, enfermagem, farmácia, serviço social, "
               "psicologia, nutrição e outras áreas.",
          cuidado="É referência da região de Rio Preto; quem mora em outra região segue a referência da sua.",
          grupo="Rio Preto, Araçatuba e Jales (RRAS 12)"),

    # ---------------- CUIDAR ----------------
    _item("sp_por_todas", "direitos", "caminho", "Estado de SP",
          "SP por Todas – serviços para mulheres",
          "portal do Estado com serviços de saúde, proteção e autonomia para mulheres",
          "Governo do Estado de SP (Agência SP)",
          "https://www.spportodas.sp.gov.br/sp-por-todas/saude/outubrorosa",
          como="Reúne, num lugar só, serviços estaduais para mulheres: saúde (como o Outubro Rosa), proteção e "
               "autonomia."),
    _item("piracicaba_cesm", "mama", "caminho", "Piracicaba",
          "Centro Especializado em Saúde da Mulher (CESM) e mamografia agendada online",
          "Piracicaba agenda mamografia pela internet e ampliou o rastreamento para 40 a 49 anos",
          "Prefeitura de Piracicaba",
          "https://piracicaba.sp.gov.br/noticias/piracicaba-atualiza-recomendacoes-para-acesso-a-mamografia-e-"
          "amplia-faixa-etaria-de-rastreamento/",
          para_quem="Moradoras de Piracicaba.",
          como="O programa municipal de saúde da mulher é coordenado pelo CESM. Desde 2024 a mamografia pode ser "
               "agendada online (sistema SISS Saúde); mulheres de 40 a 49 anos têm acesso ao exame com avaliação "
               "profissional. Há também uma unidade móvel de saúde da mulher."),
    _item("campinas_craim", "mama", "caminho", "Campinas",
          "Mamografia em Campinas: CRAIM e agendamento pelo 160",
          "no Outubro Rosa de 2025, moradoras agendaram mamografia pelo Disque Saúde 160, sem pedido médico",
          "Prefeitura de Campinas",
          "https://www.campinas.sp.gov.br/governo/saude/atencao-a-saude/saudeDaMulher_protocolos_espec_mamografia.php",
          para_quem="Moradoras de Campinas: de 40 a 49 anos com o último exame há mais de 1 ano e de 50 a 74 com o "
                    "último há mais de 2 anos (regra da campanha de 2025).",
          como="Agendamento pelo Disque Saúde 160. Exames no Centro de Referência e de Assistência Integral à Mulher "
               "(CRAIM), no CAISM Unicamp, em clínica conveniada e na carreta do Hospital de Amor.",
          confirmar="Regra da campanha de outubro de 2025: veja se há campanha neste ano."),
    _item("rio_preto_mamografia", "mama", "caminho", "São José do Rio Preto",
          "Mamografia de rastreamento em Rio Preto a partir dos 40 anos",
          "pedido na UBS; rastreamento a cada 2 anos para mulheres a partir de 40 anos",
          "Prefeitura de São José do Rio Preto (Secretaria de Saúde)",
          "https://www.riopreto.sp.gov.br/secretarias/saude",
          para_quem="Moradoras de São José do Rio Preto a partir de 40 anos.",
          como="O pedido é feito na UBS, e o médico emite a guia de agendamento na rede pública.",
          confirmar="A regra dos 40 anos veio de uma portaria citada na busca: confirme na UBS."),

    # ---------------- PROTEGER ----------------
    _item("ligue_180", "ajuda", "caminho", "Todo o Brasil",
          "Ligue 180 – Central de Atendimento à Mulher",
          "gratuito, 24 horas, todos os dias; também por WhatsApp. Em perigo agora: ligue 190",
          "Ministério das Mulheres",
          "https://www.gov.br/mulheres/pt-br/ligue180",
          como="Orienta sobre leis, direitos e serviços da rede, registra denúncias e encaminha aos órgãos "
               "competentes. Em perigo imediato, ligue 190 (Polícia Militar).",
          contato="Telefone 180; WhatsApp (61) 9610-0180."),
    _item("sp_mulher_segura", "ajuda", "caminho", "Estado de SP",
          "Aplicativo SP Mulher Segura",
          "boletim de ocorrência, pedido de medida protetiva e botão do pânico pelo celular",
          "Governo do Estado de SP (Agência SP)",
          "https://www.agenciasp.sp.gov.br/politicas-para-mulheres/sp-mulher-segura-conheca-o-aplicativo-que-permite-denunciar-violencia-"
          "domestica-e-acionar-botao-do-panico-contra-agressores/",
          como="Permite registrar boletim de ocorrência, pedir medida protetiva de urgência e, para quem já tem "
               "medida protetiva, acionar o botão do pânico, que envia a localização em tempo real. Android e iOS; "
               "entra com a conta gov.br."),
    _item("delegacia_eletronica", "ajuda", "caminho", "Estado de SP",
          "Delegacia Eletrônica – violência doméstica contra a mulher",
          "registrar ocorrência pela internet, 24 horas, e pedir medida protetiva",
          "Polícia Civil do Estado de SP",
          "https://delegaciadigital.policia-civil.sp.gov.br/pagina-inicial",
          como="Em \"Comunicar Ocorrência\", escolher \"Violência Doméstica Contra Mulher\". Dá para anexar fotos e "
               "mensagens e pedir medida protetiva de urgência no mesmo formulário."),

    # ================ LÂMINA RIO CLARO (a cidade do trabalho) ================
    _item("rc_cadu_agendamento", "mama", "rio_claro", "Rio Claro",
          "Agendamento de consultas pelo Cadu",
          "telefone e WhatsApp gratuitos para agendar atendimento nas unidades de saúde, inclusive a consulta em que se pede mamografia ou Papanicolau",
          "Publicação da Fundação Municipal de Saúde de Rio Claro de 07/10/2026, que divulga o canal; chefia de UBS (19/10/2026)",
          "https://rioclaro.sp.gov.br/fundacao-de-saude/nova-central-para-agendamento-de-consultas-comeca-a-operar-na-2a-feira-em-rc/",
          para_quem="Moradoras e moradores que precisam agendar consulta na rede municipal; para mamografia e Papanicolau, é necessário passar por profissional de saúde.",
          como="Ligue ou envie mensagem pelo WhatsApp para 0800 019 0505. A publicação municipal de 07/10/2026 informa que consultas para solicitar mamografia e Papanicolau podem ser agendadas pelo Cadu ou diretamente na unidade de saúde. O exame depende de solicitação de profissional. O Cadu só agenda: atendimentos nas unidades de saúde, com médicos, enfermeiros e dentistas, clínicos ou especialistas. É um canal externo à Fundação, e o exame pedido segue pela Central de Regulação, acionada pela unidade. Há também o aplicativo CADU Digital (Central de Atendimento Digital), para Android e iPhone: os botões de download estão abaixo.",
          contato="Cadu: 0800 019 0505 (telefone/WhatsApp).",
          confirmar="Canal confirmado em publicação municipal de 07/10/2026; confirme o funcionamento e as regras atuais antes de depender do serviço. Os endereços do aplicativo foram informados pela equipe em 18/10/2026. Uma chefia de UBS informou em 19/10/2026 que o Cadu só faz agendamento e é externo à Fundação; quem opera o serviço não foi identificado.",
          tambem_caminhos=["colo"],
          mais_links=[("Baixar o app CADU Digital no Android (Google Play)", "https://play.google.com/store/apps/details?id=com.unicidadao&hl=pt_BR"),
                      ("Baixar o app CADU Digital no iPhone (App Store)", "https://apps.apple.com/br/app/cadu-digital/id6449848522"),
                      ("Sobre o CADU na página da Prefeitura", "https://rioclaro.sp.gov.br/banner/cadu-central-de-atendimento-digital-unicidadao/")],
          conferido="09/10/2026"),
    _item("rc_unidades", "colo", "rio_claro", "Rio Claro",
          "Unidades de Saúde da Família (USF) e UBS",
          "a porta de entrada: preventivo do colo do útero, exame das mamas e pré-natal",
          "Fundação Municipal de Saúde de Rio Claro",
          "https://www.saude-rioclaro.org.br/enderecos.htm",
          para_quem="Moradoras de Rio Claro.",
          como="A Prefeitura informa 17 Unidades de Saúde da Família e 4 UBS, das 7h às 17h. A consulta é marcada "
               "na própria unidade, que é onde se faz o preventivo e se pede a mamografia. Algumas equipes têm "
               "ginecologista. Exame pedido pelo médico (mamografia, raio X e outros): o pedido fica com o "
               "funcionário da unidade, que aciona a Central Municipal de Regulação de Serviços Especializados; a "
               "Central avisa a unidade e a unidade avisa a paciente, que não precisa ir a outra central. Convém manter "
               "o telefone atualizado na unidade. A Central analisa o pedido; se faltar informação, ele volta à unidade "
               "para correção, e a marcação depende das vagas da rede. Pedido de médico ou clínica particular também "
               "vale: precisa estar em receituário próprio, com identificação do profissional, CID e justificativa "
               "clínica, e a equipe da unidade o transcreve para o formulário. O Cadu (0800 019 0505) só agenda "
               "atendimentos nas unidades, como a consulta ou a coleta do Papanicolau; o exame pedido segue pela "
               "Central de Regulação.",
          levar="O pedido do exame, completo e legível, quando já houver.",
          confirmar="O número de unidades e o horário vêm de páginas antigas da Prefeitura: confira a lista de "
                    "endereços. O caminho do exame pedido segue o protocolo da Fundação Municipal de Saúde para exames "
                    "de média e alta complexidade (revisão 03, 2026) e foi confirmado por chefias da Fundação em "
                    "19/10/2026. O protocolo não foi aberto por link público: confirme na unidade os prazos e as vagas.",
          tambem_caminhos=["mama"]),
    _item("rc_santa_casa", "tratamento", "rio_claro", "Rio Claro",
          "Santa Casa de Rio Claro – oncologia (UNACON) e Centro Oncológico Santa Ágata",
          "hospital habilitado para tratar câncer pelo SUS na própria cidade",
          "Secretaria de Estado da Saúde (lista de unidades habilitadas, jun/2021), Ministério da Saúde (habilitação em oncologia) e Santa Casa de Rio Claro",
          "https://www.santacasaderioclaro.com.br/",
          como="Habilitada como UNACON. O Centro Oncológico Santa Ágata tem 24 poltronas de quimioterapia, 6 leitos e "
               "11 consultórios. É referência em câncer de cabeça e pescoço para os 26 municípios da DRS X. O acesso "
               "pelo SUS é pela regulação (encaminhamento da unidade ou do especialista).",
          contato="Rua 2 (R. Dois), nº 297, Centro. Telefone (19) 3535-7000.",
          confirmar="O telefone e o endereço vêm da lista da Secretaria de Estado da Saúde de junho/2021: confirme antes de ligar ou ir.",
          tambem=[("hospitais", "Rio Claro e Piracicaba (RRAS 14)")]),
    _item("rc_cram", "ajuda", "rio_claro", "Rio Claro",
          "Centro de Referência de Atendimento à Mulher (CRAM) Dona Ângela Gonzaga",
          "acolhimento e orientação para mulheres, das 8h às 17h",
          "Prefeitura de Rio Claro (Desenvolvimento Social)",
          "https://rioclaro.sp.gov.br/desenvolvimento-social/casa-aberta-no-centro-de-referencia-de-atendimento-a-"
          "mulher/",
          contato="Rua 17, nº 30 (anexo ao Centro Social Urbano \"Mitiko Nevoeiro\"), entre as avenidas 23 e 35. "
                  "Telefones 3532-4014 e 3525-1366. Das 8h às 17h.",
          confirmar="Endereço e telefones vêm de uma página da Prefeitura sem data visível na busca."),

    # ================ LÂMINA BARRETOS (Hospital de Amor) ================
    _item("ha_quem_e", "tratamento", "barretos", "Barretos",
          "Hospital de Amor (Fundação Pio XII)",
          "hospital filantrópico dedicado ao câncer, fundado em 1962 em Barretos; atende pelo SUS",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/conheca-mais-sobre-nossa-historia/",
          como="Hospital filantrópico mantido pela Fundação Pio XII, dedicado à prevenção e ao tratamento do câncer, "
               "com unidades em várias regiões do Brasil. O atendimento é gratuito pelo SUS.",
          confirmar="A habilitação como CACON aparece na rede estadual, mas não consegui abrir a lista da FOSP para "
                    "confirmar.",
          grupo="Hospitais de referência",
          tambem=[("hospitais", "Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)")]),
    _item("ha_prevencao", "mama", "barretos", "Barretos",
          "Prevenção do Hospital de Amor",
          "Instituto de Prevenção em Barretos e unidades fixas de prevenção, inclusive em Campinas",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/prevencao/",
          para_quem="Mulheres de 40 a 69 anos nas ações de mamografia.",
          como="O Instituto de Prevenção de Barretos faz mamografia, Papanicolau, exame da boca, teste FIT (intestino) "
               "e teledermatologia (pele). Há unidades fixas de prevenção no Estado em Barretos, Campinas e "
               "Fernandópolis.",
          confirmar="Os detalhes do Instituto vieram de reportagem: confirme na página de Prevenção do hospital.",
          grupo="Prevenção",
          tambem_caminhos=["colo"]),
    _item("ha_moveis", "mama", "barretos", "Barretos",
          "Unidades móveis do Hospital de Amor",
          "unidades móveis que fazem ações de prevenção em parceria com as prefeituras",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/prevencao/",
          para_quem="Mulheres de 40 a 69 anos.",
          como="As unidades móveis chegam por parceria com a prefeitura. Para agendar, procure a unidade de saúde "
               "mais próxima.",
          levar="Cópia do RG, CPF, cartão SUS e comprovante de residência.",
          grupo="Carretas e unidades móveis",
          ),
    _item("ha_primeiro_atendimento", "tratamento", "barretos", "Barretos",
          "Primeiro atendimento no Hospital de Amor",
          "com o câncer confirmado por exame, o primeiro agendamento é feito com os documentos pelo WhatsApp",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/primeiro-atendimento/",
          levar="Encaminhamento médico, cópia da biópsia, exames realizados, cartão SUS, RG, CPF e comprovante de "
                "residência. Os exames precisam confirmar o tumor maligno.",
          como="Os pacientes chegam encaminhados pela rede pública dos 18 municípios do DRS de Barretos ou pelos "
               "próprios serviços do hospital, conforme os fluxos do SUS.",
          contato="Documentos pelo WhatsApp (17) 3321-5403; dúvidas pelo (17) 3321-5400. Segunda a quinta, 8h às "
                  "17h; sexta, 8h às 16h.",
          cuidado="Para quem mora em Rio Claro, o caminho do SUS passa primeiro pela referência da própria região "
                  "(RRAS 14). Converse com a equipe que acompanha você.",
          grupo="Tratamento e acesso pelo SUS"),
    _item("ha_unidades", "tratamento", "barretos", "Barretos",
          "As três unidades do Hospital de Amor em Barretos",
          "hospital adulto, Hospital Infantojuvenil e Hospital São Judas Tadeu (cuidados paliativos)",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/tag/hospital-sao-judas-tadeu/",
          como="O Hospital de Amor (unidade principal); o Hospital de Amor Infantojuvenil, só para câncer em crianças "
               "e adolescentes; e o Hospital São Judas Tadeu, onde o hospital começou em 1962 e que hoje atende "
               "pacientes em cuidados paliativos, com atendimento domiciliar na região de saúde de Barretos.",
          confirmar="Os números dos cuidados paliativos vieram da Academia Nacional de Cuidados Paliativos: confira "
                    "na página do hospital.",
          grupo="Hospitais de referência"),
    _item("ha_mastologia", "mama", "barretos", "Barretos",
          "Mastologia e reconstrução mamária",
          "referência no tratamento do câncer de mama, com oncoplastia e reconstrução da mama",
          "Hospital de Amor (Especialidades)",
          "https://especialidades.hospitaldeamor.com.br/especialidades/mastologia/",
          como="O departamento de Mastologia e Reconstrução Mamária é referência no tratamento do câncer de mama, com "
               "oncoplastia e reconstrução mamária. São cerca de 15 mil atendimentos e 1.200 cirurgias por ano.",
          grupo="Câncer de mama"),
    _item("ha_colo_busca_ativa", "colo", "barretos", "Barretos",
          "Busca ativa do câncer do colo do útero desde 1994",
          "na região de Barretos, 72% dos diagnósticos de câncer do colo do útero são feitos no estágio inicial",
          "Hospital de Amor (dado da FOSP)",
          "https://hospitaldeamor.com.br/barretos-possui-o-maior-indice-de-deteccao-precoce-do-cancer-de-colo-"
          "uterino-em-sp/",
          como="Desde 1994 o hospital faz busca ativa para o preventivo na periferia de Barretos e depois nas cidades "
               "da DRS V. Segundo a FOSP, 72% dos diagnósticos da região acontecem no estágio in situ, tratado com "
               "procedimentos simples no ambulatório: a região é a de maior detecção precoce do Estado.",
          grupo="Câncer do colo do útero"),
    _item("ha_pesquisa_hpv", "colo", "barretos", "Barretos",
          "Grupo de Pesquisa em HPV (IEP) e autocoleta",
          "estudos sobre o HPV e novas formas de rastreamento, como a autocoleta pela própria mulher",
          "Instituto de Ensino e Pesquisa do Hospital de Amor",
          "https://iep.hospitaldeamor.com.br/grupo_de_pesquisa/pesquisa-em-hpv/",
          como="Criado em 2010 e certificado pelo CNPq, estuda a infecção pelo HPV, a transformação em câncer e novas "
               "tecnologias de rastreamento. Num estudo de autocoleta (a mulher colhe a amostra com uma escovinha), "
               "os resultados concordaram em cerca de 80% com a coleta feita pela profissional.",
          grupo="Câncer do colo do útero"),
    _item("ha_iep", None, "barretos", "Barretos",
          "Instituto de Ensino e Pesquisa (IEP)",
          "pós-graduação, residência médica e grupos de pesquisa em oncologia",
          "Instituto de Ensino e Pesquisa do Hospital de Amor",
          "https://iep.hospitaldeamor.com.br/",
          como="Fundado em 2008, oferece estágios, pós-graduação em oncologia (especialização, mestrado e doutorado, "
               "com nota 6 na CAPES no acadêmico) e residências médicas. Interessa a estudantes e pesquisadores.",
          grupo="Ensino e pesquisa"),
    _item("ha_rras13", None, "barretos", "Barretos",
          "Barretos na rede do Estado: RRAS 13",
          "Barretos está na RRAS 13, com as DRS de Araraquara, Franca e Ribeirão Preto; é um dos polos de oncologia",
          "FOSP – boletim da RRAS 13",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS13.pdf",
          como="A RRAS 13 reúne as DRS de Araraquara, Barretos, Franca e Ribeirão Preto. A Fundação Pio XII "
               "(Hospital de Amor) está entre os serviços de oncologia da região, ao lado da Santa Casa de Franca e "
               "do HC de Ribeirão Preto. Rio Claro fica em outra região, a RRAS 14.",
          grupo="No Estado de SP"),

    # ---------------- OUTROS CÂNCERES (10/2026): cada um com sinais, exames e cuidados próprios ----------------
    # Escritos a partir de conhecimento geral consolidado e de busca na web em 18/10/2026; as páginas do INCA não
    # puderam ser abertas pela nuvem (gov.br inacessível), então todos levam "a confirmar" até alguém conferir o texto
    # com a página oficial. Regras: nada de diagnóstico, de remédio ou de promessa de cura; rastreamento só quando a
    # fonte o sustenta; idade e intervalo de exame NÃO entram aqui (dependem das diretrizes vigentes e do histórico).
    _item("cancer_intestino", "outros", "caminho", "SUS (todo o Brasil)",
          "Câncer de intestino (colorretal): sinais, exames e como buscar atendimento",
          "câncer no cólon ou no reto; sangue nas fezes e mudança que dura no intestino merecem avaliação, mas não "
          "confirmam câncer",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/intestino/versao-para-populacao",
          para_quem="Qualquer pessoa. Quem tem sintomas precisa de investigação com profissional de saúde. O "
                    "rastreamento é para quem não tem sintomas e depende da idade, do histórico e das diretrizes do "
                    "Ministério da Saúde.",
          topicos=[
              ("O que é", "Começa no intestino grosso (cólon) ou no reto. Muitos casos nascem de pólipos, pequenos "
                          "caroços na parede do intestino, que podem ser retirados antes de se tornarem câncer."),
              ("Fatores de risco", "Idade mais avançada, câncer de intestino ou pólipos na família, doenças "
                                   "inflamatórias do intestino, excesso de peso, sedentarismo, alimentação com "
                                   "pouca fibra e muita carne processada, bebida alcoólica e tabagismo. Ter um fator "
                                   "não significa que a pessoa terá a doença."),
              ("Sinais que merecem avaliação", "Sangue nas fezes, mudança que dura no funcionamento do intestino "
                                               "(diarreia ou prisão de ventre), dor ou desconforto na barriga, "
                                               "fraqueza ou anemia e perda de peso sem explicação. Têm muitas causas "
                                               "comuns, como hemorroidas, e não confirmam câncer; mas não se deve "
                                               "presumir a causa sem avaliação."),
              ("Prevenção, diagnóstico precoce e rastreamento", "Rastreamento e sintomas são coisas diferentes. "
                                                                 "Rastrear é procurar a doença em quem não tem "
                                                                 "sintoma. Desde maio de 2026, o SUS adota o teste "
                                                                 "imunoquímico fecal (FIT), feito com um kit em casa, "
                                                                 "como exame de referência para homens e mulheres de "
                                                                 "50 a 75 anos sem sintomas (notícia do INCA, "
                                                                 "21/05/2026). Quem tem sintoma não espera o "
                                                                 "rastreamento: faz a investigação. De quanto em "
                                                                 "quanto tempo repetir o teste e onde pegar o kit, "
                                                                 "pergunte na unidade de saúde. O passo a passo está "
                                                                 "no cartão \"Exame de intestino pelo SUS\"."),
              ("Como se investiga", "A equipe avalia os sintomas e pode pedir exames de fezes, de sangue e a "
                                    "colonoscopia, que olha o interior do intestino e permite retirar pólipos e "
                                    "coletar material. A biópsia (análise desse material no laboratório) é o que "
                                    "confirma ou afasta o câncer."),
              ("Tratamento", "Depende do tamanho, do local e da extensão da doença. Costuma envolver cirurgia e, em "
                             "alguns casos, quimioterapia e radioterapia. Quem define é a equipe de oncologia."),
              ("Depois do diagnóstico", "O acompanhamento regular depois do tratamento faz parte do cuidado: a equipe "
                                        "explica a frequência dos retornos e dos exames."),
          ],
          como="Comece pela unidade de saúde do bairro (UBS ou USF): ela avalia, pede exames e encaminha. Se houver "
               "suspeita, o encaminhamento ao especialista e ao hospital habilitado em oncologia é feito pela "
               "regulação (CROSS); veja \"Como se chega a um hospital de referência pelo SUS\".",
          cuidado="Sangue nas fezes ou mudança do intestino que dura merece consulta, não espera. Com dor forte, "
                  "sangramento intenso ou desmaio, procure um pronto atendimento ou ligue 192.",
          confirmar="O rastreamento (FIT, 50 a 75 anos, sem sintomas) foi conferido na notícia do INCA de 21/05/2026. O "
                    "resto do texto veio de conhecimento geral e de busca na web em 18/10/2026, e a página do INCA "
                    "sobre o tipo de câncer não pôde ser aberta pela nuvem: conferir na página oficial. Falta saber o "
                    "intervalo entre os testes.",
          conferido="18/10/2026", cancer=["colorretal"]),
    _item("jornada_exame_intestino", "outros", "caminho", "SUS (todo o Brasil)",
          "Exame de intestino pelo SUS: do posto de saúde ao resultado (FIT e colonoscopia)",
          "o caminho do teste FIT (sangue escondido nas fezes) e da colonoscopia; quem procura rastreamento e quem "
          "tem sintomas seguem caminhos diferentes",
          "INCA (Instituto Nacional de Câncer) e Ministério da Saúde",
          "https://www.gov.br/inca/pt-br/assuntos/noticias/2026/sus-adota-novo-exame-para-detectar-cancer-de-"
          "intestino-antes-dos-sintomas",
          para_quem="Rastreamento (teste FIT): homens e mulheres de 50 a 75 anos, sem sintomas. Sintomas (sangue nas "
                    "fezes, mudança que dura no intestino, anemia, perda de peso sem explicação): avaliação clínica, "
                    "sem esperar o rastreamento.",
          topicos=[
              ("1. Comece pela unidade de saúde", "Procure a UBS ou USF do seu bairro com o cartão do SUS e um "
                                                  "documento. É lá que a equipe avalia o seu caso e diz qual "
                                                  "caminho vale para você."),
              ("2. Rastreamento ou sintomas?", "Sem sintomas e com 50 a 75 anos: o caminho é o teste FIT. Com "
                                               "sintomas: a equipe faz a avaliação clínica e decide os exames, sem "
                                               "esperar o rastreamento. Conte também se alguém da família teve câncer "
                                               "de intestino."),
              ("3. O teste FIT", "Desde maio de 2026, o Ministério da Saúde adotou o teste imunoquímico fecal (FIT) "
                                 "como exame de referência no SUS para o rastreamento. Você recebe um kit para "
                                 "coletar em casa, e o material vai para o laboratório. Não exige preparo do "
                                 "intestino nem dieta, e basta uma amostra. Ele procura sangue escondido nas fezes e "
                                 "não diz, sozinho, que há câncer."),
              ("4. Se o FIT detectar sangue", "Você é encaminhada para exames complementares. A colonoscopia é "
                                              "considerada o exame padrão-ouro: olha o intestino por dentro e "
                                              "permite retirar pólipos durante o procedimento. Quem indica o exame é "
                                              "a equipe de saúde."),
              ("5. Vaga e regulação", "A colonoscopia e a consulta com especialista são marcadas pela regulação do "
                                      "município e do Estado. Peça à unidade o número ou a data do seu pedido. Se o "
                                      "seu nome não aparecer ou a fila não andar, veja \"Não achei meu nome na "
                                      "lista, ou a fila não anda\" e a \"Lista de Regulação de Oncologia\"."),
              ("6. Depois do resultado", "Volte à equipe que pediu o exame. Se for encontrada uma lesão, a biópsia "
                                         "confirma ou afasta o câncer. Com um diagnóstico, os próximos passos estão "
                                         "nas portas Diagnóstico, Regulação e Tratamento."),
          ],
          como="A porta de entrada é sempre a unidade de saúde do bairro (em Rio Claro, veja \"Unidades de Saúde da "
               "Família (USF) e UBS\"). Hospitais e centros de referência não são porta de entrada: a vaga vem pela "
               "regulação (CROSS).",
          cuidado="Sangue nas fezes, mudança do intestino que dura, anemia ou emagrecimento sem explicação não "
                  "esperam o FIT: procure a unidade de saúde. Com dor forte, sangramento intenso ou desmaio, procure "
                  "um pronto atendimento ou ligue 192.",
          confirmar="Faixa etária, o FIT como exame de referência e o que vem depois de um teste positivo foram "
                    "conferidos na notícia do INCA de 21/05/2026. NÃO confirmados: de quanto em quanto tempo repetir "
                    "o teste, quais unidades de Rio Claro entregam o kit e onde é feita a colonoscopia pelo SUS na "
                    "região. Pergunte na unidade de saúde ou na Secretaria Municipal de Saúde.",
          conferido="18/10/2026", cancer=["colorretal"]),
    _item("gastrocentro_unicamp", "outros", "caminho", "Campinas",
          "Gastrocentro Unicamp: diagnóstico das doenças do aparelho digestivo",
          "centro da Unicamp que faz cerca de 700 exames gratuitos por mês; a página não diz quais exames, quem é "
          "encaminhada nem se atende a região de Rio Claro",
          "Gastrocentro – Unicamp",
          "https://gastrocentro.unicamp.br/",
          topicos=[
              ("O que a página informa", "O Centro de Diagnóstico de Doenças do Aparelho Digestivo (Gastrocentro) da "
                                         "Unicamp presta assistência em gastroenterologia e hepatologia, dentro de um "
                                         "sistema de saúde hierarquizado, além de formar profissionais e fazer "
                                         "pesquisa. Tem como visão ser um centro de referência regional em doenças do "
                                         "aparelho digestivo e na detecção e no tratamento do câncer do aparelho "
                                         "digestivo e do fígado. Faz cerca de 700 exames gratuitos por mês, de quase "
                                         "duas dezenas de procedimentos."),
              ("Equipe e parceria", "Integra as áreas de cirurgia, pediatria, radiologia, anatomia patológica, "
                                    "imunologia, metabologia e obesidade. A página cita uma parceria com a agência "
                                    "japonesa Jica desde 1990, para capacitação e equipamentos voltados ao "
                                    "diagnóstico precoce de tumores do estômago, do intestino e do fígado."),
          ],
          como="A página não explica como a paciente chega ao serviço. Pelo SUS, o caminho começa na unidade de saúde "
               "do bairro, e a vaga em um serviço especializado vem pela regulação (veja \"Exame de intestino pelo "
               "SUS\").",
          cuidado="Este cartão é um cadastro, não uma vaga. O serviço não é porta de entrada confirmada.",
          confirmar="Falta confirmar com o serviço: quais exames faz (por exemplo, colonoscopia), quem pode ser "
                    "encaminhada e se atende pacientes da região de Rio Claro e Piracicaba. Conferido na página "
                    "institucional em 18/10/2026.",
          conferido="18/10/2026", cancer=["colorretal"]),
    _item("cancer_ovario", "outros", "caminho", "SUS (todo o Brasil)",
          "Câncer de ovário: sinais, exames e como buscar atendimento",
          "câncer nos ovários; no começo dá poucos sinais, e não existe exame de rastreamento para todas as mulheres",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/ovario/versao-para-populacao",
          para_quem="Qualquer mulher. Quem tem sinais que duram precisa de avaliação; quem tem câncer de mama ou de "
                    "ovário na família pode conversar com a equipe de saúde sobre o histórico.",
          topicos=[
              ("O que é", "Começa nos ovários, os órgãos dos dois lados do útero que produzem os óvulos e os "
                          "hormônios femininos."),
              ("Fatores de risco", "Câncer de ovário ou de mama na família, alterações genéticas herdadas (como BRCA1 "
                                   "e BRCA2) e a idade, entre outros. Ter um fator não significa que a mulher terá a "
                                   "doença."),
              ("Sinais que merecem avaliação", "No começo costuma não dar sinais, ou dar sinais comuns a outras "
                                               "condições: barriga inchada ou aumentada por muito tempo, dor ou "
                                               "pressão na parte baixa da barriga (pelve), sensação de estar cheia "
                                               "logo ao comer, mudanças no intestino ou na bexiga. Se duram, vale "
                                               "avaliação. Não confirmam câncer."),
              ("Prevenção, diagnóstico precoce e rastreamento", "Não há um exame de rastreamento recomendado para "
                                                                 "todas as mulheres: nem o ultrassom nem o exame de "
                                                                 "sangue servem para procurar câncer de ovário em "
                                                                 "quem não tem sintomas. Por isso, o que mais ajuda "
                                                                 "é não ignorar sinais que duram e conversar com a "
                                                                 "equipe sobre o histórico da família."),
              ("Como se investiga", "Exame ginecológico, ultrassom (muitas vezes pela via vaginal) e, quando indicado, "
                                    "tomografia, ressonância e exames de sangue. A confirmação costuma vir da "
                                    "análise do tecido retirado em biópsia ou cirurgia."),
              ("Tratamento", "Em geral envolve cirurgia e, muitas vezes, quimioterapia. A equipe de ginecologia "
                             "oncológica define o plano."),
              ("Depois do diagnóstico", "O acompanhamento regular depois do tratamento faz parte do cuidado."),
          ],
          como="Comece pela unidade de saúde ou pelo ginecologista da rede: eles avaliam, pedem exames e encaminham. "
               "O atendimento especializado em ginecologia oncológica é organizado pela regulação (CROSS). Na área "
               "Hospitais no Estado há centros com ginecologia oncológica, como o Hospital da Mulher (capital) e o "
               "CAISM da Unicamp.",
          cuidado="Não existe exame que \"garanta\" a ausência de câncer de ovário. Procure atendimento se os sinais "
                  "duram ou pioram.",
          confirmar="Texto escrito a partir de conhecimento geral e de busca na web em 18/10/2026; a página do INCA "
                    "não pôde ser aberta pela nuvem. Conferir o texto na página oficial antes de tirar esta marca.",
          conferido="18/10/2026", cancer=["ovario"]),
    _item("cancer_pele", "outros", "caminho", "SUS (todo o Brasil)",
          "Câncer de pele não melanoma: sinais, exames e como buscar atendimento",
          "o tipo de câncer de pele mais comum; ferida que demora a cicatrizar ou que sangra merece avaliação, mas "
          "nem toda lesão de pele é câncer",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/pele-nao-melanoma/versao-para-populacao",
          para_quem="Qualquer pessoa. Quem tem pele clara ou ficou muito tempo exposta ao sol precisa observar mais a "
                    "própria pele.",
          topicos=[
              ("O que é", "Começa nas células da pele, mais nas áreas expostas ao sol (rosto, orelhas, pescoço, couro "
                          "cabeludo, ombros e costas). Os tipos mais comuns são o carcinoma basocelular e o "
                          "espinocelular. O melanoma é outro tipo de câncer de pele, mais raro e mais agressivo, com "
                          "cuidados próprios; pintas que mudam de cor, forma ou tamanho merecem avaliação."),
              ("Fatores de risco", "Exposição ao sol ao longo da vida, pele, olhos e cabelos claros, queimaduras de sol, "
                                   "bronzeamento artificial, lesões de pele anteriores e histórico na família. Quem "
                                   "trabalha ao ar livre fica mais exposto."),
              ("Sinais que merecem avaliação", "Ferida que demora a cicatrizar, que sangra ou forma casca; mancha ou "
                                               "caroço que cresce, muda de cor ou de forma, coça ou descama sem "
                                               "melhorar. Muitas lesões de pele não são câncer: só quem examina pode "
                                               "dizer."),
              ("Prevenção, diagnóstico precoce e rastreamento", "O principal cuidado é a proteção contra o sol: evitar "
                                                                 "os horários de sol mais forte (entre 10h e 16h), "
                                                                 "usar chapéu, roupa e protetor solar. Este guia não "
                                                                 "apresenta um exame de rastreamento para todas as "
                                                                 "mulheres: o que ajuda é olhar a própria pele e "
                                                                 "procurar avaliação quando algo muda."),
              ("Como se investiga", "O médico examina a lesão (o dermatologista, quando disponível) e, se preciso, "
                                    "retira um pedaço pequeno para biópsia, que confirma ou afasta o câncer."),
              ("Tratamento", "Em geral, cirurgia para retirar a lesão; há outras técnicas conforme o caso. Costuma "
                             "responder bem quando é tratado cedo."),
              ("Depois do diagnóstico", "Continuar observando a pele e se proteger do sol; a equipe diz a frequência "
                                        "dos retornos."),
          ],
          como="Comece pela unidade de saúde do bairro, que examina e, se preciso, encaminha ao dermatologista pela "
               "regulação (CROSS). O Hospital de Amor, em Barretos, também faz teledermatologia nas ações de "
               "prevenção (veja \"Prevenção do Hospital de Amor\").",
          cuidado="Ferida que não fecha, que sangra ou muda rápido merece consulta, não espera.",
          confirmar="Texto escrito a partir de conhecimento geral e de busca na web em 18/10/2026; a página do INCA "
                    "não pôde ser aberta pela nuvem. Conferir o texto na página oficial antes de tirar esta marca. "
                    "O melanoma tem página própria no INCA.",
          conferido="18/10/2026", cancer=["pele"]),
    _item("cancer_pulmao", "outros", "caminho", "SUS (todo o Brasil)",
          "Câncer de pulmão: sinais, exames e como buscar atendimento",
          "o tabaco é o principal fator de risco; tosse que dura, tosse com sangue e falta de ar merecem avaliação, "
          "mas têm muitas causas",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/pulmao/versao-para-populacao",
          para_quem="Qualquer pessoa. Quem fuma, já fumou ou convive com a fumaça do tabaco tem mais motivo para "
                    "observar a respiração e para procurar ajuda para parar de fumar.",
          topicos=[
              ("O que é", "Começa nas células do pulmão. Pode demorar a dar sinais."),
              ("Fatores de risco", "O principal é o tabaco (cigarro, charuto, cachimbo, narguilé), inclusive a fumaça de "
                                   "outras pessoas. Também pesam substâncias do trabalho (como o amianto), a poluição "
                                   "e o histórico na família. Quem nunca fumou também pode ter, com menos frequência."),
              ("Sinais que merecem avaliação", "Tosse que dura semanas ou muda de característica, tosse com sangue ou "
                                               "catarro com sangue, falta de ar, chiado, dor no peito ao respirar, "
                                               "rouquidão, cansaço e perda de peso sem explicação. Também são sinais de "
                                               "muitas doenças do pulmão e do coração e não confirmam câncer."),
              ("Prevenção, diagnóstico precoce e rastreamento", "Não começar a fumar e parar de fumar são as formas "
                                                                 "mais eficazes de reduzir o risco, e as unidades de "
                                                                 "saúde do SUS oferecem apoio para parar (pergunte pelo "
                                                                 "programa de tratamento do tabagismo). O rastreamento "
                                                                 "com tomografia de baixa dose, para pessoas de alto "
                                                                 "risco e sem sintomas, é estudado, mas, pelas "
                                                                 "informações consultadas, não é rotina do SUS e não é "
                                                                 "um exame para todas as mulheres."),
              ("Como se investiga", "Radiografia ou tomografia do tórax e, quando indicado, broncoscopia e biópsia, "
                                    "que confirma ou afasta o câncer."),
              ("Tratamento", "Depende do tipo e da fase: pode envolver cirurgia, radioterapia, quimioterapia e outros "
                             "tratamentos. Quem define é a equipe de oncologia."),
              ("Depois do diagnóstico", "Seguir o acompanhamento e, para quem fuma, parar de fumar faz parte do cuidado."),
          ],
          como="Comece pela unidade de saúde do bairro: ela avalia, pede os exames e encaminha. O encaminhamento ao "
               "especialista e ao hospital de oncologia é feito pela regulação (CROSS).",
          cuidado="Tosse com sangue ou falta de ar forte: procure um pronto atendimento ou ligue 192.",
          confirmar="Texto escrito a partir de conhecimento geral e de busca na web em 18/10/2026; a página do INCA "
                    "não pôde ser aberta pela nuvem. A situação do rastreamento com tomografia no SUS está em "
                    "mudança: conferir na página oficial antes de tirar esta marca.",
          conferido="18/10/2026", cancer=["pulmao"]),
    _item("cancer_tireoide", "outros", "caminho", "SUS (todo o Brasil)",
          "Câncer de tireoide: nódulo no pescoço, exames e como buscar atendimento",
          "a maioria dos nódulos na tireoide não é câncer, mas um nódulo no pescoço merece avaliação",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/tireoide/versao-para-populacao",
          para_quem="Qualquer pessoa; é mais frequente em mulheres. Quem notou um nódulo ou uma mudança no pescoço "
                    "deve ser avaliada.",
          topicos=[
              ("O que é", "A tireoide é uma glândula na frente do pescoço que regula o funcionamento do corpo. O câncer "
                          "de tireoide começa nas células dessa glândula."),
              ("Fatores de risco", "Radiação na região do pescoço (principalmente na infância), histórico de câncer de "
                                   "tireoide na família e algumas alterações genéticas. Na maior parte dos casos, não "
                                   "se identifica uma causa."),
              ("Sinais que merecem avaliação", "Caroço ou nódulo no pescoço, rouquidão que não passa, dificuldade para "
                                               "engolir ou respirar. Muitas vezes o nódulo é descoberto num exame feito "
                                               "por outro motivo. Nódulo não significa câncer: a maioria é benigna."),
              ("Prevenção, diagnóstico precoce e rastreamento", "Este guia não apresenta um exame de rastreamento da "
                                                                 "tireoide para todas as mulheres: a indicação de "
                                                                 "exames depende da avaliação do médico."),
              ("Como se investiga", "Exame do pescoço, ultrassom da tireoide e, quando o médico indica, punção do nódulo "
                                    "com agulha fina para análise. Os exames de sangue dos hormônios mostram como a "
                                    "glândula funciona, não se há câncer."),
              ("Tratamento", "Em geral, cirurgia, às vezes complementada por outros tratamentos. A equipe orienta o uso "
                             "de qualquer medicamento."),
              ("Depois do diagnóstico", "O acompanhamento é de longo prazo, com consultas e exames periódicos."),
          ],
          como="Comece pela unidade de saúde do bairro: ela examina, pede o ultrassom e encaminha ao endocrinologista "
               "ou ao cirurgião de cabeça e pescoço pela regulação (CROSS).",
          cuidado="Nódulo que cresce rápido, rouquidão que não passa ou dificuldade para engolir ou respirar pedem "
                  "consulta sem demora.",
          confirmar="Texto escrito a partir de conhecimento geral e de busca na web em 18/10/2026; a página do INCA "
                    "não pôde ser aberta pela nuvem. Conferir o texto na página oficial antes de tirar esta marca.",
          conferido="18/10/2026", cancer=["tireoide"]),
    _item("cancer_corpo_utero", "outros", "caminho", "SUS (todo o Brasil)",
          "Câncer do corpo do útero (endométrio): não é o mesmo que o do colo do útero",
          "sangramento pela vagina depois da menopausa merece avaliação; o preventivo (Papanicolau) é do colo do "
          "útero e não procura este câncer",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/corpo-do-utero/versao-para-populacao",
          para_quem="Mulheres que tiveram sangramento depois da menopausa ou sangramentos fora do padrão. Os fatores "
                    "de risco aumentam com a idade.",
          topicos=[
              ("O que é", "Começa no corpo do útero, a parte de cima, geralmente no endométrio, o revestimento por "
                          "dentro. O colo do útero é outra parte, a de baixo, que liga o útero à vagina: o câncer do "
                          "colo é outra doença, ligada ao vírus HPV, com outros exames e cuidados."),
              ("Fatores de risco", "Idade (é mais comum depois da menopausa), excesso de peso, diabetes, uso de "
                                   "estrogênio sem acompanhamento e histórico na família. Ter um fator não significa "
                                   "que a mulher terá a doença."),
              ("Sinais que merecem avaliação", "O sinal mais importante é o sangramento pela vagina depois da "
                                               "menopausa: qualquer sangramento, mesmo pouco, deve ser avaliado. Antes "
                                               "da menopausa, sangramentos fora do período, muito intensos ou que se "
                                               "repetem também. Têm várias causas, e a maioria não é câncer: só a "
                                               "avaliação diz."),
              ("Prevenção, diagnóstico precoce e rastreamento", "O preventivo (Papanicolau) e o teste de HPV procuram o "
                                                                 "câncer do colo do útero, não o do corpo do útero. "
                                                                 "Este guia não apresenta um exame de rastreamento "
                                                                 "do corpo do útero para todas as mulheres sem sinais: "
                                                                 "o sinal de alerta é o sangramento anormal."),
              ("Como se investiga", "Ultrassom pela via vaginal e biópsia do endométrio (às vezes com histeroscopia, "
                                    "que olha por dentro do útero). A biópsia confirma ou afasta o câncer."),
              ("Tratamento", "Em geral, cirurgia, que pode ser complementada por radioterapia, quimioterapia ou "
                             "tratamento hormonal, conforme a extensão. A equipe de ginecologia oncológica define."),
              ("Depois do diagnóstico", "O acompanhamento regular depois do tratamento faz parte do cuidado."),
          ],
          como="Comece pela unidade de saúde ou pelo ginecologista da rede: eles avaliam, pedem o ultrassom e "
               "encaminham. O atendimento em ginecologia oncológica é organizado pela regulação (CROSS); na área "
               "Hospitais no Estado há centros com ginecologia oncológica, como o CAISM da Unicamp e o Hospital da "
               "Mulher (capital).",
          cuidado="Sangramento forte ou com tontura: procure um pronto atendimento ou ligue 192.",
          confirmar="Texto escrito a partir de conhecimento geral e de busca na web em 18/10/2026; a página do INCA "
                    "não pôde ser aberta pela nuvem. Conferir o texto na página oficial antes de tirar esta marca.",
          conferido="18/10/2026", cancer=["endometrio"]),
    _item("inca_tipos_cancer", "outros", "caminho", "SUS (todo o Brasil)",
          "Outros tipos de câncer: páginas do INCA para a população",
          "o INCA tem uma página para cada tipo de câncer; use-a quando o tipo não estiver detalhado neste guia",
          "INCA (Instituto Nacional de Câncer)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tipos/",
          para_quem="Quem procura um tipo de câncer que este guia ainda não detalha.",
          como="Na página, escolha o tipo de câncer. Para ser atendida, o caminho no SUS é o mesmo: unidade de saúde, "
               "exames, regulação e hospital habilitado em oncologia (portas Diagnóstico, Regulação e Rede oncológica).",
          confirmar="Link do INCA indicado pelo projeto; a página não pôde ser aberta pela nuvem.",
          conferido="18/10/2026"),

    # ---------------- DIAGNÓSTICO: depois que aparece uma alteração ----------------
    # ---------------- REGULAÇÃO: quando o nome não aparece ----------------
    _item("nao_achei_nome", "tratamento", "caminho", "SUS (todo o Brasil)",
          "Não achei meu nome na lista, ou a fila não anda: o que fazer",
          "procure a unidade que encaminhou; se não resolver, a Ouvidoria do SUS (Disque Saúde 136)",
          "Ministério da Saúde – Ouvidoria-Geral do SUS",
          "https://www.gov.br/saude/pt-br/canais-de-atendimento/ouvsus",
          como="Primeiro, volte à unidade de saúde que fez o encaminhamento: ela tem o registro do pedido e pode "
               "conferir se ele entrou na regulação (SIRESP/CROSS). Se não resolver, registre uma manifestação na "
               "Ouvidoria do SUS, pelo Disque Saúde 136 (segunda a sexta, das 8h às 20h; sábado, das 8h às 18h) ou "
               "pela internet, com a conta gov.br.",
          cuidado="A Secretaria da Saúde não publica um passo a passo para este caso: este é o caminho geral do SUS."),

    # ---------------- ENCONTRAR REFERÊNCIA: como chegar e listas oficiais ----------------
    _item("como_chegar_cross", "tratamento", "caminho", "Estado de SP",
          "Como se chega a um hospital de referência pelo SUS",
          "os hospitais de câncer não são porta de entrada: a unidade de saúde pede a vaga pela regulação (CROSS)",
          "ICESP e HC Unicamp (orientações aos pacientes)",
          "https://icesp.org.br/como-ser-atendido/",
          como="Com suspeita ou diagnóstico de câncer, procure a unidade de saúde (UBS) mais próxima de casa. O médico "
               "do SUS insere o caso na Central de Regulação de Oferta de Serviços de Saúde (CROSS/SIRESP), que "
               "encaminha a paciente a um centro de oncologia perto de onde ela mora, seguindo protocolos clínicos. "
               "É a Rede Hebe Camargo de Combate ao Câncer, do Estado.",
          tambem=[("hospitais", "Como chegar e listas oficiais")],
          tambem_caminhos=["direitos"]),
    _item("fosp_hospitais_sus", "tratamento", "caminho", "Estado de SP",
          "Lista oficial: hospitais do SUS com atendimento em câncer no Estado",
          "a lista da FOSP com todos os hospitais habilitados (CACON e UNACON) do Estado de São Paulo",
          "Fundação Oncocentro de São Paulo (FOSP) – Espaço do Paciente",
          "https://fosp.saude.sp.gov.br/fosp/espaco-paciente/hospitais-do-sus-habilitadas-para-atendimento-em-"
          "cancer-no-estado-de-sao-paulo/",
          como="A lista completa e atualizada pelo Estado. Os hospitais desta área são os que a pesquisa encontrou "
               "com fonte; a lista da FOSP tem todos.",
          tambem=[("hospitais", "Como chegar e listas oficiais")]),
    _item("inca_onde_tratar", "tratamento", "caminho", "SUS (todo o Brasil)",
          "Onde tratar pelo SUS (INCA)",
          "a página do Instituto Nacional de Câncer com os hospitais habilitados de cada estado",
          "Instituto Nacional de Câncer (INCA)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tratamento/onde-tratar-pelo-sus",
          como="UNACON trata os cânceres mais comuns; CACON trata todos os tipos. Os dois fazem do diagnóstico ao "
               "cuidado paliativo.",
          tambem=[("hospitais", "Como chegar e listas oficiais")]),

    # ================ LÂMINA HOSPITAIS NO ESTADO (por região) ================
    _item("hc_unicamp", "tratamento", "hospitais", "Campinas",
          "HC da Unicamp – Oncologia",
          "referência em câncer para as regiões de Campinas, Piracicaba (a de Rio Claro) e São João da Boa Vista",
          "HC Unicamp e Governo do Estado de SP",
          "https://www.hc.unicamp.br/especialidades/",
          como="Atende pacientes com câncer das DRS de Campinas, Piracicaba e São João da Boa Vista. Casos novos "
               "chegam pela Central Reguladora de Vagas da DRS VII; com diagnóstico de câncer, o médico do SUS "
               "insere o caso na CROSS. Tem também enfermagem, nutrição, serviço social, psicologia e odontologia.",
          contato="Oncologia Clínica: (19) 3521-7496 e (19) 3521-7363.",
          grupo="Campinas"),
    _item("icesp", "tratamento", "hospitais", "São Paulo (capital)",
          "ICESP – Instituto do Câncer do Estado de São Paulo",
          "hospital público estadual só de câncer; atende pacientes encaminhados pela regulação",
          "ICESP",
          "https://icesp.org.br/como-ser-atendido/",
          para_quem="Pacientes do SUS. É uma das unidades do Hospital das Clínicas da Faculdade de Medicina da USP, "
                    "com atendimento exclusivo pela rede pública de saúde.",
          topicos=[
              ("As quatro unidades (página institucional do ICESP)",
               "Unidade Hospitalar, na Av. Dr. Arnaldo, 251 (a matriz, com a maior parte dos atendimentos). Unidade "
               "Ambulatorial de Osasco, na R. Benedito Américo de Oliveira, 122 (oncologia clínica, radioterapia e "
               "equipe multiprofissional). Farmácia Ambulatorial, na R. da Consolação, 2049 (medicamentos para "
               "pacientes oncológicos). Instituto de Tratamento do Câncer Infantil (Itaci), na R. Galeno de Almeida, "
               "148, em Pinheiros (oncologia pediátrica, pelo SUS)."),
              ("Números da página (fevereiro de 2024)", "Mais de 146 mil pacientes atendidos desde a inauguração, em "
                                                        "2008, cerca de 40 mil pacientes ativos e 528 leitos."),
          ],
          como="Atende só pacientes encaminhados pela rede estadual (UBS, AMEs e hospitais gerais), pela Central de "
               "Regulação (CROSS), priorizando as regiões que têm o ICESP como referência. Não é porta de entrada: "
               "a vaga vem pela regulação, a partir da unidade de saúde.",
          contato="(11) 3893-2000.",
          conferido="18/10/2026",
          grupo="Capital e Grande São Paulo"),
    _item("hospital_da_mulher_sp", "tratamento", "hospitais", "São Paulo (capital)",
          "Hospital da Mulher (antigo Pérola Byington)",
          "centro estadual de referência em saúde da mulher: câncer de mama, de útero e de ovário",
          "Secretaria de Estado da Saúde de SP e Hospital da Mulher",
          "https://hospitaldamulhersp.org.br/",
          como="Referência estadual do SUS em saúde da mulher, com ênfase no câncer de mama e ginecológico: milhares de "
               "cirurgias por ano de tumores de mama, útero e ovário. Também atende violência sexual (caminho "
               "Proteger).",
          confirmar="O hospital mudou de nome e de prédio: confira endereço e telefone na página oficial.",
          grupo="Capital e Grande São Paulo",
          tambem_caminhos=["mama", "colo"]),
    _item("ibcc", "tratamento", "hospitais", "São Paulo (capital)",
          "IBCC Oncologia – Instituto Brasileiro de Controle do Câncer",
          "pioneiro no controle do câncer de mama e ginecológico em São Paulo; atende SUS e convênios",
          "IBCC",
          "https://www.ibcc.org.br/",
          como="Centro de oncologia de alta complexidade fundado em 1968, com oncologia clínica, cirurgia oncológica, "
               "mastologia e exames como mamografia e biópsia. Atende pacientes do SUS e de convênios.",
          contato="Av. Alcântara Machado, 2576 – Mooca. (11) 3474-4222.",
          confirmar="Pelo SUS, o acesso é pela regulação: confirme com a unidade de saúde.",
          grupo="Capital e Grande São Paulo"),
    _item("hc_ribeirao", "tratamento", "hospitais", "Ribeirão Preto",
          "HC de Ribeirão Preto (FMRP-USP) – Oncologia Clínica",
          "referência da Rede Hebe Camargo; recebe pacientes encaminhados pela CROSS",
          "Oncologia Clínica – FMRP-USP",
          "https://oncologia.fmrp.usp.br/regulacao-de-pacientes/",
          como="Recebe pacientes com diagnóstico de câncer vindos das unidades básicas, ambulatórios e hospitais "
               "gerais, sempre encaminhados pela Central de Regulação (CROSS). Não há atendimento direto.",
          contato="Av. Bandeirantes, 3900 – HC, 7º andar – Campus USP, Ribeirão Preto.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("cancer_franca", "tratamento", "hospitais", "Franca",
          "Hospital do Câncer do Grupo Santa Casa de Franca",
          "atende pelo SUS Franca e mais 20 municípios, com radioterapia e quimioterapia",
          "Grupo Santa Casa de Franca",
          "https://www.gruposantacasadefranca.com.br/hospital-do-cancer/",
          como="Hospital de referência regional em câncer, com consultas, radioterapia, quimioterapia e "
               "hormonioterapia pelo SUS para cerca de 750 mil habitantes da região.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("santa_casa_araraquara", "tratamento", "hospitais", "Araraquara",
          "Hospital do Câncer da Santa Casa de Araraquara",
          "UNACON com quimioterapia, radioterapia e onco-hematologia; referência regional do SUS",
          "Santa Casa de Araraquara",
          "https://santacasaararaquara.com.br/oncologia/",
          como="Habilitada como UNACON pelo Ministério da Saúde. Atende pelo SUS e convênios, com equipe "
               "multiprofissional.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("santa_casa_sao_carlos", "tratamento", "hospitais", "São Carlos",
          "Santa Casa de São Carlos – Oncologia",
          "UNACON com radioterapia, para cerca de 390 mil habitantes da microrregião",
          "Santa Casa de São Carlos",
          "https://www.santacasasaocarlos.com.br/",
          como="Habilitada como UNACON com radioterapia: diagnóstico e tratamento do câncer pelo SUS.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("santa_casa_aracatuba", "tratamento", "hospitais", "Araçatuba",
          "Santa Casa de Araçatuba – Centro de Tratamento Oncológico",
          "UNACON com radioterapia e hematologia, referência para 40 municípios",
          "Santa Casa de Araçatuba",
          "https://www.santacasadearacatuba.com.br/",
          como="Integra a Rede Hebe Camargo. Referência para o tratamento especializado de quase todos os tipos de "
               "câncer na região.",
          grupo="Rio Preto, Araçatuba e Jales (RRAS 12)"),
    _item("hospital_de_amor_jales", "tratamento", "hospitais", "Jales",
          "Hospital de Amor Jales",
          "a primeira unidade do Hospital de Amor fora de Barretos, 100% SUS",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/hospital-de-amor-jales/",
          como="Inaugurado em 2010, atende 100% pelo SUS, com radioterapia de alta precisão e cirurgias oncológicas.",
          grupo="Rio Preto, Araçatuba e Jales (RRAS 12)"),
    _item("amaral_carvalho", "tratamento", "hospitais", "Jaú",
          "Hospital Amaral Carvalho",
          "referência nacional em câncer e transplante de medula óssea; quase toda a capacidade é para o SUS",
          "Hospital Amaral Carvalho",
          "https://www.amaralcarvalho.org.br/informacoes",
          como="Hospital filantrópico de 1915, com cerca de 320 leitos. Para saber como ser atendida, procure o "
               "Serviço Social do hospital.",
          contato="Rua Dona Silvéria, 150 – Chácara Braz Miraglia, Jaú. (14) 3602-1200.",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("hc_botucatu", "tratamento", "hospitais", "Botucatu",
          "HC da Faculdade de Medicina de Botucatu (Unesp) – Oncologia",
          "centro de oncologia de referência regional, com quimioterapia e onco-hematologia",
          "HC Botucatu (Unesp)",
          "https://www.hcfmb.sp.gov.br/hcfmb",
          como="Referência regional: cerca de 17 mil consultas e 18 mil sessões de quimioterapia por ano (2021).",
          confirmar="O site do hospital mudou de endereço e a página específica de oncologia não foi localizada: o botão abre "
                    "o site geral do HC de Botucatu.",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("bauru_oncologia", "tratamento", "hospitais", "Bauru",
          "Bauru: SOPC (prevenção e diagnóstico) e Hospital Estadual de Bauru",
          "o SOPC investiga a suspeita de câncer e encaminha ao tratamento pela Rede Hebe Camargo",
          "Prefeitura de Bauru",
          "https://www2.bauru.sp.gov.br/materia.aspx?n=37669",
          como="O Serviço de Orientação e Prevenção do Câncer (SOPC), 100% SUS, atende Bauru e mais 17 cidades da "
               "DRS VI: recebe a suspeita de câncer vinda da rede básica e encaminha os casos confirmados aos "
               "hospitais de referência. O Hospital Estadual de Bauru é UNACON.",
          confirmar="A habilitação do Hospital Estadual de Bauru veio de lista de associação de pacientes: confira na "
                    "lista da FOSP.",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("hc_famema", "tratamento", "hospitais", "Marília",
          "HC da Famema (Marília) – Oncologia",
          "alta complexidade em câncer, com quimioterapia e radioterapia, para 62 municípios",
          "HC Famema (Governo do Estado de SP)",
          "https://www.hcfamema.sp.gov.br/hcfamema",
          como="Referência de média e alta complexidade para cerca de 1,2 milhão de pessoas do centro-oeste paulista, "
               "com quimioterapia e radioterapia.",
          confirmar="A habilitação mudou em 2026 (de CACON para UNACON com radioterapia, segundo notícia): confira "
                    "na lista da FOSP.",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("prudente_cancer", "tratamento", "hospitais", "Presidente Prudente",
          "Hospital Regional do Câncer de Presidente Prudente (Hospital de Esperança)",
          "UNACON com hematologia, oncologia pediátrica e radioterapia pelo SUS",
          "Agência Brasil – credenciamento de 2021",
          "https://agenciabrasil.ebc.com.br/saude/noticia/2021-07/hospital-do-cancer-de-presidente-prudente-sera-credenciado-ao-sus",
          como="Credenciado em 2021 como UNACON, com 122 leitos para o SUS. Na cidade, a lista do Ministério da Saúde "
               "(habilitação 2023) traz também o Hospital Regional Dr. Domingos Leonardo Cerávolo, UNACON com hematologia.",
          confirmar="Notícia de 2021 (o hospital hoje se chama Hospital de Esperança): confira na lista da FOSP.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),
    _item("sorocaba_oncologia", "tratamento", "hospitais", "Sorocaba",
          "Sorocaba: Santa Casa (Hospital do Câncer) e Conjunto Hospitalar",
          "Santa Casa: UNACON com radioterapia; Conjunto Hospitalar: UNACON com hematologia",
          "Prefeitura de Sorocaba (Agência de Notícias)",
          "https://noticias.sorocaba.sp.gov.br/hospital-do-cancer-da-santa-casa-inaugura-consultorio-odontologico/",
          como="A Santa Casa de Sorocaba é UNACON desde 2008 e tem radioterapia com acelerador linear desde 2020, com "
               "equipe multiprofissional.",
          confirmar="A habilitação do Conjunto Hospitalar veio de lista de associação de pacientes: confira na lista "
                    "da FOSP.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),
    _item("pio_xii_sjc", "tratamento", "hospitais", "São José dos Campos",
          "Hospital Pio XII (São José dos Campos)",
          "UNACON do Vale do Paraíba; mais de 80% dos pacientes são do SUS",
          "Hospital Pio XII",
          "https://www.hpioxii.org.br/o-hospital/",
          como="Referência em oncologia (UNACON) desde 1977 para São José dos Campos e o Vale do Paraíba.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),
    _item("guilherme_alvaro", "tratamento", "hospitais", "Santos",
          "Hospital Guilherme Álvaro (Santos)",
          "UNACON com radioterapia; unidade regional do ICESP na Baixada Santista",
          "Secretaria de Estado da Saúde de SP",
          "https://www.saude.sp.gov.br/humanizacao/unidades-participantes/hospitais-e-outros-servicos-de-saude/"
          "hospital-guilherme-alvaro/informacoes-gerais",
          como="Hospital estadual de referência da Baixada Santista, com centro de referência em câncer ligado ao "
               "ICESP.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),

    # ---------------- PROTEGER (mais rede de apoio no Estado) ----------------
    _item("casa_mulher_brasileira", "ajuda", "caminho", "São Paulo (capital)",
          "Casa da Mulher Brasileira",
          "24 horas: delegacia, Defensoria, Ministério Público, juiz de medida protetiva e IML no mesmo lugar",
          "Ministério das Mulheres (Governo Federal)",
          "https://www.gov.br/mulheres/pt-br/central-de-conteudos/noticias/2026/agosto-defeso-eleitoral/casa-da-"
          "mulher-brasileira-como-funciona-o-atendimento-e-onde-encontrar-uma-unidade",
          como="Acolhimento com apoio psicológico e assistencial, e no mesmo prédio a 1ª Delegacia de Defesa da "
               "Mulher, o Ministério Público, a Defensoria, um anexo do Tribunal de Justiça para medidas protetivas "
               "e o IML. Gratuito, com intérprete de Libras.",
          contato="Rua Vieira Ravasco, 26 – Cambuci, São Paulo. (11) 3275-8000. 24 horas, todos os dias."),
    _item("ddm_estado", "ajuda", "caminho", "Estado de SP",
          "Delegacias de Defesa da Mulher (DDM)",
          "registrar ocorrência e pedir medida protetiva; há salas DDM 24 horas em todo o Estado",
          "Governo do Estado de SP (SP por Todas / Agência SP)",
          "https://www.spportodas.sp.gov.br/sp-por-todas/seguranca_mulher/delegacias_da_mulher",
          como="A página do SP por Todas mostra a DDM ou a sala DDM 24 horas mais próxima. Pela internet, a "
               "Delegacia Eletrônica também registra a ocorrência."),
    _item("casas_mulher_paulista", "ajuda", "caminho", "Estado de SP",
          "Casas da Mulher Paulista",
          "acolhimento, apoio psicológico, orientação jurídica e ajuda para voltar ao trabalho",
          "Governo do Estado de SP (Secretaria da Mulher)",
          "https://www.spportodas.sp.gov.br/sp-por-todas/seguranca_mulher/casas%20da%20mulher%20paulista",
          como="Espaços do Estado que reúnem num lugar só atendimento psicológico, orientação jurídica, assistência "
               "social, capacitação profissional (currículo, entrevista) e prevenção à violência. Em 2024 foram "
               "abertas 15 novas unidades.",
          confirmar="Veja na página se há uma Casa da Mulher Paulista na sua cidade."),
    _item("defensoria_nudem", "ajuda", "caminho", "Estado de SP",
          "Defensoria Pública – Núcleo de Defesa dos Direitos das Mulheres",
          "advogada de graça: medida protetiva, divórcio, guarda e pensão para quem não pode pagar",
          "Defensoria Pública do Estado de SP",
          "https://www.defensoria.sp.def.br/nucleos-especializados/pagina-inicial-nucleos-especializados/"
          "promocao-e-defesa-dos-direitos-das-mulheres",
          como="Pede medida protetiva mesmo sem boletim de ocorrência, orienta, recorre quando a medida é negada e "
               "cuida de divórcio, guarda e pensão. Atendimento gratuito para quem não pode pagar advogado; o "
               "agendamento é pelo site da Defensoria."),
    _item("violencia_sexual_24h", "ajuda", "caminho", "São Paulo (capital)",
          "Violência sexual: atendimento 24 horas (programa Bem-me-quer)",
          "no Hospital da Mulher (antigo Pérola Byington): atendimento médico, psicológico e jurídico, 24 horas",
          "Secretaria de Estado da Saúde de SP",
          "https://www.saude.sp.gov.br/humanizacao/homepage/destaques/conheca-o-nucleo-de-programas-especiais-npe-"
          "centro-de-referencia-da-saude-da-mulher",
          como="Referência no Estado: a porta nunca fecha. A mulher passa por médico, psicólogo, assistente social e "
               "perícia. A Defensoria mantém a lista da rede de atendimento à violência sexual nas outras regiões.",
          confirmar="O hospital mudou de prédio: confira o endereço antes de ir."),

    # ---------------- SEUS DIREITOS ----------------
    _item("tfd", "direitos", "caminho", "SUS (todo o Brasil)",
          "Tratamento Fora do Domicílio (TFD): transporte e diárias para tratar em outra cidade",
          "quando o tratamento não existe no município onde você mora, o SUS pode pagar transporte e diárias; o "
          "médico do SUS pede e uma comissão autoriza",
          "Ministério da Saúde – Portaria SAS/MS nº 55/1999 (rotina do TFD no SUS; cópia no portal da Ebserh)",
          "https://www.gov.br/hubrasil/pt-br/hospitais-universitarios/regiao-centro-oeste/hc-ufg/saude/"
          "consultas-e-retornos/Portaria_55_24021999.pdf",
          para_quem="Pacientes do SUS que precisam de tratamento que não existe no município onde moram (a portaria "
                    "fala em esgotados os meios de tratamento no próprio município).",
          como="O médico do SUS faz o pedido e uma comissão do município (ou do Estado) autoriza. Cobre transporte e "
               "diárias de alimentação e pernoite para a paciente e, se preciso, um acompanhante, dentro do limite "
               "financeiro do município ou do Estado. Depois da consulta, guarde o comprovante para a prestação de "
               "contas.",
          confirmar="O link abre o texto da portaria federal (um PDF), não uma página de orientação ao paciente. "
                    "Regras, distância mínima e valores variam por município e por Estado, e há notícia de uma lei "
                    "recente sobre o auxílio do TFD que não foi conferida: em Rio Claro, pergunte à Fundação "
                    "Municipal de Saúde onde se pede o TFD e quais são as regras de hoje.",
          conferido="18/10/2026"),
    _item("fgts_pis", "direitos", "caminho", "Todo o Brasil",
          "Saque do FGTS e do PIS/PASEP",
          "quem tem câncer pode sacar todo o FGTS e o PIS/PASEP na Caixa",
          "INCA – Direitos sociais da pessoa com câncer",
          "https://www.gov.br/inca/pt-br/acesso-a-informacao/perguntas-frequentes/direitos-sociais-da-pessoa-com-cancer",
          levar="Atestado médico (vale 30 dias), resultado da biópsia, exame que confirma o tipo de tumor, RG, CPF e "
                "número do PIS/PASEP.",
          como="Vá a qualquer agência da Caixa Econômica Federal com os documentos."),
    _item("auxilio_inss", "direitos", "caminho", "Todo o Brasil",
          "Auxílio-doença (INSS) e isenção de imposto de renda",
          "afastamento do trabalho pago pelo INSS e isenção de IR sobre aposentadoria e pensão",
          "INCA – Direitos sociais da pessoa com câncer",
          "https://www.gov.br/inca/pt-br/acesso-a-informacao/perguntas-frequentes/direitos-sociais-da-pessoa-com-cancer",
          como="Quem contribui para o INSS e fica temporariamente sem poder trabalhar tem direito ao auxílio. A "
               "isenção de imposto de renda vale para aposentadoria, reforma e pensão: pede-se ao órgão que paga o "
               "benefício (INSS, prefeitura, Estado), com o formulário da Receita Federal."),
    _item("reconstrucao_mamaria", "direitos", "caminho", "SUS (todo o Brasil)",
          "Reconstrução da mama pelo SUS",
          "a mulher que retira a mama tem direito à reconstrução, de preferência na mesma cirurgia",
          "Senado Federal – Lei 12.802/2013",
          "https://www12.senado.leg.br/noticias/materias/2013/05/07/lei-garante-reconstrucao-da-mama-em-seguida-a-"
          "retirada-de-cancer",
          como="Quando há condições técnicas, a reconstrução é feita no mesmo ato da retirada do tumor. Se não for "
               "possível, a mulher é acompanhada e tem garantida a cirurgia assim que tiver condições clínicas. Não há "
               "limite de idade.",
          tambem_caminhos=["mama"]),
    _item("cartilha_inca", "direitos", "caminho", "Todo o Brasil",
          "Cartilha do INCA: direitos sociais da pessoa com câncer",
          "todos os direitos num lugar só, em linguagem simples",
          "Instituto Nacional de Câncer (INCA)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/orientacoes-aos-pacientes-e-familiares/orientacoes-aos-pacientes-e-familiares",
          como="Explica benefícios do INSS, FGTS e PIS, isenções, transporte, prioridade na Justiça e outros direitos."),

    # ---------------- CUIDAR (mais apoio) ----------------
    _item("ames_estado", "mama", "caminho", "Estado de SP",
          "AMEs – Ambulatórios Médicos de Especialidades",
          "especialistas e exames do Estado, marcados pela unidade básica de saúde",
          "Governo do Estado de SP",
          "https://saude.sp.gov.br/ses/perfil/cidadao/ambulatorio-medico-de-especialidades-ames/ambulatorio-medico-de-especialidades-ames",
          como="Os AMEs fazem consultas com especialistas e exames (muitos fazem mamografia). A consulta é marcada "
               "pela UBS do município, por sistema online.",
          confirmar="Página da Secretaria de Estado da Saúde trocada em 18/10/2026 (ainda não conferida pelo programa de links): para saber qual AME atende a sua região, pergunte na unidade de saúde."),
    _item("rede_feminina", "tratamento", "caminho", "Estado de SP",
          "Rede Feminina de Combate ao Câncer",
          "entidade voluntária que apoia pacientes com câncer e divulga a prevenção",
          "Rede Feminina de Combate ao Câncer do Estado de SP",
          "https://redefemininaesp.org.br/",
          como="Entidade filantrópica com núcleos em muitas cidades: apoio emocional e material a pacientes de baixa "
               "renda e informação sobre prevenção. Não é serviço público."),

    # ---------------- RIO CLARO (mais portas) ----------------
    _item("rc_ame", "mama", "rio_claro", "Rio Claro",
          "AME Rio Claro – Ambulatório Médico de Especialidades",
          "especialistas do Estado na cidade, inclusive mastologia (mama); marcado pela UBS",
          "AME Rio Claro",
          "https://amerioclaro.org.br/",
          como="Tem especialidade dedicada às mamas, na prevenção e no tratamento. O AME e as unidades de saúde têm "
               "ginecologista e mastologista; a marcação depende das vagas e é feita pela unidade de saúde, por meio da Central de Regulação. No cadastro nacional de estabelecimentos (CNES, 08/2026), o AME consta entre os "
               "poucos estabelecimentos de Rio Claro que fazem mamografia no próprio local; as unidades de saúde "
               "registram o exame como feito por outro estabelecimento. A unidade orienta onde o exame será feito.",
          contato="Rua 9 (esquina com a Avenida da Saudade), 165 – Bairro dos Estádios. (19) 3526-2300.",
          confirmar="As fontes trazem dois números para o endereço (Rua 9, 165, e Avenida da Saudade, 252): são compatíveis, "
                    "porque o AME fica na esquina das duas ruas (informação de quem trabalha na Fundação, 19/10/2026). Algumas "
                    "fontes trazem outro telefone: confirme o telefone na unidade de saúde antes de ir."),
    _item("rc_cead", "mama", "rio_claro", "Rio Claro",
          "CEAD – centro municipal de especialidades e apoio diagnóstico",
          "a unidade municipal onde ficam a mastologia e o ultrassom da mama, para quem a unidade de saúde encaminha",
          "Fundação Municipal de Saúde de Rio Claro (protocolos de câncer de mama, rev. 01, 2026, e de exames, rev. 03, 2026)",
          "https://www.saude-rioclaro.org.br/enderecos.htm",
          para_quem="Moradoras de Rio Claro encaminhadas pela unidade de saúde.",
          como="Pelo protocolo da Fundação, a mulher com nódulo suspeito, exame de imagem alterado (BI-RADS 4 ou 5) ou "
               "risco alto de câncer de mama é encaminhada pela unidade ao mastologista do CEAD. O ultrassom da mama é "
               "pedido pela unidade conforme critérios clínicos, não como exame de rotina. O CEAD é municipal, da "
               "Fundação, e é um serviço diferente do AME, que é do Estado. Mulher com câncer confirmado segue para o "
               "tratamento na Santa Casa de Rio Claro.",
          contato="Avenida 24, nº 1040, entre as ruas 8 e 9. Atendimento de segunda a sexta-feira, das 7h às 16h.",
          confirmar="O telefone do CEAD ainda não foi confirmado para este cartão, e o endereço e o horário foram "
                    "informados por quem trabalha na Fundação (19/10/2026): pergunte na unidade de saúde. O que está aqui "
                    "vem do protocolo da Fundação e de chefias da Fundação."),
    _item("rc_ddm", "ajuda", "rio_claro", "Rio Claro",
          "Delegacia de Defesa da Mulher (DDM) de Rio Claro",
          "registrar ocorrência e pedir medida protetiva na cidade",
          "OAB Rio Claro e Polícia Civil",
          "https://www.oabrioclaro.org.br/noticias/delegacia-de-defesa-da-mulher-ddm/",
          como="Rio Claro tem DDM. Em perigo imediato, ligue 190; pela internet, use a Delegacia Eletrônica.",
          confirmar="Endereços e telefones diferentes aparecem em fontes diferentes: confirme pela página das "
                    "Delegacias da Mulher do SP por Todas antes de ir."),
    _item("rc_patrulha", "ajuda", "rio_claro", "Rio Claro",
          "Patrulha Maria da Penha (Guarda Civil Municipal)",
          "visitas e acompanhamento para mulheres com medida protetiva",
          "Prefeitura de Rio Claro (Secretaria de Segurança)",
          "https://seguranca.rioclaro.sp.gov.br/patrulha-maria-da-penha/",
          como="Criada em dezembro de 2018: a Guarda Civil visita as mulheres com medida protetiva e verifica se a "
               "decisão da Justiça está sendo cumprida. Trabalha com a DDM, o CREAS, o Conselho Tutelar, o CAPS e o "
               "Anexo de Violência Doméstica."),
    _item("rc_gacc", "tratamento", "rio_claro", "Rio Claro",
          "GACC Rio Claro – Grupo de Apoio à Criança com Câncer",
          "desde 1996: transporte 24 horas para consultas e tratamentos, apoio social e psicológico, para crianças e "
          "adolescentes com câncer e suas famílias",
          "GACC Rio Claro",
          "https://www.gacc-rc.org.br/",
          para_quem="Crianças e adolescentes com câncer ou doenças hematológicas crônicas, e suas famílias, de Rio "
                    "Claro e região.",
          como="O principal serviço é o transporte do paciente e da família para consultas, exames e tratamentos, 24 "
               "horas por dia. Oferece também apoio social e psicológico, dentista, cestas básicas e de hortifrúti, "
               "ajuda com remédios e exames, suplementação alimentar e reforço escolar.",
          contato="Av. P-17, 253 – Vila Paulista, Rio Claro. (19) 3534-5612. Segunda a sexta, das 8h às 17h.",
          cuidado="Entidade filantrópica (Associação Lute pela Vida), não é serviço público."),
    _item("rc_perucas", "tratamento", "rio_claro", "Rio Claro",
          "Curso de confecção de perucas para pacientes com câncer",
          "a Prefeitura promoveu curso para fazer perucas para quem perde o cabelo no tratamento",
          "Prefeitura de Rio Claro (Fundação Municipal de Saúde)",
          "https://rioclaro.sp.gov.br/fundacao-de-saude/rio-claro-promove-curso-de-confeccao-de-perucas-para-atender-"
          "pacientes-com-cancer/",
          como="Ação da Fundação Municipal de Saúde para atender pacientes com câncer que perdem o cabelo por causa do "
               "tratamento.",
          confirmar="Foi uma ação noticiada pela Prefeitura, sem data visível na busca: pergunte na Fundação "
                    "Municipal de Saúde se as perucas continuam sendo oferecidas."),
    _item("rc_rede_feminina", "tratamento", "rio_claro", "Rio Claro",
          "Rede Rio-Clarense \"Carmem Prudente\" (Rede Feminina de Combate ao Câncer)",
          "núcleo da Rede Feminina em Rio Claro: apoio voluntário a pacientes com câncer",
          "Rede Feminina de Combate ao Câncer (página do núcleo de Rio Claro)",
          "https://www.facebook.com/tukatrivelato/",
          como="Núcleo local da Rede Feminina, entidade filantrópica de apoio a pacientes com câncer de baixa renda. "
               "Não é serviço público.",
          confirmar="A única página encontrada é a do núcleo numa rede social: confirme o contato."),
]
GRUPOS_BARRETOS = ["Hospitais de referência", "Prevenção", "Câncer de mama", "Câncer do colo do útero",
                   "Tratamento e acesso pelo SUS", "Carretas e unidades móveis", "Ensino e pesquisa",
                   "No Estado de SP"]
GRUPOS_HOSPITAIS = ["Como chegar e listas oficiais", "Rio Claro e Piracicaba (RRAS 14)", "Campinas",
                    "Capital e Grande São Paulo", "Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)",
                    "Rio Preto, Araçatuba e Jales (RRAS 12)", "Centro-Oeste: Jaú, Bauru, Botucatu e Marília",
                    "Oeste, Sorocaba, Vale do Paraíba e Litoral"]
GRUPOS_CARRETAS = ["Carretas da Mamografia do Estado"]
GRUPOS = {"barretos": GRUPOS_BARRETOS, "hospitais": GRUPOS_HOSPITAIS, "carretas": GRUPOS_CARRETAS}

# "Preciso de ajuda": em que ponto a mulher está -> portas e itens.
# (id, rótulo, fala da Lia, portas indicadas, itens mostrados)
ETAPAS = [
    ("nao_fiz", "Ainda não fiz o exame",
     "O começo é a unidade de saúde do seu bairro: lá se faz o preventivo e se pede a mamografia. De 50 a 69 anos "
     "a mamografia pelo Estado não precisa de pedido médico, e as carretas atendem sem agendamento. Em Rio Claro, "
     "a consulta também pode ser marcada pelo Cadu (0800 019 0505, telefone ou WhatsApp).",
     ["mama", "colo"], ["rc_cadu_agendamento", "rc_unidades", "mulheres_de_peito", "colo_utero"]),
    ("alterado", "Meu exame deu alterado",
     "Respire: um exame alterado não é diagnóstico de câncer, e a maior parte das alterações não é. O primeiro passo "
     "é ir, com o laudo na mão, à unidade de saúde do seu bairro (UBS ou USF) e dizer: \"meu exame deu alterado\". "
     "Foi essa equipe que pediu o exame, e é ela quem organiza os próximos exames e o encaminhamento. Não sabe qual "
     "é a sua unidade? Em Rio Claro, ligue para o Cadu (0800 019 0505, telefone ou WhatsApp) ou use o botão "
     "\"Unidades, telefones e como chegar\", no alto da página. Se depois a resposta demorar, existem prazos "
     "legais: o de até 30 dias vale quando câncer é a principal hipótese diagnóstica e o médico responsável faz um "
     "pedido fundamentado.",
     [], ["rc_unidades", "rc_cadu_agendamento"]),
    ("encaminhada", "Fui encaminhada",
     "Depois do encaminhamento, a vaga é organizada pela regulação do Estado. Você pode acompanhar a fila da "
     "oncologia e, se o nome não aparecer, sabe onde procurar ajuda.",
     [], ["lista_regulacao", "nao_achei_nome", "como_chegar_cross"]),
    ("diagnostico_cancer", "Recebi diagnóstico de câncer",
     "Converse com a equipe de saúde que acompanha seu caso para saber quem está responsável pelo encaminhamento e "
     "como acompanhar a vaga. O primeiro tratamento no SUS tem prazo de até 60 dias a partir do diagnóstico em "
     "laudo patológico, ou prazo menor conforme a necessidade terapêutica registrada no prontuário.",
     ["tratamento", "direitos"], ["lei_60_dias", "como_chegar_cross", "cartilha_inca"]),
    ("em_tratamento", "Estou em tratamento",
     "Durante o tratamento, vale conhecer os seus direitos (transporte, FGTS, INSS) e o apoio de entidades como a "
     "Rede Feminina de Combate ao Câncer e, em Rio Claro, o GACC (para crianças e adolescentes).",
     ["tratamento", "direitos"], ["tfd", "fgts_pis", "auxilio_inss", "rede_feminina", "rc_gacc", "rc_perucas"]),
    ("violencia", "Estou em situação de violência",
     "Você não precisa passar por isso sozinha. Em perigo agora, ligue 190. Estes canais atendem, orientam e "
     "protegem.",
     [], []),  # os itens da porta "ajuda" (e os de Rio Claro)
]
NOME_ETAPA = {e: r for e, r, _, _, _ in ETAPAS}
POR_ID = {i["id"]: i for i in ITENS}

# Tipos de câncer que o guia distingue (chave -> nome): os sete que o Escudo acompanha mais o corpo do útero
# (endométrio), que NÃO é o colo do útero nem o ovário. Item específico de um câncer leva `cancer`; o que não leva
# serve a todos (rede, regulação, direitos). A busca (apoio_busca) usa isto para nunca levar quem citou um câncer ao
# conteúdo de outro. Os itens de mama e colo já existiam: a marca é posta aqui, sem mexer em cada definição.
TIPOS_CANCER = {"mama": "câncer de mama", "colo": "câncer do colo do útero",
                "colorretal": "câncer de intestino (colorretal)", "ovario": "câncer de ovário",
                "pele": "câncer de pele não melanoma", "pulmao": "câncer de pulmão",
                "tireoide": "câncer de tireoide", "endometrio": "câncer do corpo do útero (endométrio)"}
_MARCAS_CANCER = {
    "mama": ("mulheres_de_peito", "caminho_do_exame", "carretas_estado", "campinas_craim",
             "rio_preto_mamografia", "ha_mastologia", "mater_ribeirao",
             "reconstrucao_mamaria"),
    "colo": ("colo_utero", "vacina_hpv", "ha_colo_busca_ativa", "ha_pesquisa_hpv"),
}
_MARCAS_VARIOS = {   # itens que servem a mais de um tipo
    "piracicaba_cesm": ("mama", "colo"),
    "ha_prevencao": ("mama", "colo", "colorretal", "pele"),
    "hospital_da_mulher_sp": ("mama", "colo", "ovario", "endometrio"),
    "caism_unicamp": ("mama", "colo", "ovario", "endometrio"),
    "ibcc": ("mama", "colo", "ovario", "endometrio"),
}
for _tipo, _ids in _MARCAS_CANCER.items():
    for _id in _ids:
        POR_ID[_id]["cancer"] = (_tipo,)
for _id, _tipos in _MARCAS_VARIOS.items():
    POR_ID[_id]["cancer"] = _tipos
# CNES conferidos no banco do autor em 18/10/2026 (nome oficial na tabela `hospitais` e município do hospital em `internacoes`
# batem; 7400926 = Fundação Hospital Regional do Câncer, Presidente Prudente, 1.737 internações, conferido em 18/10/2026; 2082888 = Santa Casa de Rio Claro, 1.711 internações, conferido em 18/10/2026; confere com a lista do Ministério da Saúde de hospitais habilitados em oncologia). Uma lista de IA trazia também 9662561 para o Hospital de Amor: NÃO existe no banco; o real é 2090236 (Fundação Pio XII).
_CNES_CONFERIDOS = {"icesp": "6123740", "amaral_carvalho": "2083086", "hc_unicamp": "2079798",
                    "hc_ribeirao": "2082187", "ha_quem_e": "2090236",
                    "prudente_cancer": "7400926", "rc_santa_casa": "2082888"}
for _id, _cnes in _CNES_CONFERIDOS.items():
    POR_ID[_id]["cnes"] = _cnes
# Cada página do INCA fala de UMA doença (autor, 18/10/2026: "cada um fala de uma doença, mas precisamos de mais"). Os cartões de câncer da
# porta Outros cânceres ganham, ao lado do botão do INCA, os serviços que uma mulher doente usa. Os endereços vêm dos próprios
# cartões de serviço (uma casa só para cada link).
_MAIS_PARA_QUEM_ESTA_DOENTE = [
    ("Unidades de saúde de Rio Claro: onde começar", "rc_unidades"),
    ("Agendar consulta pelo Cadu (Rio Claro)", "rc_cadu_agendamento"),
    ("Como ser atendida num hospital de câncer (ICESP e HC Unicamp)", "como_chegar_cross"),
    ("Lista oficial dos hospitais do SUS com atendimento em câncer", "fosp_hospitais_sus"),
]
for _id in ("cancer_intestino", "jornada_exame_intestino", "cancer_ovario", "cancer_pele", "cancer_pulmao", "cancer_tireoide",
            "cancer_corpo_utero"):
    POR_ID[_id]["mais_links"] = [(rotulo, POR_ID[outro]["link"]) for rotulo, outro in _MAIS_PARA_QUEM_ESTA_DOENTE]
# Hospitais e a prevenção de Barretos que atendem câncer ginecológico também aparecem, em cartão curto, em "Outros cânceres".
for _id in ("hospital_da_mulher_sp", "caism_unicamp", "ha_prevencao"):
    POR_ID[_id]["tambem_caminhos"] = POR_ID[_id]["tambem_caminhos"] + ["outros"]


# ---------- auditoria de usabilidade (20/10/2026): preencher lacunas só com o que o próprio catálogo já afirma ----------
# Os hospitais da área "Hospitais no Estado" não são porta de entrada (a introdução da área e os cartões dizem isso):
# chega-se a eles pela unidade de saúde e pela regulação. Isso vira o "Para quem" dos que não tinham.
PARA_QUEM_HOSPITAL = "Mulheres encaminhadas pela unidade de saúde do bairro (não é porta de entrada)."
for _i in ITENS:
    if _i["lamina"] == "hospitais" and not _i["para_quem"]:
        _i["para_quem"] = PARA_QUEM_HOSPITAL
# Telefones que já estão verificados no cadastro da página "Onde ser atendida" (dados_geograficos/catalogo_servicos_rioclaro.json,
# verificado em 10 e 11/10/2026): o Apoio aponta para o mesmo número, sem tirar a marca "a confirmar" dos cartões.
POR_ID["rc_cead"]["contato"] += " Fones: (19) 3524-1463 / (19) 3524-1805 (cadastro de Onde ser atendida, verificado em 10/10/2026)."
POR_ID["rc_ddm"]["contato"] = "Fone: (19) 3533-9009 (cadastro de Onde ser atendida, verificado em 11/10/2026)."


def frase_carretas():
    """Orienta a consultar o itinerário oficial, sem reproduzir locais sujeitos a mudança."""
    return ("As cidades, datas e endereços das Carretas da Mamografia podem mudar. Antes de sair, consulte o "
            f"[itinerário no SP Por Todas]({URL_CARRETAS_SP_POR_TODAS}) ou as "
            f"[orientações do Poupatempo]({URL_CARRETAS_POUPATEMPO}).")


def itens(caminho=None, lamina=None):
    return [i for i in ITENS if (caminho is None or i["caminho"] == caminho)
            and (lamina is None or i["lamina"] == lamina)]


def do_grupo(lam, g):
    """Itens de um tema ou região: os que moram ali (cartão completo) e
    os que só aparecem ali ("tambem", cartão curto)."""
    casa = [i for i in ITENS if i["lamina"] == lam and i["grupo"] == g]
    visitas = [i for i in ITENS if (lam, g) in i["tambem"]]
    return casa, visitas


# ---------- ações (o que um botão faz) ----------

def caminho(id):
    return {"tipo": "apoio_caminho", "id": id}


def item(id):
    return {"tipo": "apoio_item", "id": id}


def lamina(id):
    return {"tipo": "apoio_lamina", "id": id}


ITEM_PRINCIPAL = {"colorretal": "cancer_intestino", "ovario": "cancer_ovario", "pele": "cancer_pele",
                  "pulmao": "cancer_pulmao", "tireoide": "cancer_tireoide", "endometrio": "cancer_corpo_utero"}


JORNADA_DO_TIPO = {"colorretal": "jornada_exame_intestino"}   # tipos que têm o passo a passo do exame além do cartão geral


def abertura_do_tipo(tipo):
    """A ação que abre o conteúdo principal de um tipo de câncer: a porta (mama, colo) ou o cartão específico."""
    if tipo in ("mama", "colo"):
        return caminho(tipo)
    return item(ITEM_PRINCIPAL[tipo])


def grupo(lam, id):
    return {"tipo": "apoio_grupo", "lamina": lam, "id": id}


def etapa(id):
    return {"tipo": "apoio_etapa", "id": id}


SOBRE = {"tipo": "apoio_sobre"}

AVISO = (f"Conferi em {CONFERIDO} nas páginas oficiais. Regras, endereços e telefones mudam: confirme antes de "
         "ir. Eu não sou médica; quem orienta o seu caso é a equipe de saúde.")

# Até quantos itens de outra lâmina um caminho mostra um a um; acima
# disso, só aponta a lâmina ("23 itens na lâmina Hospitais no Estado").
MAX_APONTADOS = 3


def _proximo(c):
    """O próximo passo da jornada (mama/colo → diagnóstico → regulação → tratamento → direitos)."""
    if c in PROXIMO:
        alvo = PROXIMO[c]
        if alvo.startswith("etapa:"):
            return [(f"Próximo passo: {NOME_ETAPA[alvo[6:]]}", etapa(alvo[6:]))]
        return [(f"Próximo passo: {NOME_CAMINHO[alvo]}", caminho(alvo))]
    return []


def nas_laminas(c):
    """{lâmina: itens} que moram fora desta porta mas servem a ela: os
    de outras lâminas com este caminho e os de outras portas marcados
    com "tambem_caminhos" (chave "caminho"). Aqui só se aponta."""
    fora = {}
    for i in ITENS:
        if i["caminho"] == c and i["lamina"] != "caminho":
            fora.setdefault(i["lamina"], []).append(i)
        elif c in i["tambem_caminhos"]:
            fora.setdefault("caminho" if i["lamina"] == "caminho" else i["lamina"], []).append(i)
    return fora


def onde_mora(i):
    """Onde está o texto completo do item (para o cartão curto), já com a preposição."""
    if i["lamina"] == "caminho":
        return f"no assunto {NOME_CAMINHO[i['caminho']]}"
    return f"na área {LAMINAS[i['lamina']]}"


# O botão de cada cartão diz "Abrir a página oficial". Três hospitais de Piracicaba/Limeira só têm o boletim da região
# (um PDF único): o botão avisa, para ela não achar que é a página do hospital.
ROTULO_LINK_PADRAO = "Abrir a página oficial"
ROTULO_LINK = {id_: "Abrir o boletim da região (PDF)"
               for id_ in ("santa_casa_piracicaba", "fornecedores_cana", "santa_casa_limeira")}


def rotulo_do_link(i):
    return ROTULO_LINK.get(i["id"], ROTULO_LINK_PADRAO)


# Palavras do sistema de saúde que aparecem nos cartões, em linguagem do dia a dia (uma casa só; a página mostra num quadro).
# Nada aqui é regra nova: repete o que os cartões já dizem.
GLOSSARIO = [
    ("UBS e USF", "a unidade de saúde do seu bairro. É por ela que o cuidado começa e é ela que pede exames e vagas."),
    ("Regulação (CROSS)", "a central do SUS que organiza as vagas em consultas e hospitais especializados. Quem pede a vaga "
                          "é a equipe da unidade de saúde; você pode acompanhar o pedido."),
    ("Rede oncológica", "o conjunto de serviços que cuidam do câncer, da unidade de saúde ao tratamento e ao acompanhamento."),
    ("UNACON e CACON", "hospitais que o Ministério da Saúde habilitou para tratar câncer pelo SUS. Não são porta de entrada: "
                       "chega-se a eles pela regulação."),
    ("RRAS e DRS", "as regiões de saúde do Estado. Rio Claro faz parte da " + REGIAO + "."),
    ("Mastologia", "a especialidade médica que cuida das mamas."),
    ("Biópsia", "a retirada de uma pequena amostra para análise. É ela que confirma ou afasta o diagnóstico."),
    ("TFD", "Tratamento Fora do Domicílio: apoio do SUS para viajar quando o tratamento não existe na sua cidade."),
]


def itens_da_etapa(e):
    if e == "violencia":
        return [i for i in ITENS if i["caminho"] == "ajuda"]
    _, _, _, _, ids = next(x for x in ETAPAS if x[0] == e)
    return [POR_ID[i] for i in ids]


def saudacao():
    return Resposta(
        fala=f"Você está em **{CIDADE}**. O que você precisa? Escolha uma opção e eu mostro o caminho na rede de "
             "saúde, com as páginas oficiais.",
        expressao="acolhedora",
        botoes=[(r, caminho(c)) for c, r, _, _ in CAMINHOS]
        + [("Hospitais no Estado", lamina("hospitais")), ("Consultar itinerário das Carretas", lamina("carretas")),
           ("Rio Claro: o que tem aqui", lamina("rio_claro")), ("Barretos: Hospital de Amor", lamina("barretos")),
           ("De onde vêm estas informações?", SOBRE)],
        destino={"aba": LAMINAS["caminho"]},
    )


def responder_ajuda():
    return Resposta(
        fala="**Em que ponto você está?** " + next(x for x in CAMINHOS if x[0] == "ajuda")[3],
        expressao="acolhedora",
        botoes=[(r, etapa(e)) for e, r, _, _, _ in ETAPAS],
        destino={"aba": LAMINAS["caminho"], "caminho": "ajuda"},
    )


def responder_etapa(e):
    _, rotulo, fala, portas, _ = next(x for x in ETAPAS if x[0] == e)
    lista = itens_da_etapa(e)
    texto = f"**{rotulo}.** {fala}\n\n" + "\n".join(f"- **{i['titulo']}**: {i['resumo']}." for i in lista)
    return Resposta(
        fala=texto,
        expressao="acolhedora" if e in ("violencia", "diagnostico_cancer") else "explicando",
        botoes=[(f"Ver: {NOME_CAMINHO[c]}", caminho(c)) for c in portas]
        + ([("Consultar itinerário das Carretas", lamina("carretas"))] if e == "nao_fiz" else [])
        + [(i["titulo"], item(i["id"])) for i in lista]
        + [("Outro ponto do caminho", caminho("ajuda"))],
        destino={"aba": LAMINAS["caminho"], "caminho": "ajuda", "etapa": e},
        numeros=[f"{i['titulo']}: {i['fonte']}" for i in lista],
    )


def responder_caminho(c):
    if c == "ajuda":
        return responder_ajuda()
    _, rotulo, _, abertura = next(x for x in CAMINHOS if x[0] == c)
    lista = itens(caminho=c, lamina="caminho")
    fala = f"**{rotulo}.** {abertura}"
    if c == "tratamento":
        fala += "\n\n**O caminho na rede:** " + " → ".join(p for p, _, _ in FLUXO_REDE) + "."
    fala += "\n\n" + "\n".join(f"- **{i['titulo']}** · {i['onde']}: {i['resumo']}." for i in lista)
    botoes = [(i["titulo"], item(i["id"])) for i in lista]
    partes = []
    for lam, fora in nas_laminas(c).items():
        if lam != "caminho" and len(fora) > MAX_APONTADOS:
            partes.append(f"{len(fora)} itens na área {LAMINAS[lam]}")
            botoes.append((f"Ver a área {LAMINAS[lam]}", lamina(lam)))
        else:
            partes += [f"{i['titulo']} ({onde_mora(i)})" for i in fora]
            botoes += [(i["titulo"], item(i["id"])) for i in fora]
    if partes:
        fala += "\n\nTambém serve a este assunto: " + "; ".join(partes) + "."
    if c == "mama":
        fala += "\n\n" + frase_carretas()
        botoes.append(("Consultar itinerário das Carretas", lamina("carretas")))
    return Resposta(
        fala=fala,
        expressao="explicando",
        botoes=botoes + _proximo(c),
        destino={"aba": LAMINAS["caminho"], "caminho": c},
        numeros=[f"{i['titulo']}: {i['fonte']}" for i in lista],
    )


def _o_que_fazer(i):
    """Cartão de um câncer da porta Outros cânceres: além de explicar, leva ao que a pessoa doente precisa fazer
    (agendar, diagnóstico confirmado, como chegar ao hospital pela regulação, direitos). Não depende de link externo."""
    if i["caminho"] == "outros" and i["cancer"]:
        return [("Em Rio Claro: agendar consulta (Cadu)", item("rc_cadu_agendamento")),
                ("Recebi o diagnóstico: o que fazer", etapa("diagnostico_cancer")),
                ("Como se chega a um hospital de referência", item("como_chegar_cross")),
                ("Meus direitos", caminho("direitos"))]
    return []


def _voltar(i):
    if i["grupo"]:
        return [(f"Voltar a {i['grupo']}", grupo(i["lamina"], i["grupo"]))]
    if i["caminho"] == "ajuda":
        return [("Voltar a Preciso de ajuda", etapa("violencia"))]
    if i["caminho"]:
        return [(f"Voltar a {NOME_CAMINHO[i['caminho']]}", caminho(i["caminho"]))]
    return [(f"Voltar a {LAMINAS[i['lamina']]}", lamina(i["lamina"]))]


def responder_item(id):
    i = POR_ID[id]
    partes = [f"**{i['titulo']}** · {i['onde']}"]
    for rotulo, chave in (("Para quem", "para_quem"), ("Como funciona", "como"), ("Onde e contato", "contato"),
                          ("O que levar", "levar")):
        if chave == "como" and i["topicos"]:   # os tópicos (o que é, sinais, exames...) vêm antes do caminho no SUS
            partes += [f"**{rotulo_t}:** {texto_t}" for rotulo_t, texto_t in i["topicos"]]
            rotulo = "Como buscar atendimento pelo SUS"
        if i[chave]:
            partes.append(f"**{rotulo}:** {i[chave]}")
    if i["cuidado"]:
        partes.append(f"**Atenção:** {i['cuidado']}")
    if i["confirmar"]:
        partes.append(f"**A confirmar:** {i['confirmar']}")
    partes.append(f"[{rotulo_do_link(i)}]({i['link']})")
    if i["mais_links"]:
        partes.append("**Outras páginas que ajudam:** " + " · ".join(f"[{r}]({u})" for r, u in i["mais_links"]))
    partes.append(AVISO)
    return Resposta(
        fala="\n\n".join(partes),
        expressao="cautelosa" if i["confirmar"] else ("acolhedora" if i["caminho"] == "ajuda" else "explicando"),
        botoes=_voltar(i) + _o_que_fazer(i) + _proximo(i["caminho"]),
        destino={"aba": LAMINAS[i["lamina"]], "caminho": i["caminho"], "grupo": i["grupo"], "item": id,
                 "etapa": "violencia" if i["caminho"] == "ajuda" and i["lamina"] == "caminho" else None},
        numeros=[f"Fonte: {i['fonte']}", f"Página: {i['link']}", f"Conferido em {i.get('conferido', CONFERIDO)}"],
    )


INTRO_LAMINA = {
    "barretos": ("**Barretos** reúne, no **Hospital de Amor**, hospitais de referência, prevenção, carretas, ensino e "
                 "pesquisa em câncer. Aqui estão as informações e os links oficiais. Escolha um tema."),
    "hospitais": ("Estes são **hospitais que tratam câncer pelo SUS no Estado de São Paulo**, por região. Eles não "
                  "são porta de entrada: chega-se a eles pela regulação (CROSS), a partir da unidade de saúde. Para "
                  "quem mora em Rio Claro, as referências são Rio Claro e Piracicaba, e o HC da Unicamp também atende "
                  "a região. Escolha uma região."),
    "carretas": ("**Carretas da mamografia**: o exame é gratuito. Consulte os canais oficiais para ver as cidades, "
                 "datas e endereços atualizados."),
}


def responder_lamina(id):
    if id in GRUPOS:
        fala = INTRO_LAMINA[id]
        if id == "carretas":
            fala += " " + frase_carretas()
        contagem = {g: sum(len(x) for x in do_grupo(id, g)) for g in GRUPOS[id]}
        fala += "\n\n" + "\n".join(f"- **{g}**: {n} {'item' if n == 1 else 'itens'}"
                                     for g, n in contagem.items())
        botoes = [(g, grupo(id, g)) for g in GRUPOS[id]]
        numeros = []
    else:  # Rio Claro
        lista = itens(lamina=id)
        fala = (f"**Rio Claro** é a cidade do trabalho do Escudo. Aqui estão as portas da própria cidade. Rio Claro "
                f"faz parte da **{REGIAO}**: as referências de câncer da região ficam em Rio Claro e em Piracicaba, "
                "e o HC da Unicamp também atende a região (área Hospitais no Estado).")
        fala += "\n\n" + "\n".join(f"- **{i['titulo']}**: {i['resumo']}." for i in lista)
        botoes = [(i["titulo"], item(i["id"])) for i in lista] + [
            ("Hospitais da região de Rio Claro", grupo("hospitais", "Rio Claro e Piracicaba (RRAS 14)"))]
        numeros = [f"{i['titulo']}: {i['fonte']}" for i in lista]
    return Resposta(fala=fala, expressao="explicando", botoes=botoes, destino={"aba": LAMINAS[id]},
                    numeros=numeros)


def responder_grupo(lam, g):
    casa, visitas = do_grupo(lam, g)
    fala = f"**{g}.**\n\n" + "\n".join(f"- **{i['titulo']}** · {i['onde']}: {i['resumo']}."
                                         for i in casa + visitas)
    return Resposta(
        fala=fala,
        expressao="explicando",
        botoes=[(i["titulo"], item(i["id"])) for i in casa + visitas]
        + [(f"Voltar a {LAMINAS[lam]}", lamina(lam))],
        destino={"aba": LAMINAS[lam], "grupo": g},
        numeros=[f"{i['titulo']}: {i['fonte']}" for i in casa + visitas],
    )


def responder_sobre():
    pendentes = [i["titulo"] for i in ITENS if i["confirmar"]]
    return Resposta(
        fala=(f"A pesquisa-base foi reunida em {CONFERIDO}, e alguns itens receberam atualização posterior. "
              "Cada cartão informa sua própria data registrada e traz o link da fonte oficial: Secretaria da Saúde "
              "e Secretaria da Mulher do Estado de SP, FOSP, INCA, Ministério da Saúde e das Mulheres, Defensoria "
              "Pública, Poupatempo, Fundação Municipal de Saúde e Prefeitura de Rio Claro, prefeituras de outras "
              "cidades e os próprios hospitais. "
              f"{len(pendentes)} de {len(ITENS)} itens ainda pedem confirmação na própria página: estão marcados. "
              "Isto é um guia de onde procurar, não orientação médica nem garantia de vaga."),
        expressao="pensativa",
        botoes=[("Preciso de ajuda", caminho("ajuda"))],
        destino={"aba": LAMINAS["sobre"]},
        numeros=[f"A confirmar: {t}" for t in pendentes],
    )


def responder(acao):
    """Executa um botão da Lia no apoio. Toda resposta termina com [Começar de novo]."""
    tipo = acao.get("tipo")
    if tipo == "apoio_caminho" and acao.get("id") in NOME_CAMINHO:
        r = responder_caminho(acao["id"])
    elif tipo == "apoio_etapa" and acao.get("id") in NOME_ETAPA:
        r = responder_etapa(acao["id"])
    elif tipo == "apoio_item" and acao.get("id") in POR_ID:
        r = responder_item(acao["id"])
    elif tipo == "apoio_lamina" and acao.get("id") in ("hospitais", "carretas", "rio_claro", "barretos"):
        r = responder_lamina(acao["id"])
    elif tipo == "apoio_grupo" and acao.get("id") in GRUPOS.get(acao.get("lamina"), ()):
        r = responder_grupo(acao["lamina"], acao["id"])
    elif tipo == "apoio_sobre":
        r = responder_sobre()
    else:
        return saudacao()
    r.botoes = r.botoes + [("Começar de novo", INICIO)]
    return r
