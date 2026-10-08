# Escudo Feminino

Sistema de apoio à decisão para políticas públicas em saúde da mulher,
construído a partir de dados de internações hospitalares do SUS
relacionadas a câncer feminino no município de Rio Claro (SP), comparado
ao Estado de São Paulo. Trabalho acadêmico de graduação em Inteligência
Artificial — Fatec Rio Claro, 3º semestre.

O `README.md` é **informativo, não diretriz**: é o último passo do
trabalho, só registra o que já foi decidido e feito. Não se prender a
ele nem tratá-lo como guia; se divergir da conversa com o autor ou do
código, valem a conversa e o código (e o README é atualizado depois).
Ele traz, como registro, a ordem de execução dos scripts antigos em
`algoritimos/` (cada um lê o resultado do anterior).

## Autorização permanente de git

O dono deste repositório (Vladimir) autorizou explicitamente: Claude pode
criar/corrigir código para melhorar este projeto e enviar (`git push`)
direto para o branch `main`, sem precisar pedir confirmação a cada vez —
incluindo commitar, fazer merge de outro branch e dar push direto no
`main`. Essa autorização vale de forma permanente para este repositório
específico (não se estende a outros repositórios do usuário nem
dispensa cuidado normal: sempre validar a mudança — rodar `py_compile`,
testar a lógica isoladamente quando possível, revisar o diff — antes do
push, e nunca commitar segredos/credenciais).

## Arquitetura territorial (código IBGE)

O projeto está migrando de "Rio Claro fixo" para "município
configurável", identificado pelo código oficial do IBGE:

- Tabela `municipios` (codigo_ibge, origem, nome, uf) associa
  metadados IBGE a cada valor já usado em `internacoes.origem`.
  `origem` continua sendo o identificador interno usado em todo
  `WHERE origem = ?` do projeto -- a tabela só adiciona código IBGE
  e nome de apresentação em cima dele. Criada por
  `etl/criar_tabela_municipios.py`, hoje só com Rio Claro (IBGE
  3543907). SP não entra nela: é a referência estadual, não um
  município.
- `configuracao_geografica.py` expõe `obter_municipio()` (aceita
  identificador de texto OU código IBGE via `ESCUDO_MUNICIPIO`),
  `obter_codigo_ibge()`, `obter_nome_municipio()`, `obter_uf()` e
  `listar_municipios_disponiveis()` (consulta `municipios ∩
  internacoes`, nunca lista fixa no código).
- `dashboard/app.py` tem seletor de município no topo (populado por
  `listar_municipios_disponiveis()`) e lê tudo de
  `algoritimos/inteligencia.py`, direto de `internacoes`.
