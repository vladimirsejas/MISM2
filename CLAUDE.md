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

## Uma pasta só (decisão do autor, 10/2026)

O autor usa **um único projeto: `C:\MISM2`**. Nunca sugerir nem criar outra
pasta, clone ou cópia no notebook dele (já houve `MISM2_visual` e pastas
duplicadas do ChatGPT, e foi uma bagunça). Fluxo de entrega: mudança pequena
e testada -> `main` -> ele faz `git pull` em `C:\MISM2` e abre o
`Abrir Escudo Feminino.bat`. A proteção é o histórico do Git (reverter um
commit), não cópia de pasta. Antes de qualquer instrução para o notebook,
pedir o estado real (`git branch --show-current` e `git status`): a
`C:\MISM2` dele já esteve numa branch do ChatGPT (`cnes-geografia-mism2-main`)
e o `git pull` não mostrava nada. O banco (`banco\`) nunca é tocado. **Não criar atalho `.bat` novo** (o autor já tem vários e pediu para não
multiplicar, 10/2026): rodar por comando (`py ...`) e usar os `.bat` que já existem.

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

**Pendência:** taxa por 100 mil mulheres e ranking entre municípios dependem da
população do IBGE (gráfico de funil, cidades semelhantes). **Comparar cidades
(10/2026, primeira versão, sem população):** na aba Investigar, a cidade escolhida
x outra (sugestão: a de número de internações mais parecido), só com o que não
depende do tamanho: parcela de cada câncer, letalidade hospitalar, permanência
média e ritmo de crescimento (`perfil_cidade`, `tabela_comparacao`,
`mix_comparacao`, `leitura_comparacao`, `cidades_parecidas`; teste
`algoritimos/teste_comparar.py`). Número absoluto aparece avisando que não compara
tamanhos.

## Painel novo (09/2026) — decisões combinadas com o autor

Depois do retorno da Secretaria da Mulher, o autor (com Claude e
ChatGPT) decidiu **reduzir** o Escudo: uma inteligência central com
poucas portas de entrada, não cinco sistemas. Regras:

- **Toda funcionalidade nova precisa responder uma pergunta que o
  Escudo ainda não responde.** Se não responder, não entra.
- **Cada informação tem uma casa só** no painel; não repetir números
  em várias telas.
- **Todo gráfico = pergunta (título) + gráfico + leitura em texto.**
- **Toda pergunta diz de quem são os números (decisão do autor, 10/2026).**
  `pergunta(texto, escopo, detalhe)` põe um selo: roxo "🌎 Todo o Estado de
  São Paulo" (não muda ao trocar de cidade) ou azul "📍 <cidade>" (muda).
  Motivo: com "Campinas" no topo, o gráfico do Estado parecia de Campinas.
  Pergunta nova sem escopo declarado não entra. Tabelas só mostram colunas
  que informam (sem colunas iguais em todas as linhas) e levam leitura.
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
- **Onde ser atendida (10/2026, substituiu a "Rede local" do ChatGPT).** **Unificada com o mapa (10/2026, decisão do autor: "menos que já seja o mais"):** uma página só, `dashboard/pages/onde_ser_atendida.py` + `algoritimos/onde_atendida.py` (teste `teste_onde_atendida.py`), que junta o CNES com o catálogo conferido de Rio Claro (`dados_geograficos/catalogo_servicos_rioclaro.json`, vindo do MISM3: telefone, horário, data de verificação e o apoio à mulher). A pessoa escolhe do que precisa (Posto de saúde, Exames e especialistas, Hospital, Urgência, Saúde mental, Apoio à mulher); cada lugar tem **Como chegar** (rota no Google Maps a partir de onde ela está) e **Ligar**. Sem o arquivo do CNES a página usa só o catálogo (nunca fica vazia). A página "Mapa de serviços" e o índice de CEP foram removidos (histórico do Git). Descrição original abaixo: Pergunta
  nova: "onde, na minha cidade, uma mulher procura atendimento?".
  `algoritimos/unidades_saude.py` lê o CNES (`banco\cnes\tbEstabelecimento*.csv`,
  fora do GitHub) em pedaços e devolve só as unidades ATIVAS da cidade: município pelo
  ENDEREÇO (CO_IBGE; o gestor só como plano B, e a página avisa), tipo em palavras
  (não o código), grupos (Posto ou UBS / Exames e especialistas / Hospitais /
  Urgência / Saúde mental / Outros), natureza pública x sem fins x privada, endereço,
  telefone, mapa (só coordenada que cai na cidade) e link de busca no mapa. A página
  (`dashboard/pages/onde_ser_atendida.py`, link "Onde ser atendida" no topo do painel)
  cruza com o banco: o selo "internações por câncer" do hospital é o que o SIH registrou
  (não mede qualidade). Cadastro não é vaga nem serviço aberto, e a página diz isso;
  nunca ranqueia unidades. Dos arquivos da pasta `banco\` só o `tbEstabelecimento` é
  usado: o CSV de CEP (o CNES já traz latitude/longitude) e os PDFs (cras, creas...) não.
  Conferir as colunas do arquivo real: `py algoritimos\unidades_saude.py`. Testes:
  `algoritimos/teste_unidades_saude.py` e `dashboard/teste_onde_atendida_tela.py`
  (CNES sintético; **não foi testado com o arquivo real**, que a nuvem não alcança).
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
  **Carretas (10/2026, pedido do autor, feito pelo Codex e auditado pelo Claude):** o itinerário
  mensal saiu do código (`ITINERARIO`, `carretas()`, `itinerario_vencido()` e o quadro "onde a
  carreta está agora" não existem mais): ele muda a cada ~15 dias e ficava desatualizado. No lugar,
  a lâmina Carretas, a porta Câncer de mama, a lâmina Rio Claro e a fala da Lia (`frase_carretas()`)
  mandam para o canal oficial (`URL_CARRETAS_POUPATEMPO` e `URL_CARRETAS_SP_POR_TODAS`), sem cidade
  nem data. **Conferido pelo autor no notebook (18/10/2026):** o botão "🏠 Início" do Apoio volta ao
  Panorama e os links das carretas funcionam (a nuvem não abre sites do governo, então isso só
  o autor podia confirmar; a busca na web só tinha confirmado o Poupatempo). A carreta do Hospital de Amor em Rio Claro (fev/2025, evento
  único) também saiu. **Boas-vindas do Apoio (Codex):** 4 entradas (Prevenção e exames, Meu exame
  deu alterado, Recebi diagnóstico de câncer, Não sei por onde começar); "Preciso de ajuda" não presume
  mais a etapa (`ap_etapa` começa vazio); os contadores do catálogo foram para "Sobre estas informações".
  Textos das leis mais precisos: os 30 dias valem quando câncer é a principal hipótese diagnóstica e
  há pedido médico fundamentado (Lei 13.896/2019); os 60 dias contam do laudo patológico (Lei
  12.732/2012). Pergunta de diagnóstico recente ("recebi o diagnóstico de câncer...") vai direto à etapa,
  sem a busca escolher hospital (`apoio_busca._diagnostico_recente`).
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
- **Escopo do Estado: atendimento em SP (autor, 10/2026).** O Estado do
  Escudo conta as internações nos hospitais de SP, inclusive de mulheres
  que moram em outro estado; a cidade continua por residência. A carga
  grava essas linhas com `municipio = 'OUTRO_ESTADO'` (código IBGE de
  residência mantido, `OUTRO_ESTADO` fora do catálogo e do seletor de
  cidades; `validar_banco.py` mostra a coluna `outro_estado`). Antes elas
  eram descartadas -- por isso o colorretal (94.005 registros, 2.664 de
  fora) ficava de fora do banco. `baixar_sih_sp.py` não filtra mais a
  residência e tem `--aceitar-lacunas-da-fonte` (troca os CSVs pelos
  meses que o DATASUS oferece; erro de download de verdade continua
  barrando; usa a pasta `_download_sih_sp_atendimento`). **Feito em
  08/10/2026:** os 7 cânceres foram baixados e carregados com a regra
  nova (464.340 registros; 17.991 de outros estados; Rio Claro 1.668,
  igual ao de antes). Os CSVs não vão para o GitHub (têm CEP, nascimento
  e nº da AIH; o `.gitignore` já bloqueia).
- **Fluxo de pacientes (10/2026, pedido do autor: "mulheres de outros
  estados vindo se tratar em SP é importantíssimo para gestores").** A
  carga guarda `uf_residencia`, `municipio_hospital` (MUNIC_MOV, que
  confere: cada CNES tem um único município), `cnes` e `car_int`
  (nunca CEP, nascimento ou nº da AIH; a correção dos códigos inválidos
  também entrou aqui). `inteligencia.py`: `carregar_fluxo`,
  `resumo_fluxo`, `evolucao_fluxo`, `ligacoes_fluxo`, `por_cancer_fluxo`,
  `leitura_fluxo`, `fluxo_da_cidade`, `leitura_cidade` (só descrevem; nada
  de causa; contam internações, não pessoas, e só enxergam hospitais de
  SP). Painel: seção no topo da aba **Investigar** (gráfico de fluxo
  estado -> município do hospital, parcela por ano, tabela por câncer e
  o bloco "quem é atendida nos hospitais da cidade e para onde vão as
  moradoras"). Banco de carga antiga (sem as colunas): a seção avisa para
  rodar a carga, sem quebrar. **Precisa rodar a carga de novo no Windows**
  (`py etl\carga_todas_bases.py`) para o banco ganhar as colunas. Testes:
  `algoritimos/teste_fluxo.py`, `etl/teste_carga_fluxo.py` e o cenário F
  de `dashboard/teste_painel.py`. Ainda NÃO está na Lia (caminho novo na
  árvore) nem tem aba própria; decidir com o autor. Na mama: 89% das
  moradoras de Rio Claro se tratam na cidade (saldo +35) e 87% das
  mulheres de outros estados são atendidas em Barretos.
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
  **Outras bases do PySUS (17/10/2026, o autor perguntou por que o Escudo só usa o SIH):** hoje só o SIH/RD vem do PySUS. Candidatas, cada
  uma respondendo uma pergunta que falta: população (taxa por 100 mil e ranking proporcional entre cidades: a pergunta que a Lia não soube
  responder no teste com pessoa), SIM (mortalidade real por município, dentro e fora do hospital), SIA (quimio, radio, mamografia e
  biópsia ambulatoriais: o maior ponto cego declarado) e CNES (mamógrafos e leitos). A nuvem não alcança o DATASUS nem o IBGE; antes
  de escrever cada ETL, rodar no notebook `py -3.12 etl\explorar_pysus.py` (não baixa nada) para ter os nomes reais das bases e grupos.
  Reconhecido em 17/10/2026 (SP, 2023): SIH/RD 11 arquivos; SIM/CID10 0 arquivos em 2023 (provável ano ainda não publicado: testar 2021);
  SIA/PA 36 (a, b, c por mês; volume enorme: para câncer preferir as APACs AQ e AR); CNES EQ, LT e ST 12 cada. **População:**
  `py etl\baixar_populacao.py` (IBGE, Censo 2022, tabela 9514; descobre os códigos pelo nome; grava `populacao_mulheres`; teste
  `etl/teste_baixar_populacao.py`; `--reconhecer` só mostra a tabela). **Usada (17/10/2026):** `inteligencia.ranking_municipios`/`leitura_ranking` (internações
  por 100 mil mulheres, média por ano, só cidades com 20 mil mulheres ou mais, cruzando o código de residência pelos 6 primeiros dígitos;
  os meses que o DATASUS não oferece são compensados) e a Lia responde "quais cidades têm mais ... proporcionalmente?" com o ranking e a
  posição da cidade do painel (`Contexto.ranking`, `rankings_por_100_mil` em `app.py`); sem a tabela no banco ela diz o que falta
  (`SEM_POPULACAO`). Testes: `teste_inteligencia.py` (N) e `teste_assistente.py` (7e). Falta conferir com os dados reais do notebook.
  **Quimio e radio ambulatoriais (SIA, APACs AQ e AR; 17/10/2026):** `py -3.12 etl\baixar_sia_oncologia.py` (só 2023; `--anos 2013-2025` para
  tudo) grava SÓ agregados em `oncologia_ambulatorial` (modalidade, ano, mes, codigo_residencia, tipo_cancer, faixa, estadiamento,
  raca_cor, apacs, pacientes; nenhum cartão SUS, CEP ou nascimento) e imprime o perfil dos códigos reais; teste
  `etl/teste_baixar_sia_oncologia.py`. As colunas reais (AP_SEXO, AP_CIDPRI, AP_MUNPCN, AP_NUIDADE, AP_RACACOR, AQ_ESTADI/AR_ESTADI) vieram
  do `explorar_pysus --amostra`; falta usar a tabela em `inteligencia.py` e na Lia depois de conferir o perfil. O SIM se oferece sem grupo
  (`Mortalidade_Geral_ANO` e `DO<UF><ANO>`). CNES EQ (TIPEQUIP, CODEQUIP, QT_EXIST) e LT (TP_LEITO, CODLEITO, QT_SUS) têm as colunas.
  **Tudo de uma vez (17/10/2026, o autor decidiu baixar tudo):** UM comando, sem `.bat` novo: `py -3.12 etl\carregar_tudo_pysus.py`
  (`--so populacao|sia|sim|cnes` para uma etapa). Cada etapa é isolada (uma falha não derruba as outras) e o fim mostra o resumo e os
  blocos PERFIL, que o autor cola no chat para conferir códigos (sexo, raça/cor, estadiamento, equipamentos). ETLs: `baixar_sia_oncologia.py`
  (`oncologia_ambulatorial`, 2013-2025), `baixar_sim_obitos.py` (`obitos_sim`: ano, residência, câncer, faixa, local do óbito, raça/cor;
  usa `DOSP<ano>`) e `baixar_cnes_capacidade.py` (`cnes_equipamentos` e `cnes_leitos`, dezembro de cada ano, **códigos crus**: o
  Escudo AINDA NÃO nomeia "mamógrafo" nem "leito oncológico", falta o dicionário do CNES, então o CNES não entrou na Lia). Raça/cor
  tem códigos diferentes no SIA (03 parda, 04 amarela) e no SIM (4 parda, 3 amarela): `alerta_raca` avisa no PERFIL se parecerem
  trocados. Só agregados vão ao banco. Teste: `etl/teste_baixar_sim_cnes.py` (PySUS simulado). **Na Lia:** dois assuntos novos,
  `tratamento` (quimio/radio por APAC, nunca "mulheres"; estadiamento e raça/cor só informados x não, sem nomear estágio) e
  `mortalidade_real` (SIM x SIH: "não se subtraem"), com `inteligencia.resumo_/leitura_tratamento` e `resumo_/leitura_mortalidade`.
  **Entram só por gatilho** (`entendimento._por_gatilho`), não pelo índice: pondo as frases no índice, 6 perguntas dos gabaritos
  mudavam de resposta (medido); por gatilho as medições ficaram idênticas (80/47/33). Sem as tabelas, a Lia diz o que falta e como
  trazer. Teste 7g de `teste_assistente.py`. **Hospital de câncer + cidade citada (teste humano, 17/10/2026, Catanduva):**
  `assistente._hospital_de_cancer`: hospital de câncer pelo SUS não se escolhe por proximidade nem pela cidade do painel (Rio Claro é o
  centro do trabalho, os hospitais ficam fora); a cidade que a pessoa diz ("moro em X", "perto de X") vale mais que a do painel, mostra
  os hospitais do catálogo ligados a ela, e sem eles aponta a lâmina Hospitais no Estado e como descobrir a DRS (**o Escudo não tem a
  lista cidade -> região e prefere não chutar**). Teste 7f. **Streamlit:** `use_container_width` foi trocado por `width="stretch"`.
  **Localização e distância até hospitais de câncer (17/10/2026, ideia do autor):** `etl/baixar_centroides.py` (etapa `geo` do
  `carregar_tudo_pysus.py`) baixa a malha dos municípios de SP da API do IBGE em GeoJSON e calcula o PONTO CENTRAL de cada cidade em
  Python puro (sem geopandas/geobr; `geobr` fica só como plano B citado na mensagem de erro), tabela `municipios_localizacao`
  (645 linhas, dado público); confere que o centro de Rio Claro cai no lugar certo antes de gravar. `algoritimos/localizacao.py`:
  `distancia_km` (haversine) e `hospitais_proximos` (hospitais da lâmina Hospitais no Estado + Hospital de Amor, até 2 por cidade;
  cidade fora da tabela = nenhuma distância, nunca posição inventada). A Lia diz sempre que é **linha reta entre centros de cidades**,
  não rota nem tempo, e que quem decide é a regulação (CROSS). Cidade que já tem hospital no catálogo lista o dela, sem km. Teste:
  `etl/teste_baixar_centroides.py` e 7h de `teste_assistente.py`. **Rodado no notebook em 17/10/2026 com a API real do IBGE:** 645
  municípios gravados, centro de Rio Claro em (-22,373; -47,580), nomes de campo da API conferidos. **Segurança (teste humano, 17/10/2026):** "meu marido tá me agredindo, me ajuda" virava
  pedido de ajuda genérico, sem 190/180; o padrão de violência agora pega gerúndio, voz passiva e "violência doméstica" (não pega
  "violência sexual" sozinha: essa é consulta do catálogo do Apoio). Testes em `teste_entendimento.py`.
  **Polos de tratamento (17/10/2026, observação do autor: "tem diferença dos casos da população com os casos tratados nas cidades que
  têm hospitais de referência"):** o ranking por 100 mil mulheres conta onde a mulher MORA; cidade com hospital de referência (Barretos,
  Jaú, Ribeirão Preto) trata muito mais do que tem. `inteligencia.ranking_atendimento`/`leitura_atendimento`: cidades por internações nos
  hospitais DELAS (município do hospital), com % de moradoras da cidade, de outras cidades de SP e de outros estados, e a **razão** entre o
  que o hospital trata e o que as moradoras da cidade internam em qualquer hospital (mínimo de 100 internações). A fala do ranking por
  população agora diz "conta onde a mulher mora; quem vem de fora se tratar não aumenta a cidade do hospital" e oferece o botão "Cidades
  que mais tratam"; o inverso também. Entra por gatilho (`GATILHO_POLOS`, só frases inequívocas de ranking de cidades: "vem de fora
  tratar" é o assunto `fluxo` que já existia e "centro de referência" aparece em consultas do Apoio). Caminho `lia.polos`, `Contexto.atendimento`.
  Testes: O em `teste_inteligencia.py` e 7i em `teste_assistente.py`. **Conferido pelo autor com o banco real (18/10/2026):** os polos
  de tratamento responderam como esperado; o ranking por 100 mil mulheres também já tinha respondido com o banco real (17/10/2026).
  **Carga das bases novas no notebook (17/10/2026):** SIA (29 min) e SIM (3 min) entraram; o CNES falhou com "database is locked" (outro
  programa, provavelmente o painel, estava com o banco aberto): as gravações dos ETLs agora esperam até 2 min (`timeout=120`). Fechar o
  painel durante a carga continua sendo o mais seguro. `py etl\validar_bases_novas.py` só LÊ o banco (modo somente leitura) e mostra o
  que entrou em cada tabela, os anos que faltam, Rio Claro e se raça/cor parece trocada; teste `etl/teste_validar_bases_novas.py`.
  **Carga robusta (24/09/2026):** a carga antiga apagava a tabela no 1º arquivo
  e parava no 2º que desse erro -- por isso o banco do autor ficou só com colo
  do útero. Agora ela lê e confere os 7 arquivos antes de gravar, um arquivo com
  problema fica de fora com o motivo no fim (os outros entram), a tabela nova é
  montada ao lado e só troca no fim, e o banco anterior vai para
  `banco\escudo_feminino_antes_da_carga.db`. `validar_banco.py` mostra
  internações por câncer (Estado e Rio Claro) e diz se falta algum. Teste:
  `etl/teste_carga_robusta.py`. Testes do sistema atual
  rodam no GitHub (`.github/workflows/testes.yml`).

- **Revisão da aba Investigar (19/10/2026, o autor achou três blocos "confusos, limitados, que não servem para nada").**
  (1) A tabela "Em quais cânceres a parcela de fora é maior?" (7 linhas, sem leitura, números viravam texto) saiu: no lugar,
  a tabela completa e pesquisável do fluxo (`inteligencia.tabela_fluxo`, `filtrar_tabela_fluxo`, `agrupar_tabela_fluxo`,
  `parcela_fora_por_cancer`, `leitura_tabela_fluxo`): uma linha por câncer x estado de origem x hospital (um ano por linha
  opcional), filtros de câncer, estado e anos, busca sem acento/maiúscula em hospital, município, estado, câncer e CNES, ordenação
  por coluna, download CSV e leitura que ainda responde a pergunta antiga (parcela de fora de cada câncer no período).
  `por_cancer_fluxo` continua em `inteligencia.py` (tem teste), mas o painel não a usa mais. (2) O bloco "Em que anos algum câncer saiu do padrão?" saiu da
  aba Investigar (autor: "dado confuso que não ajuda em nada"; régua: um gestor ou uma aluna de 3º semestre sabe o que fazer com
  isso? Não, e vários anos marcados vinham só de meses ausentes na fonte). A informação continua em UMA casa: a camada "Destacar
  anos fora do padrão" do gráfico da aba Evolução, e a Lia conta em palavras quando perguntada (o botão "Anos fora do padrão"
  agora leva à Evolução com a camada ligada; `anos_fora_todos` fica só para a Lia). **Passeio:** a parada 3 deixou de ser "Algum
  ano fora do padrão?" (repetiria a Evolução) e virou "De onde vêm as pacientes de outros estados?" (caminho `fluxo`, aba
  Investigar), mantendo uma parada por aba. Avisos de confiabilidade agora dizem "Poucos casos" no lugar de "Números pequenos".
  O bloco "Quem é atendida nos hospitais de <cidade>" virou duas perguntas separadas (quem é atendida AQUI x onde as MORADORAS
  são atendidas), com a lista das cidades de destino e uma frase de resumo no lugar do "saldo". (3) Gráfico do hospital por
  ano: ano sem registro ganha um x laranja com o mouse dizendo quantos meses a fonte tinha, a leitura diz onde caem as lacunas e que
  o banco NÃO guarda o motivo (`_frases_anos_sem_registro`), e a caixa "Por que alguns anos ficam sem barra?" lista o que dá
  para afirmar (meses ausentes na fonte, atendimento fora do SIH ou sob outro CNES, poucos casos) sem atribuir causa. Testes:
  `teste_fluxo.py`, `teste_hospital.py` e os cenários F e H de `dashboard/teste_painel.py`. **Não foi visto no navegador real nem com
  o banco real** (a nuvem não tem o banco): conferir no notebook como a tabela se comporta com ~18 mil internações de fora.
  **Navegação (19/10/2026, autor: "falta o botão home e a indicação de onde você está"):** o botão "🏠 Início" do painel agora fica
  SEMPRE ativo (antes desligava no Panorama) e uma faixa "📍 Você está em: <aba> · <cidade>" aparece sob as abas (`escudo-voce-esta`);
  a aba aberta também ganha fundo roxo no seletor. As páginas Onde ser atendida e Hospitais habilitados ganharam a mesma faixa e o
  Início delas marca `aba = "Panorama"` antes de trocar de página. **Bloco da cidade:** a coluna "2. Onde as moradoras de <cidade> são
  atendidas" sempre aparece; sem o município do hospital (`moradoras_sem_hospital` em `fluxo_da_cidade`) ou sem internações de
  moradoras, mostra o aviso "Este dado não existe para <cidade>" e a leitura diz o mesmo. A tabela de destinos agora fica dentro da coluna. **Depois (19/10/2026, autor: "ficou muito confuso, crie a opção de ver quando as moradoras são atendidas fora e quando as de fora são atendidas aqui"):** as duas colunas viraram um seletor (`fluxo_visao`: "Moradoras atendidas em cidades de fora" x "Mulheres de fora da cidade atendidas na cidade"), mostrando uma visão por vez, cada uma com sua leitura (`inteligencia.leitura_cidade_visao`). A faixa "Você está em" ficou roxa e grande.

- **Alcance do banco (19/10/2026, autor: "a Lia não sabe os dados que ela mesma tem: as doenças, o número de cidades, as cidades; é inaceitável").** `inteligencia.alcance_dados(conexao)` lê do banco (nada escrito à mão) o total de internações, o período, os cânceres com a contagem de cada um, as cidades de SP (pelo `municipio` de residência, com o nome do catálogo), as internações de mulheres de outros estados (e de quais UFs), os estabelecimentos e quais outras bases foram carregadas (população, SIA, SIM, posição dos municípios, CNES); `leitura_alcance` conta isso em palavras e diz o que o Escudo NÃO tem (casos novos, plano de saúde, causa). A Lia ganhou o caminho `alcance` ("O que há nos dados?", botão na lateral) e a caixa entende "quais doenças você tem?", "quantas cidades?", "que dados você tem?", "qual o alcance dos dados?" (`entendimento.GATILHO_ALCANCE`, só por gatilho, com `EXCLUI_ALCANCE` para ranking/tendência/sintoma; vem antes do `_pede_comparar_canceres`, para "quais cânceres vocês acompanham?" não virar ranking). Texto fixo, sem IA (`assistente`: `alcance` fora de `SO_DADOS`). `Contexto.alcance` vem de `alcance_do_banco()` em `app.py`; sem ele a Lia diz que não conseguiu ler o banco. Medições do entendimento idênticas (80/47/33, 0 erros). Testes: `teste_alcance.py` (no GitHub Actions) e 7j de `teste_assistente.py`. A lista das cidades fica no seletor do painel (são 645); a Lia diz o total e as de mais internações.

## Pergunte à Lia — a IA do Escudo (10/2026, pedido do autor)

Requisito do trabalho (Fatec): o projeto precisa ter IA de verdade, e o autor
quis a caixa de perguntas de volta, **junto da Lia, sem mexer no que já existia**.
Documento completo, com a avaliação e os limites: `docs/IA_DO_ESCUDO.md`.
Fluxo: pergunta -> `entendimento.py` (qual assunto, qual câncer) -> `assistente.py`
(reaproveita `lia.responder`: mesmos números dos botões; monta o que a Lia não tinha)
-> Gemini redige (`ia_linguagem.redigir_resposta`) -> conferência -> balão da Lia.
- `algoritimos/entendimento.py`: 21 assuntos fechados com vocabulário popular escrito à
  mão; busca por palavras (radicais) + letras (aguenta erro de digitação), sem
  dependências novas; câncer por sinônimo popular ("seio", "preventivo"); ano futuro
  = previsão; segurança PRIMEIRO (violência, suicídio, emergência -> 190/180/188/192);
  contexto mínimo ("e no estado?", "e o de colo do útero?"); o Gemini só entra como
  segunda chance, escolhendo numa lista fechada, e o que ele devolve é conferido. **Regra de concordância
  (17/10/2026, enviada ao `main` pelos números do `algoritimos/comparar_regras.py`, ver `docs/IA_DO_ESCUDO.md` 6b):** a escolha do Gemini só vira resposta direta se estiver entre os palpites da busca local; se só
  o Gemini apontou (`origem = "gemini_sem_apoio"`), vira palpite para a pessoa confirmar (id válido ainda pode ser o
  assunto errado). `py algoritimos\comparar_regras.py` compara as duas regras com as mesmas respostas do Gemini.
  **Conversa (17/10/2026, `origem` "explicar" e "composta"):** "me explica isso melhor", "não entendi", "como assim?" retomam a
  resposta de dados anterior (a memória guarda assunto e câncer) com `assistente.EXPLICACAO_SIMPLES` + os mesmos números +
  `COMO_LER`, texto fixo, sem IA; sem resposta anterior, ou depois de assunto de texto fixo, continua pedindo/oferecendo palpites; frase
  com assunto próprio ("explica como calculam a tendência") nunca é sequestrada (`PALAVRAS_DE_EXPLICAR`). Pedido composto só nos pares
  seguros `PARES_SEGUROS` (evolução+futuro, óbitos+valores, evolução+estado) responde os dois (`Entendimento.tambem`); outras
  combinações seguem como palpites. Efeito medido: conjunto final 31 -> 33 diretas de 35, 0 erros. Ideia do Codex/ChatGPT.
  Modelo da cidade: o nome da cidade do painel é ignorado; outra cidade = comparar.
- `algoritimos/assistente.py`: respostas. Gemini só reescreve respostas de DADOS; segurança,
  sintoma, apoio, onde ser atendida, causa e "sem dados" são texto fixo. Todo texto da IA é
  conferido (`conferir`): número que não está nos cálculos, "vai ficar/aumentar" ou explicação
  de causa -> descartado e a resposta direta da Lia aparece. Sem chave/rede/cota: resposta direta.
- `inteligencia.py` (seção "PREVISÃO COM VALIDAÇÃO"): 5 modelos pequenos, escolhidos por
  backtest (treina até t, prevê t+1..t+3, anda um ano), faixa pelo erro medido, sempre
  comparada com "repetir o último ano"; sem anos suficientes, não prevê. É projeção de
  tendência de internações, nunca previsão de casos novos. `previsao_todos` ordena por variação.
- `ia_linguagem.py`: `MODELO` vem de `GEMINI_MODEL` no `.env` (padrão `gemini-3.8-flash`, **confirmado com a
  chave do autor em 17/10/2026**: `testar_gemini.py` deu 6 de 6 passos, o modelo existe e o texto redigido passou na conferência;
  uma chamada simples levou 6,7 s); timeout; `classificar_pergunta`; `redigir_resposta`.
- Painel (`dashboard/app.py`): caixa na lateral logo abaixo do balão (chaves `caixa_*`, não
  `lia_*`: o teste do painel trata `lia_*` como botão da árvore). A resposta entra no balão da Lia
  (`RespostaIA` herda de `Resposta`), o painel vai ao gráfico, e o balão mostra a pergunta, o selo
  (IA ou "sem IA"), a fonte e, se a IA redigiu, "O que o Escudo calculou". Limite de 40 perguntas
  com IA por sessão. **O texto da pergunta nunca é gravado** (10/2026, privacidade): `conversa.registrar_pergunta(banco, assunto)` só conta o assunto em `perguntas_usuarios`; relato de violência/sintoma nem isso.
- Regras que valem para qualquer mudança aqui: nunca "vai"/"deve ficar" (só "a tendência aponta");
  nada de causa; nada de orçamento; texto de IA nunca vai a segurança/sintoma; gabarito em 3 conjuntos
  (`gabarito_perguntas.json`): ajustar regras olhando só o desenvolvimento, e NÃO reaproveitar o
  conjunto "final" (já foi medido e consertado) -- criar um novo conjunto às cegas para medir de novo.
- **O que a nuvem NÃO comprovou (só o autor, no Windows):** o Gemini já passou no `py algoritimos\testar_gemini.py`
  (17/10/2026, 6 de 6); `py algoritimos\teste_entendimento.py --com-gemini` também foi medido (17/10/2026, regra em que o
  Gemini sozinho responde direto): entendeu direto **91/91** (desenvolvimento), **62/62** (teste) e **35/35** (final), 0 respostas
  erradas, contra 80, 47 e 31 só com as regras; o Gemini também recusou todo o fora do assunto do teste (4/4). Ressalvas: perguntas
  escritas pela equipe (o "final" já não é independente) e o Gemini não é determinístico mesmo com temperatura 0. **O painel com o banco real
  também passou (17/10/2026, `py dashboard\teste_painel_banco_real.py`):** 464.340 internações, 7 cânceres, 5 abas sem erro e 3 perguntas
  à Lia com o Gemini real, todas entendidas e redigidas pela IA com o texto aprovado na conferência. `py algoritimos\comparar_regras.py` com o
  Gemini real (57 consultas): a regra antiga errou 2 respostas diretas e a nova 1 (evitou 1; custo 10 confirmações); o erro que sobra,
  "qual desses cânceres tá lotando mais o hospital?" -> `tempo`, vem de o Gemini escolher mal entre candidatos que a busca local já
  tinha (defeito conhecido, não corrigido de propósito para não contaminar o conjunto final). Os testes na nuvem
  usam a base pública de Rio Claro e um Gemini simulado. Testes: `teste_previsao.py`,
  `teste_entendimento.py`, `teste_assistente.py` e o cenário I de `dashboard/teste_painel.py`.
- **Pergunte à Lia no Apoio à mulher (10/2026, enviada ao `main` em 17/10/2026 com o OK do autor; ainda
  não vista por ele no notebook):** `algoritimos/apoio_busca.py` + caixa na lateral de
  `dashboard/pages/apoio.py` (chaves `caixa_ap_*`). Aqui quem pergunta PROCURA cuidado, então: **nenhuma IA
  escreve sobre serviço** (o texto é do catálogo conferido, com aviso e link oficial); o motor só escolhe o
  item (mesmo `entendimento.Indice`, agora com universo próprio: palavras + letras sobre os 81 itens); com
  dúvida mostra até 3 candidatos em botões; o Gemini (se ligado) só escolhe uma PORTA ou LÂMINA numa lista
  fechada; segurança e sintoma = texto fixo; **as perguntas do Apoio NÃO são gravadas** (nem no banco).
  Gabarito `gabarito_apoio.json` (86 perguntas, desenvolvimento e final); testes `teste_apoio_busca.py` e
  o cenário F de `dashboard/teste_apoio_tela.py`. O conjunto final já foi medido e corrigido: para medir de
  novo, escrever um conjunto novo às cegas. O Gemini real só foi provado no teste da caixa do painel principal, não no Apoio (lá ele só escolhe porta).
- **Ajustes do Apoio (Codex, 18/10/2026, auditados pelo Claude e enviados ao `main`):** jornada do diagnóstico numerada, com "se a resposta demorar" (itens de regulação); a Lia avisa quando a resposta é de outra aba e oferece "Falar sobre <aba>"; **Gemini no Apoio desligado por padrão** (toggle `caixa_ap_gemini_ativo`, só classifica o assunto, nunca escreve; limite de 40 conta toda chamada); 17 atalhos "Assuntos" sem IA; a referência histórica da carreta em Rio Claro saiu. O `teste_painel.py` falhou no notebook do Codex por `MemoryError` do ambiente dele e passou na nuvem.
- **Cobertura por tipo de câncer no Apoio (10/2026, o autor achou que o Apoio girava em torno do câncer de mama; relatório em
  `docs/APOIO_COBERTURA_ONCOLOGICA.md`):** porta nova **Outros cânceres** na MESMA lâmina "Encontre um caminho" (as 8 portas de antes
  seguem, na ordem), com um cartão por câncer (intestino, ovário, pele, pulmão, tireoide, corpo do útero/endométrio) e o das páginas do INCA
  para tipos fora do guia. Item ganhou `cancer` (específico de quais cânceres; vazio = serve a todos) e `topicos`. **Trava na busca**
  (`apoio_busca.tipos_citados`, `buscar(..., tipos=)`): quem cita um câncer nunca vê conteúdo específico de outro; dois cânceres ou
  "câncer de útero" viram pergunta de volta; câncer fora do guia diz isso e aponta o INCA; palavra ambígua sozinha ("caroço",
  "sangramento") pergunta onde; sintoma com pista mostra o texto fixo + botão dos sinais; "e os sinais?" segue o câncer em foco
  (`RespostaApoio.tipo_cancer`, só memória da sessão). **Os seis cartões estão "a confirmar": as páginas do INCA não abrem na
  nuvem; o texto veio de conhecimento geral + busca e NÃO traz idade nem intervalo de rastreamento.** Conferir no Windows e
  tirar a marca. Teste: `algoritimos/teste_apoio_cancer.py` + `gabarito_apoio_cancer.json` (às cegas: 1ª medição 36/40 e
  25/28, depois das correções 40/40; já não é independente). O Gemini do Apoio segue só com dublê (API real não testada).
- **Contexto temporário da caixa do Apoio (Codex, 18/10/2026, auditado e juntado pelo Claude):** "e agora?", "estou com medo", "não entendi" retomam o item ou a etapa da resposta anterior e pedem
  o detalhe (`tipo = "esclarecimento"`, texto do catálogo, sem inventar o próximo passo). A sessão guarda só um token validado no catálogo
  (`caixa_ap_contexto`, "item:id" / "etapa:id"), nunca o relato; clicar, voltar, trocar de aba ou de atalho limpa. **Dois contextos convivem**
  em `responder_pergunta`: `contexto` (token do Codex) e `cancer_em_foco` (o câncer da resposta, para "e os sinais?"). Gemini não recebe histórico.
  Testes: `teste_conversa_apoio.py` e `dashboard/teste_conversa_apoio_tela.py` (regressão, não amostra independente).
- **"Meu exame deu alteração" (autor, 19/10/2026: "não ajuda em nada, a mulher em desespero deve ir no mínimo para a UBS do bairro, não para regra e lei"; e "preventivo alterado" e "mamografia alterada" não servem para uma mulher assustada).** A etapa `alterado` (`apoio.ETAPAS`) agora é acolhedora e prática: um exame alterado não é diagnóstico, levar o laudo à UBS/USF do bairro e dizer "meu exame deu alterado", Cadu (0800 019 0505) ou o botão "Unidades, telefones e como chegar" se não sabe a unidade; os prazos legais ficam por último, em uma frase. Itens mostrados: só `rc_unidades` e `rc_cadu_agendamento` (sem lei, sem BI-RADS, sem porta Diagnóstico). Na caixa, `apoio_busca._exame_alterado_generico` manda "meu exame/mamografia/preventivo/papanicolau deu alterado" para essa etapa (texto fixo); quem pergunta pelo termo técnico (BI-RADS, colposcopia, biópsia) continua indo ao cartão. **Depois (19/10/2026, autor: "mamografia alterada e colposcopia continuam dando resultado de regras... não vejo necessidade desses dois itens"): os cartões `mamografia_alterada` (BI-RADS) e `preventivo_alterado` (colposcopia/biópsia) SAÍRAM do catálogo.** Mamografia/preventivo alterado, BI-RADS e colposcopia vão à etapa `alterado` (UBS primeiro), antes do ramo de sintoma; biópsia, HPV, colonoscopia, sangue e PSA seguem o caminho próprio. Gabaritos: 4 perguntas do `gabarito_apoio.json` e 1 do `gabarito_apoio_cancer.json` passaram a esperar `etapa`. Testes ajustados: `teste_apoio_busca.py`, `teste_apoio_cancer.py` (D16), `dashboard/teste_apoio_tela.py` (C).
- **Vocabulário (autor, 18/10/2026): a usuária nunca lê "lâmina".** Hospitais no Estado, Carretas, Rio Claro e Barretos são **áreas**. "Lâmina" continua só como termo
  interno (código, comentários, nomes de teste, `LAMINAS`); texto de cartão, botão, fala da Lia e página "Sobre" diz "área". Teste: `teste_apoio.py`.
- **"O que você sabe responder?" (autor, 18/10/2026):** a caixa do Apoio explica, em texto fixo montado do catálogo (sem IA, `tipo = "sobre_a_lia"`,
  `apoio_busca.responder_o_que_sei`), os assuntos que o guia cobre, os tipos de câncer, o que a Lia NÃO faz (diagnosticar, indicar remédio, garantir vaga) e o 192,
  com as portas em botões. Só pergunta curta sobre a própria Lia e sem câncer nomeado (não sequestra pergunta de conteúdo; medido nos dois gabaritos do Apoio).
  Uma linha sob a caixa avisa a pergunta. Testes: H em `teste_apoio_cancer.py` e F em `dashboard/teste_apoio_tela.py`. **Perguntas continuam sem ser gravadas**
  (contar o que mais perguntam foi oferecido e NÃO escolhido; mudaria a regra de privacidade).
- **Jornada do exame de intestino e ICESP (autor anexou fontes oficiais, 18/10/2026):** a notícia do INCA de 21/05/2026 confirma o **FIT** como exame de
  referência no SUS para 50 a 75 anos **sem sintomas** (kit em casa; positivo leva a exames complementares; colonoscopia = padrão-ouro). Cartão novo
  `jornada_exame_intestino` (6 passos) e `cancer_intestino` com o rastreamento confirmado; **intervalo entre testes e oferta em Rio Claro NÃO estão confirmados**
  (a página não traz) e o catálogo não afirma. ICESP com as 4 unidades. A busca separa pedido de caminho ("onde faço colonoscopia pelo SUS?" -> jornada) de visão geral
  ("o que é o FIT?" -> cartão do câncer) (`apoio.JORNADA_DO_TIPO`, `apoio_busca._PEDE_CAMINHO`). A lista de centros sugerida pelo autor ficou **triada, não cadastrada**
  (sem fonte; ver `docs/APOIO_COBERTURA_ONCOLOGICA.md`). Teste: seção I de `teste_apoio_cancer.py` (o C4 passou a aceitar "50 a 75 anos" só no intestino).
- **CNES dos hospitais de referência (autor, 18/10/2026): conferidos com o banco real.** Uma lista de IA trouxe 8 CNES; `select` no banco do autor: **7 certos** (ICESP 6123740, A.C.Camargo
  2077531, Inst. do Câncer Arnaldo Vieira de Carvalho 2080125, H. Estadual Mário Covas 2080273, Amaral Carvalho 2083086, HC Unicamp 2079798, HC FAEPA Ribeirão Preto 2082187; nome oficial e
  município do hospital batem) e **1 errado: 9662561 (Hospital de Amor) não existe no banco**. Regra: CNES só entra no catálogo depois de conferido no banco (`hospitais` + `internacoes`);
  nunca de lista de terceiros. Ferramenta só de leitura: `py etl\listar_hospitais_por_cidade.py [cidades]` (top hospitais por internações de câncer, com CNES e nome oficial); teste
  `etl/teste_listar_hospitais_por_cidade.py`. **Hospital de Amor = Fundação Pio XII Barretos, CNES 2090236** (37.974 internações; o 9662561 da lista de IA não existe). O catálogo do Apoio guarda o CNES conferido de 5 hospitais (`apoio._CNES_CONFERIDOS`: ICESP, Amaral Carvalho, HC Unicamp, HC Ribeirão Preto, Hospital de Amor, Hospital Regional do Câncer de Presidente Prudente 7400926, Santa Casa de Rio Claro 2082888), só como metadado (o cartão não o mostra; a página do Apoio não abre o banco).
- **Links dos cartões (autor, 18/10/2026): "o INCA ajuda sim, mas cada página fala de uma doença e precisamos de mais".** O botão principal dos cartões de câncer da porta Outros
  cânceres continua sendo o do INCA; ao lado entram **4 páginas de serviço** que a mulher doente usa (unidades de saúde e Cadu de Rio Claro, como ser atendida num hospital de câncer, lista
  oficial de hospitais do SUS) -- campo `mais_links` do item, montado de `_MAIS_PARA_QUEM_ESTA_DOENTE` a partir dos próprios cartões de serviço (um endereço, uma casa só), e mostrado na página e
  na fala da Lia ("Outras páginas que ajudam"). Os cartões de câncer também levam a agendar (Cadu), "recebi o diagnóstico", como chegar ao hospital e direitos (`_o_que_fazer`).
  **Os links do INCA "versao-para-populacao" (ovário, pele, pulmão, tireoide, corpo do útero) vieram de um texto de IA e NUNCA foram abertos; o do intestino foi trocado pela notícia do FIT
  (única que o autor anexou).** Para conferir TODOS os links: `py algoritimos\conferir_links.py` no notebook (diz OK / REDIRECIONOU para outra página / ERRO); teste `teste_conferir_links.py`.
  **Conferidor rodado no notebook (18/10/2026): 68 OK, 8 redirecionaram, 13 com erro; 5 links corrigidos pelo endereço novo, 5 cartões marcados "a confirmar" (Prudente, Botucatu, Ribeirão agendamento, AMEs, AME Rio Claro); o conferidor ganhou a classe AVISO (certificado não verificável) e tempo de 60 s com nova tentativa.**
  **2ª rodada do conferidor (18/10/2026): 78 OK, 1 redirecionou (vacina HPV, notícia pedia login; trocada pela página "HPV" do Ministério, ainda não reconferida), 9 avisos de certificado (páginas abrem: FOSP, CAISM, HC Ribeirão, Santa Casa São Carlos), 0 erros.** Cartão de Ribeirão (404) saiu; colo do útero aponta para a BVS; AMEs e AME Rio Claro com os endereços que o autor passou.
  TFD agora abre a Portaria SAS/MS 55/1999 (e o "50 km", que a fonte não confirma, saiu).
- **Glossário da Lia (autor, 18/10/2026: "o que são APACs?" -- a Lia respondia "foge do que sei", e "qual o preço da diária?" devolvia o total de valores; "inaceitável").** `algoritimos/glossario.py` (teste `teste_glossario.py`, no GitHub Actions): ~30 termos do painel com definição e "No Escudo" (o que ele usa e o que NÃO calcula): APAC, SIA, SIM, CNES, CID, valor hospitalar registrado, diária (o Escudo não calcula o preço da diária), dias de permanência, letalidade, óbito na internação, projeção de tendência, ano fora do padrão, ritmo, meses ausentes, residência x hospital, UNACON/CACON, RRAS/DRS, regulação, UBS/USF, estadiamento, SUS, IBGE, INCA, leito, teste de acerto. **Texto fixo, a IA não improvisa definição.** Entra por gatilho em `entendimento.compreender` (assunto `glossario`, `Entendimento.termos`), como tratamento/polos, depois de segurança e saudação: só quando a pergunta pede o significado ("o que é/são/significa/quer dizer", "qual a diferença entre", "qual o preço da diária") ou é só uma SIGLA ("APAC", "UNACON"); expressões como "anos fora do padrão" ou "permanência média" sozinhas continuam sendo pergunta de dados, e AIH/SIH/internação/caso novo/incidência/DATASUS continuam no assunto `metodo`. **Medições do entendimento ficaram idênticas (80/47/33 diretas), 0 erros.** A definição de APAC segue o Instituto Oncoguia (13/07/2026, PDF que o autor enviou): "Autorização de Procedimento Ambulatorial", registro de atendimentos e tratamentos sem internação, no SIA; mencionada a *APAC Onco Exclusiva* (medicamentos oncológicos, implantação gradual; o Escudo ainda não usa). `_ajuda` avisa que dá para perguntar "o que é ...?". **Teste humano (18/10/2026): "o que é unacon e cacon" funcionava, mas "oq é unacon e cacon", "unacon e cacon", "me explica unacon e cacon" e "para que serve unacon e cacon" caíam em "foge do que sei".** Agora siglas ligadas por "e"/"ou" valem como pergunta e há jeitos curtos de pedir (`PEDE_SIGLA`: oq, me explica, para que serve...), **só para siglas** ("me explica a projeção de tendência" segue pergunta de dados); medições do entendimento idênticas (80/47/33, 0 erros). Pendente: o mesmo glossário na caixa do **Apoio** (hoje ela só busca serviços) e revisar o texto de cada termo com o autor.
- **Listas oficiais de hospitais de câncer (autor enviou, 18/10/2026):** (1) planilha do **Ministério da Saúde** "Hospitais habilitados em Oncologia" (habilitação 2023; SP = 80 estabelecimentos, com CNES e tipo UNACON/CACON): os 7 CNES conferidos no banco batem todos com ela, então é boa fonte de CNES; **o texto de IA com CNES errou 11 de 18** (ex.: HC Unicamp 2079133 -> o certo é 2079798; HC Marília 2077590 é o IBCC) -- nunca usar CNES de texto de IA; (2) PDF da **SES-SP** "Unidades habilitadas para atendimento em câncer no Estado de SP (atualizado junho/2021)", imagem (não copiável), com endereço e telefone por RRAS. **Santa Casa de Rio Claro: UNACON, CNES 2082888 (1.711 internações no banco do autor), R. Dois 297, (19) 3535-7000 (lista de jun/2021; cartão marcado "a confirmar").** **Feito (18/10/2026):** o recorte de SP está em `dados_geograficos/hospitais_oncologia_sp.csv` (80 estabelecimentos, só dado público; exceção no `.gitignore`) e `py etl\cruzar_hospitais_oncologia.py` (só lê; `--salvar` grava em `analises\`) cruza a lista, pelo CNES, com o `tbEstabelecimento` do CNES já em `banco\cnes` (endereço, telefone, coordenada, ativo/desabilitado), com as internações do banco e com o catálogo do Apoio; teste `etl/teste_cruzar_hospitais_oncologia.py` (entra no GitHub Actions). **Ideias combinadas (ainda não feitas, depois da apresentação de 20/10):** gerar a área "Hospitais no Estado" do Apoio a partir da lista oficial (tipo de habilitação em cada cartão); a Lia mostrar os hospitais habilitados mais próximos (linha reta entre centros, `localizacao.py`); e a pergunta de gestores "quantas mulheres moram a mais de X km de um hospital habilitado" (centros dos municípios + população do IBGE, descritivo); mapa nacional sugerido pelo ChatGPT só se o CNES trouxer coordenada confiável (nunca ponto no centro da cidade). Pendente: cadastrar Araras (Hospital São Luiz, UNACON, mesma RRAS 14 de Rio Claro); o CAISM Unicamp não consta como habilitado em oncologia nas listas (o HC da Unicamp consta); as páginas 4 e 7 do PDF não foram lidas.
- **Busca em "Onde ser atendida" (18/10/2026, Codex + Claude):** "Exames e especialistas" busca nos SERVIÇOS do CNES de cada unidade (`rlEstabServClass`, `tbClassificacaoServico`, `tbServicoEspecializado`: mamografia, ultrassom, preventivo...) e, desde o mesmo dia, nas ESPECIALIDADES MÉDICAS (`unidades_saude._medicos_cnes`: `tbCargaHorariaSus` x dicionário `tbAtividadeProfissional`, só ocupações "MEDICO ...", profissionais distintos com carga ambulatorial por unidade; o código do profissional fica só na memória e nada de pessoa é guardado; `tbDadosProfissionalSus` NUNCA é lido). É cadastro, não agenda. **Medido com o CNES real (18/10/2026, `py etl\diagnosticar_busca_cnes.py`, só leitura):** Rio Claro tem 888 unidades ativas (821 privadas, 55 públicas, 12 sem fins), identificadas pelo município do GESTOR (a tabela real não tem CO_IBGE); `tbCargaHorariaSus` (881 MB, 6,78 mi de linhas) tem bytes fora de UTF-8 depois dos primeiros 200 KB (por isso lê em latin-1; o 1º defeito foi esse e os médicos nunca apareciam); 26 dermatologistas em 29 unidades, só 3 públicas. **A busca mostra públicas e particulares em dois grupos** (nada some pelo filtro "só públicas"), o cartão mostra TUDO por unidade (médicos "N no ambulatório, M cadastrados", um por linha; excedente em "Ver os outros") e há uma lista "o que existe na cidade" (`oa.opcoes_de_busca`) para escolher sem adivinhar a palavra. Nomes de profissionais NÃO são mostrados (ficam em `tbDadosProfissionalSus`, nunca lido). **Caixa de busca refeita (18/10/2026, o autor: "a caixa de pesquisa não está boa"; bateria `algoritimos/teste_busca_caixa.py`, 47+ frases, 15 falhavam antes):** a palavra digitada tem de COMEÇAR uma palavra do cadastro ("ame" não acha "Gamela"); plural, feminino, radical (fisioterapia ~ fisioterapeuta) e hífen (prenatal ~ PRE-NATAL); erro de digitação corrigido só com palavras que EXISTEM no cadastro (`corrigir_busca`, difflib; a página avisa "Mostrando resultados para..."); todas as partes da frase precisam casar ("mamografia e ultrassom" = as duas); **exame só vale em serviço, nunca em médico** (um "médico em radiologia" cadastrado não é o aparelho de raio X: 31 em 29 unidades no CNES real); lugar cujo nome bate vem primeiro; apelidos do dia a dia (coração, olhos, grávida, criança); sem resultado, sugestões do que existe. Profissionais agora incluem psicólogo, nutricionista, fisioterapeuta, dentista, enfermeiro, assistente social etc. (`PROFISSOES_BUSCAVEIS`; veterinário e técnicos não). **Causa das UBS aparecerem em raio X/ultrassom/mamografia (achada com o CNES real, 18/10/2026, `diagnosticar_unidade_cnes.py "Fittipaldi"`):** `rlEstabServClass` tem 13 colunas e só 3 eram lidas; `TP_CARACTERISTICA` = 1 é serviço PRÓPRIO e = 2 é POR TERCEIRO (outro estabelecimento faz; `CO_CNPJCPF` o identifica). A UBS Dr Mario Fittipaldi registra pré-natal, atenção primária, imunização e saúde bucal como próprios (1) e radiologia, ultrassom, tomografia, ressonância e mamografia como terceiro (2), o que bate com o que o autor (trabalha na FMSRC) sabe: UBS só com especialistas, raio X nas UPAs, ultrassom no CEAD, o AME tem tudo. **O CNES estava certo; o erro era do Escudo, que não distinguia "faz" de "tem por terceiro".** Agora o texto de serviços marca o terceiro com `unidades_saude.TAG_TERCEIRO`, a busca e a lista "o que existe" só contam o próprio (`oa.separar_registros`), e o cartão mostra o terceiro À PARTE ("Serviços feitos por outro estabelecimento... não são feitos no próprio local", `oa.servicos_de_terceiros`). Serviço próprio vence terceiro quando os dois existem. Arquivo antigo sem `TP_CARACTERISTICA`: tudo conta como próprio. **O filtro "Só públicas e sem fins lucrativos" vale SEMPRE, também com busca digitada** (autor, 18/10/2026: "não se auto atualiza"; com busca ele era ignorado e o botão parecia morto) e a página diz quantas unidades particulares ele está ocultando e como vê-las. As colunas `CO_AMBULATORIAL_SUS`/`CO_HOSPITALAR_SUS` (SUS x não SUS?) NÃO foram interpretadas ainda: falta confirmar o significado dos códigos. `py etl\diagnosticar_servico_cnes.py "RADIOLOGIA"` (só leitura) lista quem FAZ e quem tem por terceiro, e tenta resolver quem é o terceiro. Testes: `teste_unidades_saude.py`, `teste_onde_atendida.py`, `dashboard/teste_onde_atendida_tela.py`.
- **CORREÇÃO da lista de hospitais habilitados (18/10/2026):** a planilha do Ministério usa células mescladas (UF/município em branco = os da linha de cima). A 1ª versão do CSV leu só as linhas com UF preenchida e tinha **80** estabelecimentos de SP; o certo são **88** (61 UNACON, 14 CACON, 8 hospitais gerais com cirurgia oncológica, 5 serviços de radioterapia; os 8 que faltavam: Albert Einstein, Santa Casa de Itu, Taubaté, Catanduva, CTR Ribeirão Preto, IRABC, Vila Nova Cachoeirinha, Vila Penteado). O Brasil tem **361** em 27 estados. `etl/gerar_lista_hospitais_oncologia.py` (lê o .xlsx sem dependências, `banco\cnes\Hospitais habilitados em Oncologia.xlsx`) grava `dados_geograficos/hospitais_oncologia_br.csv` e `_sp.csv`; teste `etl/teste_gerar_lista_hospitais_oncologia.py`. **O 88,7% de internações em hospitais da lista foi medido com 80: recalcular** (`py etl\cruzar_hospitais_oncologia.py`). Roteiro de terça já corrigido.
- **Página "Hospitais habilitados em oncologia" (18/10/2026, ideia do autor: mapa de hospitais de câncer, "pode ser Brasil: ajuda a entender por que vem tanta gente de fora"):** `dashboard/pages/hospitais_cancer.py` + `algoritimos/hospitais_oncologia.py` (testes `teste_hospitais_oncologia.py`, `dashboard/teste_hospitais_cancer_tela.py`). Página PRÓPRIA (só arquivos novos), com a PORTA dentro do Apoio (área "Hospitais no Estado": link "🗺️ Ver todos os hospitais habilitados no mapa", uma casa só; nenhum botão novo no topo do painel, "menos que já seja o mais"). Duas visões com os mesmos dados: Estado de SP (escolhe a cidade onde mora: os 3 hospitais mais próximos em LINHA RETA, `municipios_localizacao`) e Brasil (filtro por estado, tipo e busca; nota de que o SIH só enxerga hospitais de SP: dá para ver quem vem de fora, não quem sai). Dados: lista nacional do Ministério (`etl/gerar_lista_hospitais_oncologia.py` -> `dados_geograficos/hospitais_oncologia_br.csv`, 361 estabelecimentos) + endereço/telefone/posição do CNES (`etl/gerar_hospitais_oncologia_geo.py` -> `hospitais_oncologia_br_geo.csv`, **rodar no notebook**: lê o `tbEstabelecimento` de 300 MB). **Só vira ponto quem passa nas conferências** (cadastro ativo, UF do `CO_UNIDADE` = UF da planilha, coordenada dentro do retângulo do estado e, em SP, a até 35 km do centro do município); o resto fica na lista, sem ponto e com o motivo (nunca ponto no centro da cidade). Sem o arquivo de posições a página mostra a lista e diz o comando. **Texto: "contexto", nunca "motivo"** (detectar ≠ explicar): o mapa mostra onde ficam os hospitais, não explica por que as pacientes vêm de outros estados. Sem ranking, sem internações por hospital no Apoio (pareceria ranking de qualidade para uma paciente). Fica para depois: camada com a ORIGEM das pacientes (UF de residência no SIH) na aba Investigar, que exige combinar mexer no painel. **1ª rodada no notebook (18/10/2026): 357 de 361 com posição** (sem ponto: Santa Casa de Cuiabá e Instituto de Radium de Recife com cadastro DESABILITADO no CNES, e Marília e Avaré a 43-44 km do centro). **Fraqueza achada depois:** fora de SP a conferência era só o retângulo do estado (um ponto na cidade errada passaria; em SP 2 de 88 estavam errados, ~2%); agora o gerador também confere o CONTORNO do município (IBGE, baixado uma vez para `analises\municipios_ibge_caixas.csv`; aceita o ponto se cair em qualquer um dos dois candidatos, o município do `CO_UNIDADE` ou o do nome da planilha; sem internet, pula). **2ª rodada (18/10/2026, notebook): 353 de 361 com ponto**; os 8 sem ponto: 2 desabilitados no CNES (Cuiabá, Recife: o CNES ativo de nome parecido é OUTRA entidade, não se iguala), Avaré e Marília (44 km do centro) e 4 cujo ponto cai em outra cidade (Varginha, Dourados, Bonsucesso/RJ, Joaçaba). **Mapa com pydeck (não `st.map`):** nome no balão ao passar o mouse e, com até 15 hospitais na tela, o nome escrito ao lado do ponto; enquadramento próprio (`vista_do_mapa`, blocos de 512 px: o automático do pydeck deixava Barretos fora da tela); `character_set` do `TextLayer` vai como texto (lista vira expressão e quebra no navegador). Caixa fixa na página explicando UNACON, CACON e os outros tipos (descrições em `hospitais_oncologia.TIPOS`, uma casa só). Roteiro: 89,1% das internações em hospitais da lista (88 de SP). **Na aba Investigar (pedido do autor, 18/10/2026, "menos lapidado"):** o mapa de bolhas por estado de origem ganhou a chave "Mostrar também onde ficam os hospitais habilitados em oncologia" (`ver_hospitais`, ligada por padrão): pontos pequenos por tipo na mesma escala lat/lon, nome no balão, uma frase de leitura ("mostra de onde vêm e onde ficam; não explica por que vêm; habilitado não é vaga") e link para a página detalhada; sem o arquivo de posições a seção avisa o comando. Só dentro desse bloco; teste no cenário F de `dashboard/teste_painel.py`. Não foi visto no navegador real. **A conferir:** o aspecto do mapa com internet (fundo de ruas) no notebook.
- **Próximo passo combinado (18/10/2026): mapa por área de USF com o projeto do Kauê (`KaueFLima/MISM`).** O Kauê é do mesmo grupo e colaborador do MISM2; os dois projetos se completam. **Ainda NÃO acoplado** (não antes da apresentação de 20/10 à Secretaria). O projeto dele tem 3 scripts (`georreferenciar_dados.py`: CEP -> coordenada; `classificar_areas_usf.py`: coordenada -> área da USF por polígono `mapaRioClaroUSF.geojson`; `gerar_mapa.py`: HTML Leaflet). Pergunta nova que ele responde: "dentro de Rio Claro, qual área de USF concentra mais internações?". **Condições para acoplar:** (1) o `gerar_mapa.py` grava um registro por paciente (CEP, logradouro, lat/lon, idade, valor, dias, óbito, CID) dentro do HTML público: **esse HTML não entra e não é mostrado**; (2) o CEP e a coordenada só existem num passo LOCAL (como os outros ETLs, lendo `dados\`), que grava no banco apenas contagem agregada por área da USF x ano x câncer, com supressão de números pequenos (ex.: "menos de 5"); (3) sem geopandas (cruzamento ponto-polígono em Python puro, como em `baixar_centroides.py`); (4) conferir que a soma 2021-2025 bate com as internações de Rio Claro do painel; (5) faltam os arquivos `mapaRioClaroUSF.geojson`, `municipio_rio_claro.geojson` (de onde vêm? data?) e o banco de CEPs com coordenadas do Google (termos de uso do Google restringem guardar o resultado: conferir); (6) crédito ao Kauê na página "Método". Visual: nova visão na aba Investigar com pergunta + selo "📍 Rio Claro" + leitura, sem mexer nas abas, na Lia nem no chatbot existentes.
- Ainda não feito (combinar): população do IBGE; testar com pessoas de verdade; revisar com o autor o
  vocabulário popular do Apoio (`apoio_busca.VOCABULARIO`/`EXTRA`).

- **Decisões de 20/10/2026 (o autor mandou decidir sem pedir autorização, com a régua "o dashboard tem de ser legível, não um quebra-cabeça").**
  (1) **Apoio:** faixa fixa de emergência (190/180/192), faixa "Você está em", a página não abre mais em câncer de mama, nomes unificados
  ("Meu exame deu alterado", "Barretos: Hospital de Amor"; "porta" virou "assunto" para a usuária), glossário (`apoio.GLOSSARIO`), botão
  "Abrir o boletim da região (PDF)" nos 3 hospitais da RRAS 14, carretas num bloco só, Lia da lateral sem repetir a lista de cartões, ordem do cartão
  (Para quem, Como funciona, Onde e contato, O que levar), "Para quem" dos hospitais, fones de CEAD e DDM vindos do cadastro de Onde ser atendida.
  **O Cadu fica como está** (ninguém em Rio Claro sabe quem opera; cartão "a confirmar"). Cuidado: texto novo em `contato`/`para_quem` entra no índice da busca
  (a palavra "telefone" ou "regulação" ali já derrubou `teste_conversa_apoio`). Teste de jornada das 4 mulheres em `dashboard/teste_apoio_tela.py` (A2).
  (2) **Gráfico de idade** (pedido da Secretaria da Mulher): cidade e câncer escolhidos no próprio gráfico, "Todos os cânceres acompanhados"
  (`inteligencia.TODOS_CANCERES`), um único ano vira um período, cidade sem dado diz "este dado não existe". Cenário J de `teste_painel.py`.
  (3) **Aba Investigar dividida:** nova aba **Rede hospitalar** (fluxo, hospitais, mapa, tabela de fluxo, cidade atendida) e Investigar fica só com
  perguntas da cidade escolhida (câncer que cresce, idade, comparar cidades). Cada pergunta numa aba só (cenário K). Destinos da Lia de fluxo e polos
  agora vão a "Rede hospitalar". Inventário em `docs/INVENTARIO_DO_PAINEL.md`.
  (4) **2025 e 2026 (CONFIRMADO no notebook do autor em 20/10/2026 com `py -3.12 etl\listar_meses_pysus.py --ano 2026` e `--ano 2025`):**
  **2025** tem 12/12 meses nas três bases (SIH/RD, SIA/AQ, SIA/AR): já está no banco, NÃO baixar de novo. **2026:** SIH/RD tem só **jan, mar, abr, mai, jun, jul**
  (fevereiro não foi listado; agosto em diante ainda não existe); SIA/AQ e SIA/AR têm **jan a jul**. É lacuna da fonte, nunca preenchida. A nuvem não alcança o DATASUS
  (proxy 403) e a web não traz cronograma de 2026. Regras do autor: preservar as lacunas, nunca preencher/estimar, lacuna da fonte != falha de download, não repetir
  download nem verificação já feitos, ano incompleto não se compara como ano completo.
  **Como atualizar (feito em 20/10/2026, falta rodar no notebook):** `py -3.12 etl\baixar_sih_sp.py --anos 2026` (modo incremental `main_incremental`/`atualizar_anos`:
  baixa só esses meses e troca, dentro do CSV atual de cada câncer, só as linhas de ANO_CMPT=2026; o resto fica intacto, CSV antigo vai para `_backup_*`, erro de
  download de verdade não troca nada, sem CSV atual não inventa; rodar de novo não duplica); `py -3.12 etl\baixar_sia_oncologia.py --anos 2026-2026` (já troca só o ano);
  depois `py etl\carga_todas_bases.py` (feche o painel). Teste: `etl/teste_baixar_sih_sp.py`. SIM (`DOSP`) e CNES: NÃO sabemos se têm 2024/2026 (a carga de 17/10 foi SIM até 2023 e CNES até 2025); `py -3.12 etl\\listar_meses_pysus.py --ano 2024` (e 2025, 2026) agora também pergunta CNES/EQ, CNES/LT e o SIM (um arquivo por ano), sem baixar nada. Os textos "2013–2025" do painel agora vêm do
  banco (`ano_ini`–`ano_fim`). 2026 entra como ano INCOMPLETO pelas regras que já existiam (`meses_por_ano`, `anos_incompletos`, `ajustar_meses`; teste em `teste_inteligencia.py`).
  **Consulta nova "Quantas internações o SIH registrou em <ano>, mês a mês?"** (fim da aba Evolução; pedido da Secretaria da Mulher): `inteligencia.internacoes_do_periodo`/`leitura_internacoes_periodo`
  (ano, **mulheres que moram na cidade x internações nos hospitais da cidade**, um câncer ou os 7 somados; mês que a fonte não tem = "sem dado", NUNCA zero; mês da fonte sem registro = zero de
  verdade; total é o registrado; diz o último mês e que o ano está incompleto; o ano é o da competência). Cenário L de `teste_painel.py`. **Conferido pelo autor no notebook com o banco real (20/10/2026): a pergunta mostra 2026 até julho, como previsto.**
  **Falta:** a Lia responder "quantas internações em <cidade> neste ano?" (hoje só o painel) e decidir se `ANO_CMPT` = ano da internação (ver `analises\investigacao_2025.txt` no notebook).
  **O que o DATASUS oferece (CONFIRMADO no notebook em 20/10/2026, `listar_meses_pysus.py --ano 2024/2025/2026`):** SIH/RD 2024 só 8 meses (faltam 02, 06, 08, 12; lacuna da fonte); SIA 2024 e 2025 12/12; CNES 2024 e 2025 12/12 e 2026 jan-ago (o ETL usa dezembro, então 2026 ainda não entra);
  **SIM: 2024 existe como `DOSP2024` (o ETL atual lê: `py -3.12 etl\baixar_sim_obitos.py --anos 2024-2024`, e o padrão do ETL agora é 2013-2024); 2025 e 2026 NÃO têm `DOSP`: o PySUS lista só
  `Mortalidade_Geral_2025.parquet` / `_2026` (provavelmente do Brasil inteiro, por residência, e DOSP é por ocorrência em SP: misturar pode criar queda falsa nos totais do Estado).**
  Por isso o ETL NÃO lê esse arquivo ainda: antes, `py -3.12 etl\sondar_mortalidade_geral.py --ano 2025` (só conta; não grava nem mostra declaração; teste `etl/teste_sondar_mortalidade_geral.py`) diz as colunas, se é nacional, até que mês vai.
  **Resultado da sonda (notebook, 20/10/2026):** `Mortalidade_Geral_2025`: 1.528.085 linhas, NACIONAL (27 UFs de residência), 354.173 de moradores de SP, **15.199 óbitos de mulheres pelos 7 cânceres entre moradoras de SP**, óbitos de 01/01 a 31/12/2025 (12 meses), com LOCOCOR, RACACOR, IDADE, CAUSABAS, CODMUNRES, DTOBITO. `DOSP2024` (carregado): 351.616 óbitos no arquivo, 15.245 de mulheres pelos 7 cânceres (2023: 14.711).
  **Decisão (20/10/2026):** `baixar_sim_obitos.py` usa o `DOSP` e SÓ SE ele não existir cai para o `Mortalidade_Geral`, filtrado para moradoras de SP (`CODMUNRES` começando em 35, `preparar(residentes_uf="35")`), lendo só as colunas necessárias; cada ano grava em `obitos_sim_fonte` (ano, arquivo, meses com óbito).
  O "Estado" do SIM (`resumo_mortalidade`) agora conta SEMPRE só moradoras de SP (o DOSP tem também moradoras de outros estados) e `leitura_mortalidade` avisa quando o último ano vem do `Mortalidade_Geral` ("preliminar, pode ser revisado") ou tem menos de 12 meses. Testes: `etl/teste_baixar_sim_cnes.py` e 7g de `teste_assistente.py`. Para carregar: `py -3.12 etl\baixar_sim_obitos.py --anos 2025-2026` (rodou 2024 no notebook: 15.245).
  **SIA/SIM/CNES no painel:** hoje só a Lia usa; entram no painel (uma seção própria, nunca somadas ao SIH) depois de conferir os códigos com o banco real.
  A afirmação do ChatGPT de que o SIH ainda não tem regra territorial única está desatualizada (resolvido em 08/10/2026).

- **Layout sem barra lateral (22/10/2026, ideia de um integrante do grupo: "abas laterais"; o autor achou as abas do painel de difícil
  visualização e sem hierarquia, e deixou a decisão final com o Claude).** A lateral saiu do painel e do Apoio; a Lia é UMA só, no centro,
  entre as abas e os dados, com a caixa "Pergunte à Lia" logo abaixo (chaves `caixa_*`, `lia_*` e `bv_*` iguais às de antes). Ordem do painel:
  título -> botões das outras páginas em fileira (só "Apoio à mulher" é vermelho) -> abas com cara de aba (ativa em roxo) e Início no mesmo nível
  -> "Você está em" -> Lia -> seletor de município (junto dos dados, dizendo que 📍 muda e 🌎 não) -> números grandes (só no Panorama) e gráficos.
  **Por que as abas pareciam círculos soltos:** o CSS antigo usava `input[value="Panorama"]`, mas o Streamlit atual põe `value="0"`, `"1"`...; o
  estilo novo usa `data-testid="stRadioOption"` e `data-selected` dentro do container `abas_painel` (se uma versão nova do Streamlit mudar esses
  ganchos, as abas voltam a parecer círculos: conferir ali primeiro). **Lia recolhível** (`lia_recolhida`, botões `caixa_lia_recolher` e
  `caixa_lia_abrir`; as chaves NÃO podem começar com `lia_`, o teste do painel as trataria como caminho da árvore): faixa fina que deixa os dados
  subirem; ela reabre sozinha quando a pessoa clica numa pergunta. Celular: abas numa linha que rola de lado, rosto menor (antes a caixa de
  perguntas ficava escondida atrás da seta da lateral). O CSS é lido uma vez: reiniciar o painel depois de mexer em `estilo.py`. Testes de tela
  agora procuram a Lia em `at.main` (não mais em `at.sidebar`); o Início da lateral do Apoio deixou de existir. **Visto só com dados de teste e
  com Streamlit 1.66; não visto no navegador do autor nem com o banco real.** O texto da Lia e o do cartão no Apoio se repetem (antes ficavam lado a lado).
  **Seletor de município colado nos dados (autor, 22/10/2026: "ele lá em cima não faz sentido"):** `desenhar_seletor_cidade` (app.py) desenha o seletor UMA vez por execução, em TODA aba (o Streamlit esquece um widget que deixa de ser desenhado, e a cidade voltaria ao padrão): nas abas da cidade, no começo dos dados; na **Rede hospitalar**, logo acima do bloco "Quem é atendida nos hospitais de <cidade>" (os gráficos de cima são do Estado e não mudam; sem o fluxo no banco ele vai para o fim da aba). A cidade é lida de `st.session_state["municipio_painel"]` no topo do script. Teste: cenário M de `teste_painel.py` (ordem, troca de cidade, volta por todas as abas).

- **De quais cidades vêm as mulheres de fora (22/10/2026, pedido do autor: "fica lindo e ajuda muito por serem cidades vizinhas"; o autor deixou o desenho com o Claude).**
  Na aba Rede hospitalar, visão "Mulheres de fora da cidade atendidas na cidade", nova pergunta "De quais cidades de SP vêm as mulheres de fora?" (📍 cidade escolhida),
  com o seletor "Ver como": **Mapa** (padrão) ou **Barras** (uma informação, uma casa só). `inteligencia.fluxo_da_cidade` devolve `origens` (cidade de
  RESIDÊNCIA das internações nos hospitais da cidade, nome do catálogo `municipios`, plano B pela chave); `agrupar_origens` mostra só as cidades com pelo menos
  `MINIMO_POR_CIDADE` = 5 internações e no máximo as `MAXIMO_DE_CIDADES` = 15 maiores (polo como Barretos recebe de dezenas de cidades); as demais viram uma barra só
  ("Outras N cidades (até M cada)") e NÃO entram no mapa (se nenhuma chega a 5, vale a lista das maiores, também com teto); as barras somam o número "De outras cidades de SP".
  **Vale para qualquer cidade do seletor** (usa o código IBGE da cidade escolhida; testado com Rio Claro e com Barretos em `teste_fluxo.py`). `localizacao.pontos_origens` dá a posição: o ponto é o CENTRO do município (`municipios_localizacao`, IBGE),
  nunca o endereço de ninguém; cidade fora da tabela fica de fora e é contada em "sem posição" (nunca ponto inventado); sem a tabela ou sem o centro da
  cidade dos hospitais só aparecem as barras. A leitura (`leitura_cidade_visao`, usada também pela Lia) cita as 3 maiores com a parcela e diz que a cidade é a de
  residência e que mostra de onde vêm, não explica por quê. **Conferido com o banco real do autor (22/10/2026):** Rio Claro = 1.508 moradoras + 350 de outras cidades de SP +
  0 de outros estados nos hospitais da cidade; Santa Gertrudes 143, Itirapina 59, Ipeúna 56, Analândia 28, Corumbataí 18 (as 14 maiores somam 343, as 7 restantes têm 1 cada);
  `OUTRO_ESTADO` = 0 por consulta direta. Testes: `teste_fluxo.py` e o cenário F de `dashboard/teste_painel.py`. Visto só com posições aproximadas (demonstração) e dados de teste.

- **Ficha do hospital mais completa, para gestor e pesquisador (22/10/2026, o autor ama a ficha e a tabela "Quem vem de fora, de qual câncer e para qual hospital? Pesquise tudo" e pediu para decidir o melhor
  sem juntá-las; a tabela NÃO mudou).** Os dois itens olham de lados opostos e ficam separados: a **tabela** é o lado da ORIGEM (só mulheres de outros estados, todos os hospitais, estado de origem,
  óbitos, dias de leito, anos, busca, CSV); a **ficha** é o lado do HOSPITAL (todas as pacientes de um hospital, por procedência, urgência, permanência vs Estado, ano a ano). O que a ficha ganhou:
  (1) **filtro de Anos** (`hospital_anos`, intervalo; vale para a lista de hospitais, os números, o gráfico por ano, os estados e a referência do Estado: `ficha_hospital(..., anos=)`,
  `lista_hospitais(..., anos=)`, `texto_do_periodo`; a consulta `SQL_HOSPITAL_UF` agora guarda o `ano`; dados antigos sem a coluna não quebram); (2) o **hospital escolhido fica guardado pelo CNES**
  (`hospital_cnes`, `guardar_hospital`) e não pula quando o câncer ou os anos mudam; a chave do seletor só ganha sufixo quando há período, então `hospital_perfil_todos` continua valendo;
  (3) **"De quais estados vêm as mulheres de fora de <hospital>?"** (barras, `agrupar_estados`, `leitura_estados_do_hospital`; selo 🌎); (4) **atalho** "Ver estas internações na tabela completa": preenche a busca (CNES),
  o câncer e os anos da tabela de baixo (`abrir_tabela_do_hospital`; só põe câncer e anos que existem nas opções da tabela, senão o Streamlit dá erro); (5) **CNES visível** e **CSV por ano**
  (`hospital_baixar_anos`). **Deliberadamente NÃO entrou letalidade/óbitos por hospital na ficha:** a própria leitura diz que ela "não serve para comparar hospitais nem medir qualidade" (hospital de referência
  recebe casos mais graves), e um número de óbito ao lado do nome do hospital seria lido como nota. A redundância que sobra na aba é a tabela "Quais hospitais de SP mais atendem..." (os 10 maiores),
  que é a tabela completa somada por hospital; deixada como está. Testes: `teste_hospital.py` (período) e o cenário H de `teste_painel.py`.

- **Palavra extinta (autor, 23/10/2026: "nós combinamos que não existe observatório; essa palavra foi extinta").** O Escudo/MISM2 não se chama nem se descreve como "observatório" em texto
  visível, documento ou comentário. O cabeçalho do painel agora diz "MISM2 · saúde da mulher". Se aparecer de novo (por exemplo em texto gerado), troque por "painel" ou "saúde da mulher".
- **Telas grandes (autor, 23/10/2026: "as laterais estão vazias; o texto e a Lia poderiam ser maiores; ela é a estrela").** Só a partir de 900 px de largura (`@media (min-width: 900px)` no fim do CSS de
  `dashboard/estilo.py`; o celular não muda): página até 1560 px, texto 10% maior (`html { font-size: 110% }`), Lia maior (rosto 210 px nas boas-vindas e 140 px nas respostas, com contorno claro e sombra),
  nome e fala dela maiores. O mesmo CSS vale para o painel, o Apoio e as outras páginas. O gráfico do Plotly passou de fonte 13 para 14.

## Notas de contexto do domínio

- Banco de dados: `banco/escudo_feminino.db` (SQLite). O caminho é
  calculado a partir da pasta do projeto (`RAIZ_PROJETO`), não fixo: o
  projeto pode ficar em qualquer pasta (hoje `C:\MISM2`). Painel e
  `algoritimos/` leem o `BANCO` de `configuracao_geografica.py`; os
  scripts de `etl/` calculam o mesmo caminho. O banco e a pasta `dados\`
  não vão para o GitHub: ao mudar o projeto de pasta, levar `banco\` e
  `dados\` junto (ou rodar a carga de novo).
- **Dados em Parquet / site único (27/10/2026, autor e grupo):** o MISM2 roda também dentro do site único
  (`MISM-Saude-da-Mulher/MISM`: abas MAPA do MISM 1 e CENTRAL DE INFORMAÇÕES deste painel). `algoritimos/fonte_parquet.py`
  monta o SQLite a partir de `<site>/dados_parquet/mism2` num cache (`.cache_mism/`) e `configuracao_geografica.BANCO` aponta para ele
  (`ESCUDO_BANCO_SQLITE` força um `.db`); **sem a pasta `dados_parquet`, nada muda: vale `banco\escudo_feminino.db`** (quem usa só `C:\MISM2`
  continua como sempre). O banco legado **nunca é lido nem alterado** pelo caminho do Parquet. `unidades_saude.py` lê o CNES do CSV ou,
  se só houver o Parquet, de `dados_parquet/cnes` (`_ler_csv`, `_existe`). Na hospedagem, `garantir_dados()` baixa os arquivos de um
  dataset privado do Hugging Face (`MISM_DATASET`, `HF_TOKEN`). **Depois de qualquer carga nova no banco, rodar
  `py etl\exportar_banco_parquet.py`** (perguntas_usuarios sai só com o esquema), senão o site lê o Parquet antigo. Os testes que montam
  CNES sintético usam `ESCUDO_PARQUET_PASTA` apontando para uma pasta inexistente. **Memória:** `inteligencia._compactar_tratamento`
  (categorias no pandas >= 3, inteiros menores, nunca altera valores) e a leitura em pedaços de `carregar_tratamento` reduziram o painel de
  ~790 para ~295 MB em repouso; `resumo_tratamento` foi conferido (328 combinações idênticas). `teste_painel.py` completo precisa de
  >2 GB de RAM livre; no notebook do autor (7,4 GB) rodar com poucos programas abertos ou por cenário. As falhas dos cenários F (números dos dados
  reais) e I (o `.env` tem GEMINI_API_KEY) do teste são do ambiente, não do código.
- `pysus` só funciona no Python 3.12 do autor (`py -3.12`); o `py`
  padrão dele é 3.14.
