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

## Fontes
- Fundação Municipal de Saúde de Rio Claro: https://www.saude-rioclaro.org.br/protocolos.htm
- DATASUS, SISCAN: https://datasus.saude.gov.br/acesso-a-informacao/sistema-de-informacao-do-cancer-siscan-colo-do-utero-e-mama/
- DATASUS, Epidemiologia e morbidade: https://datasus.saude.gov.br/epidemiologicas-e-morbidade/
- INCA, Dados e Números — mama: https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros
- INCA, Dados e Números — colo do útero: https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-do-colo-do-utero/dados-e-numeros
- Portal de Dados Abertos do SUS: https://dadosabertos.saude.gov.br/dataset/mgdi-prevencao-do-cancer-de-colo-e-mama
- Ministério da Saúde, Painel-Oncologia: https://www.gov.br/saude/pt-br/composicao/saes/cgcan/cgcan