- Municípios disponíveis dependem só dos dados carregados no banco --
  adicionar uma cidade é (1) ter os CSVs estaduais em `dados\` (a
  carga já traz todas as cidades de SP pelo MUNIC_RES), (2) a cidade
  estar no catálogo `municipios`. Nenhum código precisa mudar.

**Limpeza de 09/2026:** a arquitetura antiga saiu do repositório (está
no histórico do git; lista e motivos em `docs/INVENTARIO_DO_CODIGO.md`):
a cadeia das 13 tabelas derivadas (mortalidade, custos, anomalias,
priorizador, base_conhecimento, memoria_ia...), o chat de terminal
(`chat_escudo.py`, `motor_raciocinio.py`, `padroes_analiticos.py`) e os
testes dela, os scripts avulsos de `analises/` e as espiadas no banco
(fica só `etl/validar_banco.py`). Ela calculava em paralelo, sem as
regras novas (meses da fonte, fonte única), e podia divergir do painel.
`salvar_tabela_municipio`/`ler_tabela_municipio` saíram de
`configuracao_geografica.py`. Ideias antigas (vulnerabilidade, score,
perfil) só voltam como função nova em `inteligencia.py`.

**Pendência:** comparação entre municípios depende da população do IBGE
(gráfico de funil, cidades semelhantes).

## Painel novo (09/2026) — decisões combinadas com o autor

Depois do retorno da Secretaria da Mulher, o autor (com Claude e
ChatGPT) decidiu **reduzir** o Escudo: uma inteligência central com
poucas portas de entrada, não cinco sistemas. Regras:

- **Toda funcionalidade nova precisa responder uma pergunta que o
  Escudo ainda não responde.** Se não responder, não entra.
- **Cada informação tem uma casa só** no painel; não repetir números
  em várias telas.
- **Todo gráfico = pergunta (título) + gráfico + leitura em texto.**
- **A inteligência calcula, o Gemini explica.** Nunca atribuir
  causa; detectar ≠ explicar.
- **Nada de orçamento em reais.** O Escudo aponta o que merece
  atenção no planejamento, com evidências; quem decide é o gestor.
  (A aba "Onde investir", commit `273fbe5`, foi descartada por isso.)
- Usuários: gestores (Secretaria é uma delas), pesquisadores,
  estudantes, população (via modo simples do chat).
- **Pensar e combinar antes de codar.** O autor pediu explicitamente
  para não sair implementando sem conversar.

Estado atual:
- `algoritimos/inteligencia.py`: única fonte dos números do painel
  (série anual cidade + Estado, anos fora do padrão, ritmo do Estado
  na escala da cidade, projeção exploratória com teste de acerto,
  frases de leitura). Testado por `teste_inteligencia.py`.
- `dashboard/app.py`: portas em abas, cada informação numa casa só --
  **Panorama** (barras medidas por internações / valor hospitalar
  registrado / óbitos / dias + ficha "o que chama atenção" do câncer
  em foco), **Evolução** (linha com camadas Estado / fora do padrão /
  projeção de tendência + caixa de confiabilidade), **Investigar**
  (anos fora do padrão de todos os cânceres, "quando cada câncer
  aparece", faixa etária em dois períodos, download CSV),
  **Planejamento** = **radar do futuro** ("Se nada mudar, onde a
  cidade pode ter problema até <ano+3>?": `inteligencia.radar_futuro`,
  níveis alerta / observar / estável com os sinais, dias de leito a
  mais, cuidados e linha de ação do INCA; quadrante crescimento x
  letalidade colorido pelo nível), **Método**. Lia na
  lateral (só botões).
- Dinheiro sempre como **"valor hospitalar registrado no SIH/SUS"**
  (VAL_TOT das AIHs): não é orçamento municipal nem custo total do
  tratamento. Projeção sempre como **"projeção de tendência"**, nunca
  "IA preditiva". Óbitos não são projetados (poucos por ano).
- **Lia** (`algoritimos/lia.py`, `dashboard/lia_rosto.py`,
  `docs/LIA.md`): guia do Escudo, pesquisadora negra madura (não
  médica, sem marca de instituição real). Árvore de 3 níveis
  (caminhos -> câncer -> ação), falas determinísticas montadas com
  `inteligencia.py`, expressão do rosto escolhida pela confiabilidade
  do dado (acolhedora / explicando / atenta / cautelosa / pensativa).
  O painel acompanha a Lia (aba, câncer, medida, camadas). Testado por
  `teste_lia.py`. **A caixa de texto livre saiu (decisão do autor,
  09/2026):** respondia o mesmo que os botões, com menos precisão; a
  Lia conduz só por botões. Mais opções devem entrar como caminhos
  novos na árvore, não como texto livre. **Fechamento das informações
  da Lia (09/2026):** mês ausente não é zero; ano incompleto não é ano
  normal. Caminho "Os dados estão completos?" (`lia.completude`), ano
  fora do padrão em ano incompleto marcado com cautela, projeção como
  "a tendência aponta" (nunca "vai"/"deve ficar"). A Lia só usa
  `inteligencia.py` (não depende de motor_raciocinio, memoria_ia,
  base_conhecimento, padroes_analiticos nem conversa.py). **Passeio pelo Escudo**
  (`algoritimos/passeio.py`, 09/2026): interação a mais, combinada com
  o autor -- 6 paradas na ordem, só cliques, cartão verde-água logo
  abaixo do rosto da Lia (convite no fim da lateral), falas da própria
  Lia, painel vai ao gráfico de cada parada (`aplicar_destino`). Não
  mudar o que já existe (lado direito, balão da Lia) sem combinar.
  **Teste de aceitação:** `dashboard/teste_painel.py` (AppTest: árvore
  inteira, 56 pares câncer x ação, voltar, passeio, abas) -- rodar
  antes de push que mexa no painel ou na Lia. O atalho `Abrir Escudo Feminino.bat`
  reinicia o painel quando o `git pull` traz código novo (o Streamlit
  não recarrega `algoritimos/` sozinho). **Armadilha do Streamlit resolvida no painel:**
  widgets que somem e voltam (abas desenhadas só quando abertas)
  devolviam o valor antigo; por isso cada widget tem chave atrelada
  ao valor (`chave_widget`) e o estado real fica em chaves próprias
  (`definir`). Não voltar a usar `key="doenca"` direto.
- **Apoio à mulher — "Encontre um caminho" (09/2026, pedido do autor):**
  outras lâminas, de APOIO, separadas do estudo da doença
  (`dashboard/pages/apoio.py`, aberta pelo botão vermelho "Apoio à mulher" no topo do
  painel; `showSidebarNavigation = false` em `.streamlit/config.toml`).
  Não mexer no painel principal por causa dela. Mesmo layout (CSS em
  `dashboard/estilo.py`, movido de app.py sem mudar uma letra) e a
  Lia idêntica, com a árvore de `algoritimos/apoio.py` (catálogo com
  fonte oficial, data de conferência e "a confirmar" em cada item).
  Lógica: Estado de SP primeiro (carretas, Mulheres de Peito, rede
  oncológica da FOSP, Lista de Regulação de Oncologia), depois as
  cidades como FONTE de itens (Campinas, Ribeirão Preto, Rio Preto,
  Piracicaba entram nos caminhos; sem lâmina por cidade). Exceções
  combinadas: lâmina **Rio Claro** (cidade do trabalho, mais detalhe)
  e **Barretos** (Hospital de Amor). Cada item tem uma casa só; os
  caminhos só apontam para os itens de Rio Claro e Barretos. Pesquisa
  de 24/09/2026 feita pela busca na web (o ambiente de nuvem não abre
  os sites do governo): itens com detalhe antigo ou de reportagem
  estão marcados "a confirmar" -- conferir no Windows e tirar a marca.
  Testes: `algoritimos/teste_apoio.py` e `dashboard/teste_apoio_tela.py`.
  **Botão "Início" (autor, 09/2026):** volta ao Panorama, a página inicial.
  No painel fica ao lado das abas (`inicio_painel`); no apoio, no topo e no
  fim da lateral (`inicio_topo`/`inicio_lateral`). Rótulo só "🏠 Início" (autor: "Panorama" confunde quem é de fora). Marca `aba = "Panorama"` e
  troca de página (`st.switch_page`). Substituiu o link "← Estudo da doença".
  **"O importante é saber onde clicar" (autor):** cada cartão tem o botão azul
  "Abrir a página oficial"; caminhos e temas aparecem como botões (container
  `ap_pilulas_*`); Barretos organizada nos temas do modelo do autor (Hospitais de
  referência, Prevenção, Mama, Colo do útero, Tratamento e acesso pelo SUS,
  Carretas, Ensino e pesquisa, No Estado de SP). O autor preferiu este layout à
  grade de blocos do modelo do ChatGPT.
  **Ampliação (autor achou "fraquinho"):** 75 itens. Lâmina nova **Hospitais no
  Estado** (23 hospitais de câncer pelo SUS em 8 regiões, com a lista oficial da
  FOSP, o INCA e "como chegar" pela CROSS; o HC Unicamp é referência também da
  DRS Piracicaba); caminho novo **Seus direitos** (TFD, FGTS/PIS, INSS e IR,
  reconstrução da mama, cartilha do INCA); Proteger com Casa da Mulher Brasileira,
  DDMs, Casas da Mulher Paulista, Defensoria (NUDEM) e violência sexual 24 h;
  Rio Claro com AME, DDM, Patrulha Maria da Penha e Rede Feminina. Item que mora
  numa lâmina e aparece em outra usa `tambem` (cartão curto, sem repetir texto).
  **Carretas (itinerário):** `apoio.ITINERARIO` (trazido pelo autor, conferido na
  Agência SP em 24/09/2026) alimenta o quadro "Onde a carreta está agora?" (Ir até
  você) e a fala da Lia, pela data do dia; vencido, avisa para ver o Poupatempo.
  Atualizar todo mês trocando a lista.
  **8 portas (proposta do autor, 09/2026):** Câncer de mama, Colo do útero,
  Diagnóstico, Regulação ("já fui encaminhada, e agora?"), Tratamento, Rede
  oncológica (fluxo UBS → diagnóstico → regulação → especialista → tratamento →
  acompanhamento), Direitos e acesso, Preciso de ajuda ("Em que ponto você está?",
  `apoio.ETAPAS`; a proteção contra violência mora aqui, decisão do autor).
  Hospitais e Carretas viraram recursos (lâminas próprias). Mama e colo reúnem
  prevenção, exame, diagnóstico e tratamento de cada câncer.
- **Divisão de trabalho (09/2026):** o ChatGPT cuida de
  `conversa.py`/`teste_conversa.py`; Claude cuida de `inteligencia.py`
  e do painel (o autor passou a Lia para o Claude). Pendências do
  chat para acompanhar o painel: trocar
  "valor pago pelo SUS" por "valor hospitalar registrado no SIH/SUS";
  trocar "Projeção exploratória" por "Projeção de tendência" nos
  textos de "onde ver"; usar `inteligencia.evidencias_planejamento`,
  `ficha_cancer`, `destaques_cancer` e `LINHAS_DE_ACAO` em vez das
  cópias locais (`sinais_de_atencao`, `LINHAS_DE_ACAO` em
  `conversa.py`), para chat e painel não divergirem; usar
  `inteligencia.cancer_de()` ("câncer colorretal", sem "de").
  Achados ao testar a caixa da Lia (09/2026), para `conversa.py`:
  "Quais cânceres estão aumentando?" responde só o câncer em foco
  (EVOLUCAO sem câncer citado deveria comparar todos); ano futuro
  além dos dados ("em 2030?") não cai em PROJECAO (só 2026-2028 são
  palavras-chave).
- **O DATASUS não oferece todos os meses (confirmado 23/09/2026;
  ver `docs/FONTE_DOS_DADOS.md`).** Faltam 35 dos 156 meses de
  competência do SIH/RD de SP (2013-2025), os mesmos nos 7 cânceres;
  só 2025 tem 12/12 (2018 só 6). **Não foi falha de download** (o autor
  sabia; `baixar_sih_sp.py` mostra "NÃO LISTADO pelo DATASUS"). Por
  mês, o crescimento é suave; o "salto de 2025" era só 2025 ter os 12
  meses. Regra do Escudo: a carga guarda `mes`; `carregar_serie` usa
  `ajustar_meses` -- para comparar anos, média dos meses disponíveis
  x 12 (colunas internacoes, obitos, valor_total, dias_permanencia);
  o registrado fica em `<coluna>_reg` e é o que entra nos totais do
  período (`resumo_doencas`, `ficha_cancer`, letalidade; use
  `registrado()` em qualquer soma nova). Meses por ano vêm do
  Estado. `anos_incompletos()` alimenta o aviso de confiabilidade, a
  nota da Lia e o marcador vazado na Evolução. Banco antigo sem `mes`:
  aviso para recarregar, sem ajuste. **Precisa rodar a carga de novo
  no Windows** para o ajuste valer. Efeito nos dados reais: 2025 deixa
  de ser atípico no Estado, colorretal 2023 deixa de ser fora do
  padrão, ritmos menores (mama 6,9% -> 5,3%), colo do útero vira
  alerta; mama 2019 (7 meses) aparece fora do padrão -- estimativa
  menos firme.
- **Coerência passado x projeção (09/2026):** 2025 ficou muito acima
  da reta em vários cânceres e a projeção de 2028 aparecia ABAIXO de
  2025 com "cresce X% ao ano". Agora a projeção sai da reta
  (`tendencia_no_periodo`, desenhada no gráfico), `leitura_ponta_projecao`
  explica quando último ano e projeção parecem se contradizer, e o
  futuro do radar é comparado com o nível da tendência, nunca com o
  último ano. `anos_fora_do_padrao` continua sem testar as pontas
  (aedda21); o último ano do ESTADO é avaliado por
  `ponta_fora_da_tendencia` (um passo, esperado >= MEDIA_PEQUENA), e
  o aviso "2025 em investigação" voltou. Para decidir 2025 de vez:
  `py etl\investigar_2025.py` (ANO_CMPT x DT_INTER, IDENT, N_AIH,
  MES_CMPT nos CSVs brutos) -- falta rodar no Windows.
- **Contagem em dobro de Rio Claro: confirmada e corrigida.** No
  banco real havia 1.668 internações de Rio Claro com origem
  RIO_CLARO e as mesmas 1.668 com origem SP (a pasta estadual já traz
  todas as cidades). **A carga agora lê SÓ os arquivos estaduais**
  (`MAPA` em `etl/carga_todas_bases.py` não tem mais as pastas
  `cancer_*_rio_claro`; se estiverem em `dados\`, são ignoradas com
  aviso, e falta de pasta estadual é avisada -- nunca volta a ler a
  da cidade). Toda linha tem `origem = 'SP'`; a cidade de residência
  está em `municipio`. Scripts de `analises/` passaram de
  `origem = 'RIO_CLARO'` para `municipio = 'RIO_CLARO'`. Teste:
  `etl/teste_carga_duplicidade.py`. Os arquivos de Rio Claro não
  precisam ser apagados (podem ficar guardados fora de `dados\`).
  Precisa rodar a carga + cadeia de novo no Windows.
- **`algoritimos/conversa.py`** (fora do painel desde que a caixa
  da Lia saiu; substituiu `chat_servico.py`). Entender (assunto por PONTUAÇÃO de palavras-
  chave, não "primeiro if que der match"; câncer por sinônimos com
  palavra inteira) -> calcular (fatos de `inteligencia.py`, nunca das
  13 tabelas antigas) -> explicar (Gemini via `ia_linguagem`; se
  falhar, resposta direta com os fatos). Perguntas de orçamento
  recebem sinais de atenção com evidência, nunca valores em R$.
  Testado por `teste_conversa.py`.
- Próximos passos combinados, nesta ordem: (1) no Windows, rodar a
  carga de novo (`py etl\carga_todas_bases.py`: grava o mês) e conferir
  com `py etl\validar_banco.py` que os 7 cânceres entraram (em
  24/09/2026 o banco do autor ficou só com colo do útero -- a carga
  provavelmente parou no 2º arquivo; falta ver a mensagem de erro);
  (2) população do IBGE para comparar cidades.
  **Carga robusta (24/09/2026):** a carga antiga apagava a tabela no 1º arquivo
  e parava no 2º que desse erro -- por isso o banco do autor ficou só com colo
  do útero. Agora ela lê e confere os 7 arquivos antes de gravar, um arquivo com
  problema fica de fora com o motivo no fim (os outros entram), a tabela nova é
  montada ao lado e só troca no fim, e o banco anterior vai para
  `banco\escudo_feminino_antes_da_carga.db`. `validar_banco.py` mostra
  internações por câncer (Estado e Rio Claro) e diz se falta algum. Teste:
  `etl/teste_carga_robusta.py`. Testes do sistema atual
  rodam no GitHub (`.github/workflows/testes.yml`).

## Notas de contexto do domínio

- Banco de dados: `banco/escudo_feminino.db` (SQLite). O caminho é
  calculado a partir da pasta do projeto (`RAIZ_PROJETO`), não fixo: o
  projeto pode ficar em qualquer pasta (hoje `C:\MISM2`). Painel e
  `algoritimos/` leem o `BANCO` de `configuracao_geografica.py`; os
  scripts de `etl/` calculam o mesmo caminho. O banco e a pasta `dados\`
  não vão para o GitHub: ao mudar o projeto de pasta, levar `banco\` e
  `dados\` junto (ou rodar a carga de novo).
- `pysus` só funciona no Python 3.12 do autor (`py -3.12`); o `py`
  padrão dele é 3.14.
