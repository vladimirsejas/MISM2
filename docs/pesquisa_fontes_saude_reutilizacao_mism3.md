# Pesquisa de fontes de saúde para reutilização no MISM2

**Pesquisa registrada em 09/10/2026.** Este documento preserva referências e hipóteses de análise que também podem apoiar o MISM3. Os projetos permanecem separados: MISM3 é a prioridade de produto e serviços municipais; MISM2 é o projeto analítico de saúde da mulher com dados do SUS.

## 1. Achados locais de Rio Claro

### Protocolos da Fundação Municipal de Saúde
- Índice oficial de protocolos: https://www.saude-rioclaro.org.br/protocolos.htm
- Protocolo de câncer de mama: https://www.saude-rioclaro.org.br/protocolos/Protocolo%20de%20CA%20de%20mama.pdf
- Protocolo de câncer do colo do útero: https://www.saude-rioclaro.org.br/uac/Protocolo%20do%20Cancer%20Colo%20utero%20QRcode.pdf
- Protocolo de câncer do colo do útero (revisão indicada em 2026): https://www.saude-rioclaro.org.br/protocolos/Protocolo%20CA%20colo%20do%20utero%202026.pdf

Informações identificadas nos documentos:
- O protocolo municipal de mama menciona 127 diagnósticos registrados em Rio Claro entre 2020 e 2024.
- O protocolo de colo do útero menciona 35 encaminhamentos em 2023 e 55 em 2024 para tratamento de lesões precursoras, câncer in situ e/ou invasor.
- Os documentos tratam da organização da linha de cuidado, rastreamento, diagnóstico, encaminhamento e acompanhamento.

**Uso recomendado no MISM2:** contexto local para discussão e triangulação de achados, não como substituto dos microdados de internação e não como observações diretamente comparáveis sem definição, período e fonte. Diagnósticos, encaminhamentos, exames e internações são medidas diferentes.

## 2. Fontes públicas de dados e indicadores

### DATASUS — SISCAN
https://datasus.saude.gov.br/acesso-a-informacao/sistema-de-informacao-do-cancer-siscan-colo-do-utero-e-mama/

O portal oferece consultas sobre citopatologia e histopatologia do colo do útero, mamografia e citopatologia/histopatologia de mama, com opções por residência e local de atendimento.

**Potencial:** comparar procedimentos com o padrão de internações do MISM2, distinguindo município de residência de município de atendimento. Verificar cobertura, unidade de contagem e regras de cada consulta antes de comparar resultados.

### DATASUS — Epidemiologia e morbidade
https://datasus.saude.gov.br/epidemiologicas-e-morbidade/

Reúne caminhos para SIH/SUS (morbidade hospitalar), SIM (mortalidade), SINAN e SISCAN. É uma fonte de referência para documentar proveniência e encontrar séries complementares.

### INCA — dados e números de câncer de mama
https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros

Reúne séries e análises sobre detecção precoce, produção de procedimentos e mortalidade a partir de sistemas como SIA, SIM e SISCAN. Serve como comparação contextual nacional/estadual, não como substituto dos dados locais.

### INCA — dados e números de câncer do colo do útero
https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-do-colo-do-utero/dados-e-numeros

Apresenta dados para monitoramento da linha de cuidado com fontes como SIA, SIM e SISCAN, além de inquéritos nacionais.

### Portal de Dados Abertos do SUS — prevenção de câncer de colo e mama
https://dadosabertos.saude.gov.br/dataset/mgdi-prevencao-do-cancer-de-colo-e-mama

Lista recursos sobre exames citopatológicos em mulheres de 25 a 64 anos, mamografias, hospitais habilitados, serviços de referência, laboratórios e recursos relacionados à prevenção e ao tratamento. A página indicava atualização dos recursos em junho de 2026. Conferir granularidade territorial, dicionário e período de cada arquivo antes de incorporar.

### Painel-Oncologia
https://www.gov.br/saude/pt-br/composicao/saes/cgcan/cgcan

