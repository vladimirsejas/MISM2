from datetime import date

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
    ("diagnostico", "Diagnóstico", "exame alterado, biópsia, especialista",
     "Quando um exame vem alterado, começa a investigação: exames complementares, biópsia e encaminhamento ao "
     "especialista. Alteração não quer dizer câncer."),
    ("regulacao", "Regulação", "já fui encaminhada, e agora?",
     "Depois do encaminhamento, a vaga é organizada pela regulação do Estado. Dá para acompanhar a fila e pedir "
     "ajuda se algo não andar."),
    ("tratamento", "Tratamento", "onde e como se trata pelo SUS",
     "Com o diagnóstico confirmado, o tratamento pelo SUS tem prazo em lei e acontece nos hospitais habilitados."),
    ("rede", "Rede oncológica", "do posto de saúde ao tratamento",
     "A rede oncológica do Estado liga a unidade de saúde, o diagnóstico, a regulação, o especialista, o "
     "tratamento e o acompanhamento."),
    ("direitos", "Direitos e acesso", "benefícios, transporte e como o SUS funciona",
     "Quem recebe um diagnóstico de câncer tem direitos garantidos por lei e um caminho no SUS. Aqui, em "
     "linguagem simples."),
    ("ajuda", "Preciso de ajuda", "em que ponto você está?",
     "Me conta em que ponto você está, que eu mostro o próximo passo na rede de saúde."),
]
NOME_CAMINHO = {c: r for c, r, _, _ in CAMINHOS}
# O próximo passo de cada porta (a jornada da mulher na rede).
PROXIMO = {"mama": "diagnostico", "colo": "diagnostico", "diagnostico": "regulacao", "regulacao": "tratamento",
           "tratamento": "direitos"}
# A rede oncológica em passos (porta Rede oncológica): (passo, o que é, porta)
FLUXO_REDE = [
    ("Unidade de saúde", "consulta, preventivo e pedido de mamografia", "mama"),
    ("Diagnóstico", "exames complementares e biópsia", "diagnostico"),
    ("Regulação", "a vaga no especialista, pela CROSS", "regulacao"),
    ("Especialista", "consulta no hospital de referência", "rede"),
    ("Tratamento", "cirurgia, quimioterapia, radioterapia", "tratamento"),
    ("Acompanhamento", "direitos, transporte e apoio", "direitos"),
]


def _item(id, caminho, lamina, onde, titulo, resumo, fonte, link, para_quem=None, como=None, levar=None,
          contato=None, confirmar=None, cuidado=None, grupo=None, tambem=(), tambem_caminhos=(), conferido=None):
    """caminho=None: item que não é passo da jornada da mulher (ensino,
    pesquisa, a região no Estado) -- mora só na lâmina dele. grupo: o
    tema (Barretos) ou a região (Hospitais no Estado) do item na lâmina.
    tambem: [(lâmina, grupo)] onde o item também aparece, em cartão
    curto, sem repetir o texto (a casa dele continua sendo uma só).
    tambem_caminhos: outras portas onde o item aparece em cartão curto."""
    return {"id": id, "caminho": caminho, "lamina": lamina, "onde": onde, "titulo": titulo, "resumo": resumo,
            "para_quem": para_quem, "como": como, "levar": levar, "contato": contato, "fonte": fonte,
            "link": link, "confirmar": confirmar, "cuidado": cuidado, "grupo": grupo, "tambem": list(tambem),
            "conferido": conferido or CONFERIDO,
            "tambem_caminhos": list(tambem_caminhos)}


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
          "de 25 a 64 anos, na unidade de saúde; o teste de DNA-HPV está substituindo o Papanicolau aos poucos",
          "Ministério da Saúde",
          "https://www.gov.br/saude/pt-br/assuntos/noticias/2025/agosto/ministerio-da-saude-oferta-tecnologia-"
          "inovadora-100-nacional-para-detectar-cancer-do-colo-do-utero-no-sus",
          para_quem="Mulheres de 25 a 64 anos.",
          como="Na unidade de saúde do bairro (UBS ou USF). O SUS está trocando, aos poucos, o Papanicolau pelo teste "
               "de DNA-HPV, que é mais sensível; São Paulo está entre os estados que já têm o teste. Com o teste de "
               "DNA-HPV negativo, o próximo exame é em 5 anos.",
          confirmar="A troca é gradual: pergunte na sua unidade qual exame ela faz hoje."),
    _item("vacina_hpv", "colo", "caminho", "SUS (todo o Brasil)",
          "Vacina contra o HPV",
          "dose única de 9 a 14 anos; protege contra o vírus que causa o câncer do colo do útero",
          "Ministério da Saúde",
          "https://www.gov.br/saude/pt-br/assuntos/noticias/2025/dezembro/ministerio-da-saude-amplia-prazo-de-"
          "resgate-vacinal-contra-hpv-para-jovens-de-15-a-19-anos-ate-2026",
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
    _item("lei_30_dias", "diagnostico", "caminho", "SUS (todo o Brasil)",
          "Direito: exames de diagnóstico em até 30 dias",
          "com suspeita de câncer, os exames que confirmam o diagnóstico devem sair em até 30 dias",
          "Lei federal 13.896/2019 (Câmara dos Deputados)",
          "https://www2.camara.leg.br/legin/fed/lei/2019/lei-13896-30-outubro-2019-789326-norma-pl.html",
          para_quem="Pessoas com suspeita de câncer atendidas no SUS.",
          como="A lei garante que os exames necessários para confirmar o diagnóstico sejam feitos em até 30 dias, "
               "contados do pedido médico.",
          tambem_caminhos=["direitos"]),
    _item("mater_ribeirao", "diagnostico", "caminho", "Ribeirão Preto",
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
               "quimioterapia ou radioterapia). Somada à lei dos 30 dias, da suspeita ao início do tratamento são no "
               "máximo 90 dias.",
          tambem_caminhos=["direitos"]),
    _item("rede_oncologica", "rede", "caminho", "Estado de SP",
          "Rede de Atenção Oncológica do Estado de São Paulo",
          "a lista oficial dos hospitais habilitados para tratar câncer pelo SUS, por região",
          "Fundação Oncocentro de São Paulo (FOSP)",
          "https://fosp.saude.sp.gov.br/fosp/diretoria-adjunta-de-informacao-e-epidemiologia/rede-de-atencao-"
          "oncologica-do-estado-de-sao-paulo/",
          como="Os hospitais são habilitados como CACON (alta complexidade) ou UNACON, com ou sem radioterapia e "
               "hematologia. O acesso é pela regulação: a unidade de saúde ou o especialista encaminha. A lista "
               "serve para saber quais são as referências da sua região."),

    # ---------------- ACOMPANHAR ----------------
    _item("lista_regulacao", "regulacao", "caminho", "Estado de SP",
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
          "a partir de 35 anos, sem mamografia nos últimos 12 meses; itinerário no Poupatempo",
          "Poupatempo / Secretaria de Estado da Saúde de SP",
          "https://www.poupatempo.sp.gov.br/carta/B7ED6C20-6D1B-481B-8693-35AD62D16E42",
          para_quem="Mulheres a partir de 35 anos que não fizeram mamografia nos últimos 12 meses.",
          levar="De 50 a 74 anos: RG e cartão SUS. De 35 a 49 e acima de 74 anos: também o pedido médico do SUS.",
          como="Consultar o itinerário no Poupatempo (site ou aplicativo). Atendimento de segunda a sexta, das 8h às "
               "17h, e aos sábados, das 8h às 12h, com senhas limitadas. Gratuito.",
          confirmar="O itinerário muda todo mês: consulte antes de ir.",
          grupo="Carretas da Mamografia do Estado"),

    # ---------------- ENCONTRAR REFERÊNCIA ----------------
    _item("santa_casa_piracicaba", "rede", "hospitais", "Piracicaba (região de Rio Claro)",
          "Santa Casa de Piracicaba",
          "UNACON com radioterapia, na mesma região de saúde de Rio Claro",
          "FOSP – boletim da RRAS 14 (DRS Piracicaba)",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS14.pdf",
          como="Hospital habilitado como UNACON com serviço de radioterapia. Faz parte da RRAS 14, a mesma de Rio "
               "Claro. O acesso é pela regulação do SUS.",
          grupo="Rio Claro e Piracicaba (RRAS 14)"),
    _item("fornecedores_cana", "rede", "hospitais", "Piracicaba (região de Rio Claro)",
          "Hospital dos Fornecedores de Cana de Piracicaba",
          "UNACON com radioterapia e hematologia, na mesma região de saúde de Rio Claro",
          "FOSP – boletim da RRAS 14 (DRS Piracicaba)",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS14.pdf",
          como="Hospital habilitado como UNACON com radioterapia e hematologia. Faz parte da RRAS 14, a mesma de Rio "
               "Claro. O acesso é pela regulação do SUS.",
          grupo="Rio Claro e Piracicaba (RRAS 14)"),
    _item("santa_casa_limeira", "rede", "hospitais", "Limeira (região de Rio Claro)",
          "Santa Casa de Limeira",
          "citada como UNACON com radioterapia na região de Rio Claro (a confirmar)",
          "FOSP – boletim da RRAS 14 (DRS Piracicaba)",
          "https://fosp.saude.sp.gov.br/wp-content/uploads/Boletim-RRAS14.pdf",
          como="O acesso é pela regulação do SUS.",
          confirmar="Não consegui abrir o boletim da FOSP inteiro para confirmar a habilitação de Limeira.",
          grupo="Rio Claro e Piracicaba (RRAS 14)"),
    _item("caism_unicamp", "rede", "hospitais", "Campinas",
          "CAISM Unicamp – Hospital da Mulher",
          "maior hospital de saúde da mulher do interior; câncer ginecológico e de mama; só SUS",
          "CAISM – Unicamp",
          "https://www2.caism.unicamp.br/",
          como="Atende só pelo SUS. Tem ambulatórios de oncologia ginecológica (vulva, vagina, colo e corpo do útero, "
               "ovário) e de mastologia, referência para Campinas e região. As consultas são agendadas pelas "
               "unidades básicas de saúde e pela rede pública.",
          cuidado="O acesso é por encaminhamento da rede pública; para quem mora em Rio Claro, o caminho começa "
                  "na referência da própria região.",
          grupo="Campinas",
          tambem_caminhos=["mama", "colo"]),
    _item("hospital_base_rio_preto", "rede", "hospitais", "São José do Rio Preto",
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
    _item("ribeirao_agendamento", "mama", "caminho", "Ribeirão Preto",
          "Mamografia agendada pelo site da Prefeitura de Ribeirão Preto",
          "moradoras de 50 a 69 anos sem mamografia há 2 anos ou mais agendam pela internet",
          "Prefeitura de Ribeirão Preto",
          "https://www.ribeiraopreto.sp.gov.br/portal/sassom/prevencao-cancer-mama",
          para_quem="Moradoras de Ribeirão Preto de 50 a 69 anos sem mamografia há 2 anos ou mais.",
          como="Agendar no site da Prefeitura; quem não conseguir pode pedir na unidade de saúde mais próxima."),
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
          "https://www.agenciasp.sp.gov.br/sp-mulher-segura-conheca-o-aplicativo-que-permite-denunciar-violencia-"
          "domestica-e-acionar-botao-do-panico-contra-agressores/",
          como="Permite registrar boletim de ocorrência, pedir medida protetiva de urgência e, para quem já tem "
               "medida protetiva, acionar o botão do pânico, que envia a localização em tempo real. Android e iOS; "
               "entra com a conta gov.br."),
    _item("delegacia_eletronica", "ajuda", "caminho", "Estado de SP",
          "Delegacia Eletrônica – violência doméstica contra a mulher",
          "registrar ocorrência pela internet, 24 horas, e pedir medida protetiva",
          "Polícia Civil do Estado de SP",
          "https://www.delegaciaeletronica.policiacivil.sp.gov.br/",
          como="Em \"Comunicar Ocorrência\", escolher \"Violência Doméstica Contra Mulher\". Dá para anexar fotos e "
               "mensagens e pedir medida protetiva de urgência no mesmo formulário."),

    # ================ LÂMINA RIO CLARO (a cidade do trabalho) ================
    _item("rc_cadu_agendamento", "mama", "rio_claro", "Rio Claro",
          "Agendamento de consulta e exames pelo Cadu",
          "telefone e WhatsApp gratuitos para agendar consulta e solicitar mamografia ou Papanicolau",
          "Fundação Municipal de Saúde de Rio Claro (publicação de 07/10/2026)",
          "https://rioclaro.sp.gov.br/fundacao-de-saude/nova-central-para-agendamento-de-consultas-comeca-a-operar-na-2a-feira-em-rc/",
          para_quem="Moradoras e moradores que precisam agendar consulta na rede municipal; para mamografia e Papanicolau, é necessário passar por profissional de saúde.",
          como="Ligue ou envie mensagem pelo WhatsApp para 0800 019 0505. A publicação municipal de 07/10/2026 informa que consultas para solicitar mamografia e Papanicolau podem ser agendadas pelo Cadu ou diretamente na unidade de saúde. O exame depende de solicitação de profissional.",
          contato="Cadu: 0800 019 0505 (telefone/WhatsApp).",
          confirmar="Canal confirmado em publicação municipal de 07/10/2026; confirme o funcionamento e as regras atuais antes de depender do serviço.",
          tambem_caminhos=["colo"],
          conferido="09/10/2026"),
    _item("rc_unidades", "colo", "rio_claro", "Rio Claro",
          "Unidades de Saúde da Família (USF) e UBS",
          "a porta de entrada: preventivo do colo do útero, exame das mamas e pré-natal",
          "Fundação Municipal de Saúde de Rio Claro",
          "https://www.saude-rioclaro.org.br/enderecos.htm",
          para_quem="Moradoras de Rio Claro.",
          como="A Prefeitura informa 17 Unidades de Saúde da Família e 4 UBS, das 7h às 17h. A consulta é marcada "
               "na própria unidade, que é onde se faz o preventivo e se pede a mamografia. Algumas equipes têm "
               "ginecologista.",
          confirmar="O número de unidades e o horário vêm de páginas antigas da Prefeitura: confira a lista de "
                    "endereços.",
          tambem_caminhos=["mama"]),
    _item("rc_central_vagas", "mama", "rio_claro", "Rio Claro",
          "Central de Vagas da Fundação Municipal de Saúde (mamografia com pedido médico)",
          "com o pedido médico em mãos, a mamografia é agendada na Central de Vagas",
          "Fundação Municipal de Saúde de Rio Claro (informativo)",
          "https://www.saude-rioclaro.org.br/informativos/Rio%20Claro%20faz%20agendamento%20de%20exame%20de%20mama.htm",
          levar="O pedido médico.",
          contato="Rua 10, esquina com a Via da Saudade. Telefones 3524-1463 e 3534-0026. Segunda a sexta, das 7h "
                  "às 16h.",
          confirmar="É um informativo antigo da Fundação: confirme endereço, telefones e se o agendamento ainda é "
                    "feito ali."),
    _item("rc_carreta_hospital_de_amor", "mama", "rio_claro", "Rio Claro",
          "Carreta do Hospital de Amor em Rio Claro",
          "em fevereiro de 2025 a carreta veio a Rio Claro: cerca de 300 mamografias e Papanicolau, com agendamento",
          "Prefeitura de Rio Claro",
          "https://rioclaro.sp.gov.br/fundacao-de-saude/rc-faz-300-exames-de-papanicolau-e-mamografia-em-carreta-"
          "do-hospital-do-amor/",
          como="Nos dias 17, 18 e 20 de fevereiro de 2025 a carreta ficou no Centro Cultural, das 8h às 16h, e fez "
               "cerca de 300 exames gratuitos. Foram 180 vagas de mamografia para mulheres de 40 a 69 anos e 120 de "
               "Papanicolau para 25 a 65 anos, com agendamento prévio nas Unidades de Saúde da Família.",
          confirmar="Foi uma ação com data marcada, não um serviço fixo: pergunte na sua USF se haverá nova vinda.",
          tambem=[("carretas", "Unidades móveis do Hospital de Amor")]),
    _item("rc_santa_casa", "tratamento", "rio_claro", "Rio Claro",
          "Santa Casa de Rio Claro – oncologia (UNACON) e Centro Oncológico Santa Ágata",
          "hospital habilitado para tratar câncer pelo SUS na própria cidade",
          "FOSP (boletim da RRAS 14) e Santa Casa de Rio Claro",
          "https://www.santacasaderioclaro.com.br/",
          como="Habilitada como UNACON. O Centro Oncológico Santa Ágata tem 24 poltronas de quimioterapia, 6 leitos e "
               "11 consultórios. É referência em câncer de cabeça e pescoço para os 26 municípios da DRS X. O acesso "
               "pelo SUS é pela regulação (encaminhamento da unidade ou do especialista).",
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
    _item("ha_quem_e", "rede", "barretos", "Barretos",
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
          "carretas que percorrem o país em ações com as prefeituras; em fevereiro de 2025 uma esteve em Rio Claro",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/prevencao/",
          para_quem="Mulheres de 40 a 69 anos.",
          como="As unidades móveis chegam por parceria com a prefeitura. Para agendar, procure a unidade de saúde "
               "mais próxima.",
          levar="Cópia do RG, CPF, cartão SUS e comprovante de residência.",
          grupo="Carretas e unidades móveis",
          tambem=[("carretas", "Unidades móveis do Hospital de Amor")]),
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
    _item("ha_unidades", "rede", "barretos", "Barretos",
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
          "https://hospitaldeamor.com.br/site/barretos-possui-o-maior-indice-de-deteccao-precoce-do-cancer-de-colo-"
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

    # ---------------- DIAGNÓSTICO: depois que aparece uma alteração ----------------
    _item("mamografia_alterada", "diagnostico", "caminho", "SUS (todo o Brasil)",
          "Mamografia alterada: o que quer dizer o BI-RADS",
          "BI-RADS 0 pede exame complementar; 3, novo exame em 6 meses; 4 e 5, biópsia",
          "Ministério da Saúde – Linha de cuidado do câncer de mama",
          "https://linhasdecuidado.saude.gov.br/portal/cancer-de-mama/unidade-de-atencao-primaria/rastreamento-"
          "diagnostico/risco-cancer-conduta-categoria-BI-RADS/",
          como="O laudo da mamografia traz uma categoria BI-RADS. 0: o exame ficou incompleto e precisa de "
               "complemento (outras incidências ou ultrassom). 3: achado provavelmente benigno, com novo exame em 6 "
               "meses. 4: achado suspeito, e a conduta é a biópsia. 5: muito suspeito, também biópsia. Quando a "
               "alteração não se esclarece, a mulher é encaminhada ao especialista (mastologista).",
          cuidado="Quem explica o seu resultado é a equipe que pediu o exame; leve o laudo à unidade de saúde."),
    _item("preventivo_alterado", "diagnostico", "caminho", "SUS (todo o Brasil)",
          "Preventivo alterado: colposcopia e biópsia",
          "resultado alterado pede repetição, colposcopia ou biópsia; muitas alterações não são câncer",
          "Ministério da Saúde – diretriz de rastreamento do câncer do colo do útero",
          "https://www.gov.br/saude/pt-br/assuntos/pcdt/r/rastreamento-cancer-do-colo-do-utero",
          como="Conforme o resultado, repete-se o exame ou a mulher vai à colposcopia, exame que olha o colo do útero "
               "com aumento; se houver uma área suspeita, faz-se uma biópsia. Com o teste de HPV, quem tem os tipos "
               "16 ou 18 vai direto à colposcopia. Muitas lesões são tratadas no próprio ambulatório.",
          cuidado="Quem explica o seu resultado é a equipe que pediu o exame."),

    # ---------------- REGULAÇÃO: quando o nome não aparece ----------------
    _item("nao_achei_nome", "regulacao", "caminho", "SUS (todo o Brasil)",
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
    _item("como_chegar_cross", "regulacao", "caminho", "Estado de SP",
          "Como se chega a um hospital de referência pelo SUS",
          "os hospitais de câncer não são porta de entrada: a unidade de saúde pede a vaga pela regulação (CROSS)",
          "ICESP e HC Unicamp (orientações aos pacientes)",
          "https://icesp.org.br/como-ser-atendido/",
          como="Com suspeita ou diagnóstico de câncer, procure a unidade de saúde (UBS) mais próxima de casa. O médico "
               "do SUS insere o caso na Central de Regulação de Oferta de Serviços de Saúde (CROSS/SIRESP), que "
               "encaminha a paciente a um centro de oncologia perto de onde ela mora, seguindo protocolos clínicos. "
               "É a Rede Hebe Camargo de Combate ao Câncer, do Estado.",
          tambem=[("hospitais", "Como chegar e listas oficiais")],
          tambem_caminhos=["direitos", "rede"]),
    _item("fosp_hospitais_sus", "rede", "caminho", "Estado de SP",
          "Lista oficial: hospitais do SUS com atendimento em câncer no Estado",
          "a lista da FOSP com todos os hospitais habilitados (CACON e UNACON) do Estado de São Paulo",
          "Fundação Oncocentro de São Paulo (FOSP) – Espaço do Paciente",
          "https://fosp.saude.sp.gov.br/fosp/espaco-paciente/hospitais-do-sus-habilitadas-para-atendimento-em-"
          "cancer-no-estado-de-sao-paulo/",
          como="A lista completa e atualizada pelo Estado. Os hospitais desta lâmina são os que a pesquisa encontrou "
               "com fonte; a lista da FOSP tem todos.",
          tambem=[("hospitais", "Como chegar e listas oficiais")]),
    _item("inca_onde_tratar", "rede", "caminho", "SUS (todo o Brasil)",
          "Onde tratar pelo SUS (INCA)",
          "a página do Instituto Nacional de Câncer com os hospitais habilitados de cada estado",
          "Instituto Nacional de Câncer (INCA)",
          "https://www.gov.br/inca/pt-br/assuntos/cancer/tratamento/onde-tratar-pelo-sus",
          como="UNACON trata os cânceres mais comuns; CACON trata todos os tipos. Os dois fazem do diagnóstico ao "
               "cuidado paliativo.",
          tambem=[("hospitais", "Como chegar e listas oficiais")]),

    # ================ LÂMINA HOSPITAIS NO ESTADO (por região) ================
    _item("hc_unicamp", "rede", "hospitais", "Campinas",
          "HC da Unicamp – Oncologia",
          "referência em câncer para as regiões de Campinas, Piracicaba (a de Rio Claro) e São João da Boa Vista",
          "HC Unicamp e Governo do Estado de SP",
          "https://www.hc.unicamp.br/especialidades/",
          como="Atende pacientes com câncer das DRS de Campinas, Piracicaba e São João da Boa Vista. Casos novos "
               "chegam pela Central Reguladora de Vagas da DRS VII; com diagnóstico de câncer, o médico do SUS "
               "insere o caso na CROSS. Tem também enfermagem, nutrição, serviço social, psicologia e odontologia.",
          contato="Oncologia Clínica: (19) 3521-7496 e (19) 3521-7363.",
          grupo="Campinas"),
    _item("icesp", "rede", "hospitais", "São Paulo (capital)",
          "ICESP – Instituto do Câncer do Estado de São Paulo",
          "hospital público estadual só de câncer; atende pacientes encaminhados pela regulação",
          "ICESP",
          "https://icesp.org.br/como-ser-atendido/",
          como="Atende só pacientes encaminhados pela rede estadual (UBS, AMEs e hospitais gerais), pela Central de "
               "Regulação (CROSS), priorizando as regiões que têm o ICESP como referência.",
          contato="(11) 3893-2000.",
          grupo="Capital e Grande São Paulo"),
    _item("hospital_da_mulher_sp", "rede", "hospitais", "São Paulo (capital)",
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
    _item("ibcc", "rede", "hospitais", "São Paulo (capital)",
          "IBCC Oncologia – Instituto Brasileiro de Controle do Câncer",
          "pioneiro no controle do câncer de mama e ginecológico em São Paulo; atende SUS e convênios",
          "IBCC",
          "https://www.ibcc.org.br/",
          como="Centro de oncologia de alta complexidade fundado em 1968, com oncologia clínica, cirurgia oncológica, "
               "mastologia e exames como mamografia e biópsia. Atende pacientes do SUS e de convênios.",
          contato="Av. Alcântara Machado, 2576 – Mooca. (11) 3474-4222.",
          confirmar="Pelo SUS, o acesso é pela regulação: confirme com a unidade de saúde.",
          grupo="Capital e Grande São Paulo"),
    _item("hc_ribeirao", "rede", "hospitais", "Ribeirão Preto",
          "HC de Ribeirão Preto (FMRP-USP) – Oncologia Clínica",
          "referência da Rede Hebe Camargo; recebe pacientes encaminhados pela CROSS",
          "Oncologia Clínica – FMRP-USP",
          "https://oncologia.fmrp.usp.br/regulacao-de-pacientes/",
          como="Recebe pacientes com diagnóstico de câncer vindos das unidades básicas, ambulatórios e hospitais "
               "gerais, sempre encaminhados pela Central de Regulação (CROSS). Não há atendimento direto.",
          contato="Av. Bandeirantes, 3900 – HC, 7º andar – Campus USP, Ribeirão Preto.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("cancer_franca", "rede", "hospitais", "Franca",
          "Hospital do Câncer do Grupo Santa Casa de Franca",
          "atende pelo SUS Franca e mais 20 municípios, com radioterapia e quimioterapia",
          "Grupo Santa Casa de Franca",
          "https://www.gruposantacasadefranca.com.br/hospital-do-cancer/",
          como="Hospital de referência regional em câncer, com consultas, radioterapia, quimioterapia e "
               "hormonioterapia pelo SUS para cerca de 750 mil habitantes da região.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("santa_casa_araraquara", "rede", "hospitais", "Araraquara",
          "Hospital do Câncer da Santa Casa de Araraquara",
          "UNACON com quimioterapia, radioterapia e onco-hematologia; referência regional do SUS",
          "Santa Casa de Araraquara",
          "https://santacasaararaquara.com.br/oncologia/",
          como="Habilitada como UNACON pelo Ministério da Saúde. Atende pelo SUS e convênios, com equipe "
               "multiprofissional.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("santa_casa_sao_carlos", "rede", "hospitais", "São Carlos",
          "Santa Casa de São Carlos – Oncologia",
          "UNACON com radioterapia, para cerca de 390 mil habitantes da microrregião",
          "Santa Casa de São Carlos",
          "https://www.santacasasaocarlos.com.br/",
          como="Habilitada como UNACON com radioterapia: diagnóstico e tratamento do câncer pelo SUS.",
          grupo="Barretos, Franca, Ribeirão Preto e Araraquara (RRAS 13)"),
    _item("santa_casa_aracatuba", "rede", "hospitais", "Araçatuba",
          "Santa Casa de Araçatuba – Centro de Tratamento Oncológico",
          "UNACON com radioterapia e hematologia, referência para 40 municípios",
          "Santa Casa de Araçatuba",
          "https://www.santacasadearacatuba.com.br/",
          como="Integra a Rede Hebe Camargo. Referência para o tratamento especializado de quase todos os tipos de "
               "câncer na região.",
          grupo="Rio Preto, Araçatuba e Jales (RRAS 12)"),
    _item("hospital_de_amor_jales", "rede", "hospitais", "Jales",
          "Hospital de Amor Jales",
          "a primeira unidade do Hospital de Amor fora de Barretos, 100% SUS",
          "Hospital de Amor",
          "https://hospitaldeamor.com.br/hospital-de-amor-jales/",
          como="Inaugurado em 2010, atende 100% pelo SUS, com radioterapia de alta precisão e cirurgias oncológicas.",
          grupo="Rio Preto, Araçatuba e Jales (RRAS 12)"),
    _item("amaral_carvalho", "rede", "hospitais", "Jaú",
          "Hospital Amaral Carvalho",
          "referência nacional em câncer e transplante de medula óssea; quase toda a capacidade é para o SUS",
          "Hospital Amaral Carvalho",
          "https://www.amaralcarvalho.org.br/informacoes",
          como="Hospital filantrópico de 1915, com cerca de 320 leitos. Para saber como ser atendida, procure o "
               "Serviço Social do hospital.",
          contato="Rua Dona Silvéria, 150 – Chácara Braz Miraglia, Jaú. (14) 3602-1200.",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("hc_botucatu", "rede", "hospitais", "Botucatu",
          "HC da Faculdade de Medicina de Botucatu (Unesp) – Oncologia",
          "centro de oncologia de referência regional, com quimioterapia e onco-hematologia",
          "HC Botucatu (Unesp)",
          "https://hcfmb.unesp.br/servico-de-oncologia/",
          como="Referência regional: cerca de 17 mil consultas e 18 mil sessões de quimioterapia por ano (2021).",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("bauru_oncologia", "rede", "hospitais", "Bauru",
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
    _item("hc_famema", "rede", "hospitais", "Marília",
          "HC da Famema (Marília) – Oncologia",
          "alta complexidade em câncer, com quimioterapia e radioterapia, para 62 municípios",
          "HC Famema (Governo do Estado de SP)",
          "https://www.hcfamema.sp.gov.br/hcfamema",
          como="Referência de média e alta complexidade para cerca de 1,2 milhão de pessoas do centro-oeste paulista, "
               "com quimioterapia e radioterapia.",
          confirmar="A habilitação mudou em 2026 (de CACON para UNACON com radioterapia, segundo notícia): confira "
                    "na lista da FOSP.",
          grupo="Centro-Oeste: Jaú, Bauru, Botucatu e Marília"),
    _item("prudente_cancer", "rede", "hospitais", "Presidente Prudente",
          "Hospital Regional do Câncer de Presidente Prudente (Hospital de Esperança)",
          "UNACON com hematologia, oncologia pediátrica e radioterapia pelo SUS",
          "Governo Federal (Planalto) – credenciamento de 2021",
          "https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/noticias/2021/07/hospital-de-presidente-prudente-sp-"
          "e-credenciado-para-assistencia-de-alta-complexidade-em-oncologia",
          como="Credenciado em 2021 como UNACON, com 122 leitos para o SUS. Na cidade, a Santa Casa de Presidente "
               "Prudente também é UNACON.",
          confirmar="O nome do hospital mudou: confira na lista da FOSP.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),
    _item("sorocaba_oncologia", "rede", "hospitais", "Sorocaba",
          "Sorocaba: Santa Casa (Hospital do Câncer) e Conjunto Hospitalar",
          "Santa Casa: UNACON com radioterapia; Conjunto Hospitalar: UNACON com hematologia",
          "Prefeitura de Sorocaba (Agência de Notícias)",
          "https://noticias.sorocaba.sp.gov.br/hospital-do-cancer-da-santa-casa-inaugura-consultorio-odontologico/",
          como="A Santa Casa de Sorocaba é UNACON desde 2008 e tem radioterapia com acelerador linear desde 2020, com "
               "equipe multiprofissional.",
          confirmar="A habilitação do Conjunto Hospitalar veio de lista de associação de pacientes: confira na lista "
                    "da FOSP.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),
    _item("pio_xii_sjc", "rede", "hospitais", "São José dos Campos",
          "Hospital Pio XII (São José dos Campos)",
          "UNACON do Vale do Paraíba; mais de 80% dos pacientes são do SUS",
          "Hospital Pio XII",
          "https://www.hpioxii.org.br/o-hospital/",
          como="Referência em oncologia (UNACON) desde 1977 para São José dos Campos e o Vale do Paraíba.",
          grupo="Oeste, Sorocaba, Vale do Paraíba e Litoral"),
    _item("guilherme_alvaro", "rede", "hospitais", "Santos",
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
          "se o tratamento é a mais de 50 km e não existe na sua região, o SUS pode pagar transporte e diárias",
          "INCA – cartilha Direitos sociais da pessoa com câncer",
          "https://www.inca.gov.br/publicacoes/cartilhas/direitos-sociais-da-pessoa-com-cancer-orientacoes-aos-usuarios",
          como="O médico do SUS faz o pedido e uma comissão do município (ou do Estado) autoriza. Cobre transporte e "
               "diárias de alimentação e pernoite para a paciente e, se preciso, um acompanhante, conforme o "
               "orçamento. Depois da consulta, guarde o comprovante para a prestação de contas.",
          confirmar="Em Rio Claro, pergunte à Fundação Municipal de Saúde onde se pede o TFD."),
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
          "https://www.inca.gov.br/publicacoes/cartilhas/direitos-sociais-da-pessoa-com-cancer-orientacoes-aos-usuarios",
          como="Explica benefícios do INSS, FGTS e PIS, isenções, transporte, prioridade na Justiça e outros direitos."),

    # ---------------- CUIDAR (mais apoio) ----------------
    _item("ames_estado", "mama", "caminho", "Estado de SP",
          "AMEs – Ambulatórios Médicos de Especialidades",
          "especialistas e exames do Estado, marcados pela unidade básica de saúde",
          "Governo do Estado de SP",
          "https://www.saopaulo.sp.gov.br/spnoticias/ultimas-noticias/veja-a-relacao-dos-ames-ambulatorios-medicos-"
          "de-especialidades-no-estado/",
          como="Os AMEs fazem consultas com especialistas e exames (muitos fazem mamografia). A consulta é marcada "
               "pela UBS do município, por sistema online."),
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
          "AME Rio Claro (Seconci-SP)",
          "https://seconci-sp.org.br/amerioclaro/",
          como="Tem especialidade dedicada às mamas, na prevenção e no tratamento. A consulta é marcada pela unidade "
               "de saúde do município.",
          contato="Rua 9 (esquina com a Avenida da Saudade), 165 – Bairro dos Estádios. (19) 3526-2300.",
          confirmar="Algumas fontes trazem outro telefone: confirme na página do AME."),
    _item("rc_ddm", "ajuda", "rio_claro", "Rio Claro",
          "Delegacia de Defesa da Mulher (DDM) de Rio Claro",
          "registrar ocorrência e pedir medida protetiva na cidade",
          "OAB Rio Claro e Polícia Civil",
          "https://www.oabrioclaro.org.br/1955-2/",
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
GRUPOS_CARRETAS = ["Carretas da Mamografia do Estado", "Unidades móveis do Hospital de Amor"]
GRUPOS = {"barretos": GRUPOS_BARRETOS, "hospitais": GRUPOS_HOSPITAIS, "carretas": GRUPOS_CARRETAS}

# "Preciso de ajuda": em que ponto a mulher está -> portas e itens.
# (id, rótulo, fala da Lia, portas indicadas, itens mostrados)
ETAPAS = [
    ("nao_fiz", "Ainda não fiz o exame",
     "O começo é a unidade de saúde do seu bairro: lá se faz o preventivo e se pede a mamografia. De 50 a 69 anos "
     "a mamografia pelo Estado não precisa de pedido médico, e as carretas atendem sem agendamento.",
     ["mama", "colo"], ["rc_unidades", "mulheres_de_peito", "colo_utero"]),
    ("alterado", "Meu exame deu alteração",
     "Um exame alterado não quer dizer câncer: é o começo de uma investigação. Leve o laudo à unidade de saúde, "
     "e a lei garante os exames de diagnóstico em até 30 dias.",
     ["diagnostico"], ["mamografia_alterada", "preventivo_alterado", "lei_30_dias"]),
    ("encaminhada", "Fui encaminhada",
     "Depois do encaminhamento, a vaga é organizada pela regulação do Estado. Você pode acompanhar a fila da "
     "oncologia e, se o nome não aparecer, sabe onde procurar ajuda.",
     ["regulacao"], ["lista_regulacao", "nao_achei_nome", "como_chegar_cross"]),
    ("diagnostico_cancer", "Recebi diagnóstico de câncer",
     "Com o diagnóstico, o tratamento pelo SUS deve começar em até 60 dias, num hospital habilitado da rede. Você "
     "também tem direitos, como transporte e benefícios.",
     ["tratamento", "rede", "direitos"], ["lei_60_dias", "como_chegar_cross", "cartilha_inca"]),
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


# ---------- itinerário das Carretas da Mamografia do Estado ----------
# Trazido pelo autor em 24/09/2026 e conferido nas notícias da Agência
# SP. Muda todo mês: quando vencer, o painel e a Lia avisam para ver o
# novo no Poupatempo. Atualizar = trocar esta lista (datas em 2026).
FONTES_ITINERARIO = {
    "setembro": ("Agência SP – Carretas da Mamografia atenderão a capital e mais cinco municípios em setembro",
                 "https://www.agenciasp.sp.gov.br/carretas-da-mamografia-atenderao-capital-e-mais-cinco-municipios-no-"
                 "estado-em-setembro/"),
    "fim_setembro": ("Agência SP – Carretas fecham o mês de setembro em cinco municípios (publicada em 23/09/2026)",
                     "https://www.agenciasp.sp.gov.br/carretas-de-prevencao-ao-cancer-de-mama-fecham-o-mes-de-setembro-"
                     "em-cinco-municipios-paulistas-veja-itinerario/"),
}
ITINERARIO = [
    {"cidade": "Apiaí", "inicio": None, "fim": None, "local": None, "fonte": "setembro"},
    {"cidade": "Bananal", "inicio": date(2026, 9, 3), "fim": date(2026, 9, 14), "local": None, "fonte": "setembro"},
    {"cidade": "São Paulo (Paraisópolis)", "inicio": date(2026, 9, 10), "fim": date(2026, 9, 21), "local": None,
     "fonte": "setembro"},
    {"cidade": "Eldorado", "inicio": date(2026, 9, 16), "fim": date(2026, 9, 28), "local": None, "fonte": "setembro"},
    {"cidade": "Piquete", "inicio": date(2026, 9, 17), "fim": date(2026, 9, 28), "local": None, "fonte": "setembro"},
    {"cidade": "Araçoiaba da Serra", "inicio": date(2026, 9, 24), "fim": date(2026, 10, 5), "local": None,
     "fonte": "setembro"},
    {"cidade": "Bertioga", "inicio": date(2026, 9, 22), "fim": date(2026, 10, 3),
     "local": "Avenida São Gonçalo, s/n – Chácara Vista Linda", "fonte": "fim_setembro"},
    {"cidade": "Serrana", "inicio": date(2026, 9, 22), "fim": date(2026, 10, 3),
     "local": "Rua Tancredo de Almeida Neves, 176 – Jardim Bela Vista", "fonte": "fim_setembro"},
    {"cidade": "Barra do Turvo", "inicio": date(2026, 9, 22), "fim": date(2026, 10, 3),
     "local": "Avenida Vinte e Um de Março, 304 – Centro", "fonte": "fim_setembro"},
    {"cidade": "Itapura", "inicio": date(2026, 9, 22), "fim": date(2026, 10, 3),
     "local": "Av. Mal. Artur Costa e Silva, 1120 (em frente à UBS II)", "fonte": "fim_setembro"},
    {"cidade": "Avaré", "inicio": date(2026, 9, 22), "fim": date(2026, 10, 3),
     "local": "Praça Prefeito Romeu Bretas (Praça da Concha Acústica) – Centro", "fonte": "fim_setembro"},
]
SITUACOES = {"agora": "Agora", "em_breve": "Em breve", "sem_data": "Sem data publicada", "encerrada": "Já passou"}


def hoje():
    """A data de hoje (função própria para os testes fixarem o dia)."""
    return date.today()


def carretas(dia=None):
    """O itinerário com a situação de cada carreta no dia: agora, em
    breve, sem data publicada ou já passou (nessa ordem)."""
    dia = dia or hoje()
    lista = []
    for c in ITINERARIO:
        if c["inicio"] is None:
            situacao = "sem_data"
        elif dia < c["inicio"]:
            situacao = "em_breve"
        elif dia > c["fim"]:
            situacao = "encerrada"
        else:
            situacao = "agora"
        lista.append({**c, "situacao": situacao})
    ordem = list(SITUACOES)
    return sorted(lista, key=lambda c: (ordem.index(c["situacao"]), c["inicio"] or date.max, c["cidade"]))


def itinerario_vencido(dia=None):
    """True quando todas as datas guardadas já passaram."""
    dia = dia or hoje()
    return all(c["fim"] is None or c["fim"] < dia for c in ITINERARIO)


def periodo(c):
    if c["inicio"] is None:
        return "datas no Poupatempo"
    return f"{c['inicio']:%d/%m} a {c['fim']:%d/%m}"


def frase_carretas(dia=None):
    """A fala da Lia sobre onde a carreta está no dia."""
    dia = dia or hoje()
    if itinerario_vencido(dia):
        return (f"O itinerário que eu tenho terminou em {max(c['fim'] for c in ITINERARIO if c['fim']):%d/%m}. "
                "Consulte o novo no Poupatempo (cartão Carretas da Mamografia).")
    lista = carretas(dia)
    agora = [c for c in lista if c["situacao"] == "agora"]
    breve = [c for c in lista if c["situacao"] == "em_breve"]
    partes = [f"**Hoje ({dia:%d/%m}) a carreta está em:** "
              + (", ".join(f"{c['cidade']} (até {c['fim']:%d/%m})" for c in agora) if agora else "nenhuma cidade")
              + "."]
    if breve:
        partes.append("**Em breve:** " + ", ".join(f"{c['cidade']} ({periodo(c)})" for c in breve) + ".")
    partes.append(f"Nenhuma está na região de {CIDADE} ({REGIAO}) neste itinerário; ele muda todo mês."
                  if not any(c["cidade"] == CIDADE for c in agora + breve) else "")
    return " ".join(p for p in partes if p)


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
        return [(f"Próximo passo: {NOME_CAMINHO[PROXIMO[c]]}", caminho(PROXIMO[c]))]
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
    """Onde está o texto completo do item (para o cartão curto)."""
    if i["lamina"] == "caminho":
        return f"porta {NOME_CAMINHO[i['caminho']]}"
    return f"lâmina {LAMINAS[i['lamina']]}"


def itens_da_etapa(e):
    if e == "violencia":
        return [i for i in ITENS if i["caminho"] == "ajuda"]
    _, _, _, _, ids = next(x for x in ETAPAS if x[0] == e)
    return [POR_ID[i] for i in ids]


def saudacao():
    return Resposta(
        fala=f"Você está em **{CIDADE}**. O que você precisa? Escolha uma porta e eu mostro o caminho na rede de "
             "saúde, com as páginas oficiais.",
        expressao="acolhedora",
        botoes=[(r, caminho(c)) for c, r, _, _ in CAMINHOS]
        + [("Hospitais no Estado", lamina("hospitais")), ("Carretas: onde estão agora", lamina("carretas")),
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
        botoes=[(f"Porta {NOME_CAMINHO[c]}", caminho(c)) for c in portas]
        + ([("Carretas: onde estão agora", lamina("carretas"))] if e == "nao_fiz" else [])
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
    if c == "rede":
        fala += "\n\n**O caminho na rede:** " + " → ".join(p for p, _, _ in FLUXO_REDE) + "."
    fala += "\n\n" + "\n".join(f"- **{i['titulo']}** · {i['onde']}: {i['resumo']}." for i in lista)
    botoes = [(i["titulo"], item(i["id"])) for i in lista]
    partes = []
    for lam, fora in nas_laminas(c).items():
        if lam != "caminho" and len(fora) > MAX_APONTADOS:
            partes.append(f"{len(fora)} itens na lâmina {LAMINAS[lam]}")
            botoes.append((f"Ver a lâmina {LAMINAS[lam]}", lamina(lam)))
        else:
            partes += [f"{i['titulo']} ({onde_mora(i)})" for i in fora]
            botoes += [(i["titulo"], item(i["id"])) for i in fora]
    if partes:
        fala += "\n\nTambém para esta porta: " + "; ".join(partes) + "."
    if c == "mama":
        fala += "\n\n" + frase_carretas()
        botoes.append(("Carretas: onde estão agora", lamina("carretas")))
    return Resposta(
        fala=fala,
        expressao="explicando",
        botoes=botoes + _proximo(c),
        destino={"aba": LAMINAS["caminho"], "caminho": c},
        numeros=[f"{i['titulo']}: {i['fonte']}" for i in lista],
    )


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
    for rotulo, chave in (("Para quem", "para_quem"), ("O que levar", "levar"), ("Como funciona", "como"),
                          ("Onde e contato", "contato")):
        if i[chave]:
            partes.append(f"**{rotulo}:** {i[chave]}")
    if i["cuidado"]:
        partes.append(f"**Atenção:** {i['cuidado']}")
    if i["confirmar"]:
        partes.append(f"**A confirmar:** {i['confirmar']}")
    partes.append(f"[Abrir a página oficial]({i['link']})")
    partes.append(AVISO)
    return Resposta(
        fala="\n\n".join(partes),
        expressao="cautelosa" if i["confirmar"] else ("acolhedora" if i["caminho"] == "ajuda" else "explicando"),
        botoes=_voltar(i) + _proximo(i["caminho"]),
        destino={"aba": LAMINAS[i["lamina"]], "caminho": i["caminho"], "grupo": i["grupo"], "item": id,
                 "etapa": "violencia" if i["caminho"] == "ajuda" and i["lamina"] == "caminho" else None},
        numeros=[f"Fonte: {i['fonte']}", f"Página: {i['link']}", f"Conferido em {CONFERIDO}"],
    )


INTRO_LAMINA = {
    "barretos": ("**Barretos** reúne, no **Hospital de Amor**, hospitais de referência, prevenção, carretas, ensino e "
                 "pesquisa em câncer. Aqui estão as informações e os links oficiais, e a ligação com a nossa cidade: "
                 "em fevereiro de 2025 a carreta do hospital esteve em Rio Claro. Escolha um tema."),
    "hospitais": ("Estes são **hospitais que tratam câncer pelo SUS no Estado de São Paulo**, por região. Eles não "
                  "são porta de entrada: chega-se a eles pela regulação (CROSS), a partir da unidade de saúde. Para "
                  "quem mora em Rio Claro, as referências são Rio Claro e Piracicaba, e o HC da Unicamp também atende "
                  "a região. Escolha uma região."),
    "carretas": ("**Carretas da mamografia**: o exame vai até a mulher, de graça. As do Estado mudam de cidade todo "
                 "mês; o Hospital de Amor também tem unidades móveis."),
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
                "e o HC da Unicamp também atende a região (lâmina Hospitais no Estado).")
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
        fala=(f"Juntei estas informações em {CONFERIDO}, a partir de páginas oficiais: Secretaria da Saúde e "
              "Secretaria da Mulher do Estado de SP, FOSP, INCA, Ministério da Saúde e das Mulheres, Defensoria "
              "Pública, Poupatempo, Fundação Municipal de Saúde e Prefeitura de Rio Claro, prefeituras de outras "
              "cidades e os próprios hospitais. Cada item traz a página oficial. "
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