O Ministério da Saúde descreve o painel como instrumento de monitoramento do prazo para início do primeiro tratamento oncológico, calculado a partir de registros no SIA, SIH e SISCAN. Pode complementar o estudo de oportunidade de tratamento, respeitando a cobertura e as regras da base.

## 3. Indicadores que podem ser úteis

Avaliar disponibilidade e definição antes de implementar:
1. Internações SUS por tipo de câncer, ano, idade/faixa etária e município de residência.
2. Internações por município de atendimento versus residência, para identificar deslocamento para tratamento fora do município.
3. Procedimentos de rastreamento/diagnóstico (mamografia, citopatologia, histopatologia), separados de diagnósticos e internações.
4. Mortalidade por causa específica e período, a partir do SIM, com denominadores populacionais apropriados.
5. Tempo até início do tratamento, apenas se a fonte e a cobertura forem adequadas à escala de análise.
6. Comparações municipais/estaduais com denominadores, faixas etárias e períodos compatíveis.
7. Mudanças na produção assistencial ao longo do tempo, evitando interpretar aumento de procedimentos como aumento automático da incidência.

## 4. Regras metodológicas

- O conjunto principal do MISM2 é baseado em internações hospitalares do SUS (SIH/SUS); não representa todos os casos incidentes de câncer na população.
- Uma pessoa pode gerar mais de uma internação. Não chamar contagem de internações de “número de mulheres com câncer” sem deduplicação e metodologia apropriadas.
- Diagnósticos mencionados em protocolo, encaminhamentos, exames, internações e óbitos são medidas distintas.
- Diferenciar município de residência e município de atendimento.
- Não combinar sistemas distintos sem documentar definições, códigos, períodos, denominadores, cobertura e limitações.
- Séries de 2025 podem estar incompletas ou sujeitas a atraso de consolidação; verificar cobertura mês a mês antes de comparar com anos completos.
- Para taxas, usar denominadores compatíveis com sexo, idade, território e período; para comparar populações com estruturas etárias diferentes, considerar padronização.
- Evitar divulgar células muito pequenas que possam permitir identificação indireta.
- Não publicar dados pessoais, identificadores, endereço, CEP individual ou coordenadas de pacientes.

## 5. Como compartilhar achados com o MISM3 sem misturar projetos

**Pode ser reaproveitado no MISM3:** links e protocolos municipais oficiais; contatos e descrição de serviços públicos confirmados; lista de indicadores propostos e suas definições; estatísticas agregadas públicas com fonte e período; referências sobre linhas de cuidado e gargalos de acesso.

**Não copiar automaticamente do MISM2 para o MISM3:** microdados ou registros individuais; tabelas agregadas sem documentação; estimativas territoriais baseadas na localização de paciente; resultados exploratórios apresentados como indicadores oficiais municipais.

Para o MISM3, priorizar catálogo de serviços e estrutura de indicadores de gestão. Para o MISM2, preservar a análise de internações SIH/SUS e usar SISCAN, SIM, SIA e protocolos como fontes complementares claramente separadas.

## 6. Serviços concretos e direitos de acesso (atualização de 09/10/2026)

Esta seção prioriza caminhos de acesso e direitos úteis à saúde da mulher. Não é uma coleção de notícias nem substitui o catálogo de serviços do MISM3. No MISM2, essas referências servem para contextualizar a linha de cuidado e formular perguntas para a gestão; não devem ser tratadas como prova de que a pessoa conseguiu atendimento.

### Acesso local em Rio Claro

- **Agendamento na rede municipal (Cadu):** telefone/WhatsApp **0800 019 0505**. A publicação municipal de 07/10/2026 confirma que consultas para solicitar mamografia e Papanicolau podem ser agendadas diretamente na unidade de saúde ou pelo Cadu. O exame depende de solicitação de profissional de saúde. O comunicado não deve ser usado como garantia permanente de ausência de fila; disponibilidade e regras podem mudar.
  - Referência oficial que confirma o canal: https://rioclaro.sp.gov.br/fundacao-de-saude/outubro-rosa-reforca-importancia-de-exames-preventivos/
  - Página de referência da central: https://rioclaro.sp.gov.br/fundacao-de-saude/nova-central-para-agendamento-de-consultas-comeca-a-operar-na-2a-feira-em-rc/
- **Endereços das unidades municipais:** https://www.saude-rioclaro.org.br/enderecos.html
- **Protocolos municipais:** https://www.saude-rioclaro.org.br/protocolos.htm
- **Protocolo municipal de câncer de mama:** https://www.saude-rioclaro.org.br/protocolos/Protocolo%20de%20CA%20de%20mama.pdf
- **Protocolo municipal de câncer do colo do útero:** https://www.saude-rioclaro.org.br/uac/Protocolo%20do%20Cancer%20Colo%20utero%20QRcode.pdf
- **Revisão de 2026 do protocolo de colo do útero:** https://www.saude-rioclaro.org.br/protocolos/Protocolo%20CA%20colo%20do%20utero%202026.pdf

### Direitos e caminhos nacionais

- **Tratamento oncológico pelo SUS — Lei nº 12.732/2012:** https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12732.htm
  - Estabelece o direito ao primeiro tratamento de neoplasia maligna comprovada em até 60 dias a partir do diagnóstico em laudo patológico, ou em prazo menor quando a necessidade terapêutica estiver registrada.
  - A lei também prevê prazo máximo de 30 dias para exames necessários à elucidação diagnóstica quando a principal hipótese for neoplasia maligna e houver solicitação médica fundamentada.
  - Esses prazos são direitos legais, não uma afirmação de que o prazo esteja sendo cumprido localmente. O MISM2 não pode inferir cumprimento ou descumprimento sem dados adequados.
- **Onde tratar câncer pelo SUS (INCA):** https://www.gov.br/inca/pt-br/assuntos/cancer/tratamento
  - Referência para localizar a rede habilitada; antes de orientar uma pessoa, é necessário confirmar o serviço de referência e o fluxo de encaminhamento aplicável a Rio Claro.
- **SISCAN — exames e produção relacionados a mama e colo do útero:** https://datasus.saude.gov.br/acesso-a-informacao/sistema-de-informacao-do-cancer-siscan-colo-do-utero-e-mama/
  - Fonte para análise de exames/procedimentos, não um canal de agendamento para pacientes.
- **INCA — detecção precoce do câncer de mama:** https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/acoes/deteccao-precoce
  - A orientação nacional atualizada em 2025 prioriza mamografia de rastreamento a cada dois anos para mulheres de 50 a 74 anos. Para mulheres de 40 a 49 anos e acima de 74, a possibilidade de exame deve ser discutida com profissional de saúde, considerando riscos e benefícios.
  - **Atenção à divergência de comunicação:** a página municipal publicada em outubro de 2026 afirma que mulheres a partir de 40 anos têm direito ao rastreamento. Não reproduzir essa frase no MISM2 como regra nacional universal. Diferenciar a orientação local de acesso da recomendação nacional para rastreamento de rotina e encaminhar dúvidas individuais à equipe de saúde.

### Planejamento Municipal de Saúde 2026 — serviços e ações a acompanhar

**Documento oficial:** [Programação Anual de Saúde (PAS) 2026 — PDF](https://saude-rioclaro.org.br/uac/PAS%202026-%20FINAL.pdf). É uma fonte de planejamento municipal, não uma lista de vagas disponíveis. As metas e ações abaixo foram identificadas no documento; antes de anunciar qualquer serviço ao público, confirmar a oferta efetiva, critérios de elegibilidade, unidade responsável e forma de acesso.

- **Saúde sexual e reprodutiva:** a PAS prevê oferta de métodos contraceptivos na Atenção Primária, ações educativas, planejamento reprodutivo e continuidade da inserção de DIU. Menciona DIU no pós-parto imediato na maternidade, inserção em UBS e continuidade no CEAD, além de implantes contraceptivos (LARC/Implanon) e DIU Mirena para mulheres elegíveis, conforme protocolo.
- **Pré-natal e puerpério:** prevê atualização dos protocolos, identificação e acompanhamento de gestantes, testagem para gravidez, exames em tempo oportuno e encaminhamento ao pré-natal de alto risco quando necessário.
- **Rastreamento de câncer feminino:** a PAS descreve intensificação do exame preventivo do colo do útero para mulheres cadastradas de 25 a 64 anos e mamografia bienal para mulheres cadastradas de 50 a 69 anos, além de busca ativa, ampliação de coleta/vagas e campanhas. Isso registra a meta municipal de planejamento; não confirma que exista vaga imediata nem substitui avaliação individual.
- **Testes e cuidado de ISTs:** prevê testes rápidos na Atenção Básica, ações de testagem em campanhas e territórios, tratamento e acompanhamento, com atenção especial à sífilis e ao pré-natal.
- **Atenção a pessoas em situação de violência:** a PAS prevê articulação intersetorial e qualificação do protocolo de atenção integral à pessoa em situação de violência. O documento menciona elaboração de protocolos para violência sexual e aborto legal; portanto, não devemos afirmar que todos esses fluxos estejam concluídos apenas porque constam do planejamento.
- **Acesso territorial e continuidade:** o plano prevê ampliar a cobertura da Estratégia Saúde da Família, qualificar cuidado de hipertensão/diabetes e fortalecer referência e contrarreferência. São metas de gestão úteis para acompanhar, não serviços novos já comprovadamente implantados.

**Como usar no MISM2:** estes pontos ajudam a formular perguntas de gestão e a interpretar resultados de internações de câncer feminino. Exemplo: comparar a evolução de internações com a existência de ações de rastreamento documentadas, sem concluir que a ação causou a mudança. A PAS não fornece, por si só, resultados de execução ou cobertura efetiva.

**Como compartilhar com o MISM3:** priorizar somente caminhos concretos que possam ser verificados para o público — unidades, agendamento, contracepção, pré-natal, exames, testagem, transporte de saúde e atendimento especializado. Os itens da PAS que ainda são metas devem permanecer identificados como “previsto no planejamento; oferta a confirmar”, não como benefício garantido.

### Como aproveitar sem transformar o MISM2 em catálogo de notícias

1. Na interpretação dos resultados, indicar o protocolo municipal pertinente como referência de linha de cuidado.
2. Em uma eventual seção de orientação, oferecer somente links estáveis de serviço/direitos e registrar a data da última verificação.
3. Separar **disponibilidade anunciada**, **solicitação/agendamento**, **exame realizado**, **diagnóstico**, **encaminhamento** e **internação**. São etapas diferentes e não devem ser tratadas como equivalentes.
4. Não afirmar que há vaga, fila zerada ou atendimento garantido com base em uma notícia isolada.
5. Antes de apresentar um link como caminho de atendimento atual, conferir se a página e o canal continuam ativos. Os links de notícias servem apenas como evidência datada de uma informação operacional, não como substitutos da página do serviço.

## Fontes
- Fundação Municipal de Saúde de Rio Claro: https://www.saude-rioclaro.org.br/protocolos.htm
- DATASUS, SISCAN: https://datasus.saude.gov.br/acesso-a-informacao/sistema-de-informacao-do-cancer-siscan-colo-do-utero-e-mama/
- DATASUS, Epidemiologia e morbidade: https://datasus.saude.gov.br/epidemiologicas-e-morbidade/
- INCA, Dados e Números — mama: https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros
- INCA, Dados e Números — colo do útero: https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-do-colo-do-utero/dados-e-numeros
- Portal de Dados Abertos do SUS: https://dadosabertos.saude.gov.br/dataset/mgdi-prevencao-do-cancer-de-colo-e-mama
- Ministério da Saúde, Painel-Oncologia: https://www.gov.br/saude/pt-br/composicao/saes/cgcan/cgcan
