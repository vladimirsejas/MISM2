# MISM2 — Monitoramento Inteligente da Saúde da Mulher

> **Novo nome do projeto:** o projeto, antes chamado **Escudo Feminino**,
> passou a se chamar **MISM2** — *Monitoramento Inteligente da Saúde da
> Mulher*. Ele é o **complemento do projeto MISM**:
> https://github.com/KaueFLima/MISM
>
> "Escudo Feminino" continua aparecendo neste README e no código como o
> nome do painel/sistema (arquivos, pastas e o atalho `Abrir Escudo
> Feminino.bat`); só o nome do projeto mudou.

> **Aviso: este README é informativo, não é diretriz.** Ele é o
> último passo do nosso trabalho: só recebe o registro do que já foi
> decidido e feito, para quem chega ao projeto. Não é guia nem regra
> para o desenvolvimento. As decisões vêm da conversa com o autor
> (Vladimir) e do próprio código; se o README estiver desatualizado
> ou divergir disso, vale a conversa e o código, e o README é que
> deve ser corrigido depois. Isso vale para qualquer IA que ajude no
> projeto (Claude, ChatGPT etc.).

Sistema de inteligência analítica sobre saúde da mulher, construído a partir
de dados de internações hospitalares do SUS relacionadas a câncer feminino
no município de Rio Claro (SP), comparado ao Estado de São Paulo.

O projeto é um **Sistema de Apoio à Decisão para Políticas Públicas baseado
em Inteligência Analítica** — a Lia é a porta de entrada; o produto de
verdade é a inteligência que calcula os números por trás dela.

Trabalho acadêmico de graduação em Inteligência Artificial — Fatec Rio
Claro, 3º semestre.

---

## Abrir o painel (com a Lia) sem terminal

Dê dois cliques em **`Abrir Escudo Feminino.bat`**, na pasta do
projeto. Ele atualiza o projeto pelo GitHub, liga o painel numa janela
minimizada e abre o navegador em http://localhost:8600 quando estiver
pronto. Para fechar, feche a janela "Escudo Feminino - painel". Se o
código mudou desde a última vez, ele reinicia o painel sozinho.

Os outros dois atalhos que já existem: **`Atualizar dados do Escudo.bat`**
(refaz a tabela `internacoes` a partir dos CSVs que já estão em `dados\`;
não baixa nada da internet, e as outras tabelas ficam como estão) e
**`Testar IA (Gemini).bat`** (confere se a chave do Gemini funciona).
No PowerShell, arquivo com espaço no nome se chama assim:
`& ".\Abrir Escudo Feminino.bat"`.

---

## Dados em Parquet e site unificado (27/10/2026)

O MISM2 também roda dentro do **site único do grupo** (repositório `MISM-Saude-da-Mulher/MISM`, com as abas MAPA, do MISM 1, e
CENTRAL DE INFORMAÇÕES, que é este painel). Nesse site os dados vêm do Parquet, sem guardar o banco no projeto:

- **Banco:** as tabelas do painel ficam em `dados_parquet/mism2/` (uma por arquivo, mais `esquema.sql`), na pasta do site, ao lado do `MISM2`.
  Quando essa pasta existe, `algoritimos/fonte_parquet.py` monta o SQLite num cache local (`.cache_mism/`, uns 10 s, refeito sozinho se o Parquet
  mudar) e `configuracao_geografica.BANCO` aponta para ele. As consultas SQL do painel não mudaram.
  **Sem a pasta `dados_parquet`, tudo funciona como sempre: lê `banco\escudo_feminino.db`** (é o caso de quem usa só a pasta do MISM2).
  `ESCUDO_BANCO_SQLITE=<caminho>` força um `.db` específico.
- **CNES (Onde ser atendida):** `unidades_saude.py` usa o CSV de `banco\cnes` se ele existir; senão, as tabelas em `dados_parquet/cnes/`. O resultado é o mesmo.
- **Hospedagem:** sem `dados_parquet` no servidor, `fonte_parquet.garantir_dados()` baixa os arquivos de um dataset privado do Hugging Face
  (variáveis `MISM_DATASET` e `HF_TOKEN`). Passo a passo no `HOSPEDAR.md` do repositório do site.
- **Atualizar o Parquet:** depois de uma carga nova no banco (`etl\carga_todas_bases.py` etc.), rode `py etl\exportar_banco_parquet.py`.
  Sem isso, o site continua lendo o Parquet antigo. A tabela `perguntas_usuarios` é exportada só com o esquema (sem linhas).
- **Memória:** `inteligencia.carregar_tratamento` lê `oncologia_ambulatorial` em pedaços e compacta os tipos (`_compactar_tratamento`; resultados idênticos,
  painel de ~790 para ~295 MB em repouso).

---

## Como montar o banco do zero

O painel lê direto a tabela `internacoes`; não há mais cadeia de
scripts intermediários (a arquitetura antiga das 13 tabelas saiu em
09/2026 e está no histórico do git). Da pasta do projeto:

```powershell
py etl\criar_tabela_municipios.py   # catálogo IBGE dos municípios (uma vez)
py etl\carga_todas_bases.py         # monta internacoes a partir dos CSVs estaduais
py etl\validar_banco.py             # conferência: total e tipos de câncer carregados
```

Os CSVs ficam em `dados\cancer_<tipo>_sp\` (um CSV por pasta). A carga:

- lê **só os arquivos estaduais** (eles já trazem a cidade de
  residência); pastas municipais antigas são ignoradas com aviso, para
  Rio Claro não ser contada em dobro;
- recusa rodar se houver mais de um CSV na mesma pasta;
- detecta se o CSV usa `;` ou `,`;
- guarda o **mês**, o **estado de residência**, o **município do hospital**
  e o **CNES** de cada internação (nunca CEP, nascimento ou nº da AIH);
- lê e confere os 7 arquivos antes de gravar e só troca a tabela no fim
  (o banco anterior fica em `banco\escudo_feminino_antes_da_carga.db`).

Para baixar de novo o SIH do DATASUS: `py -3.12 etl\baixar_sih_sp.py
--aceitar-lacunas-da-fonte` (o `pysus` não funciona no Python 3.14). Sem
filtro de residência: o Estado conta o atendimento em SP, inclusive
moradoras de outros estados.

### Outras bases (17/10/2026): um comando só

```powershell
py -3.12 etl\carregar_tudo_pysus.py            # tudo (cerca de 40 min; feche o painel antes)
py -3.12 etl\carregar_tudo_pysus.py --so sim   # uma etapa: populacao, geo, sia, sim ou cnes
py etl\validar_bases_novas.py                  # só LÊ o banco: o que entrou em cada tabela
```

| Etapa | Fonte | Tabela | O que responde |
|---|---|---|---|
| `populacao` | IBGE, Censo 2022 (tabela 9514) | `populacao_mulheres` | internações por 100 mil mulheres, ranking entre cidades |
| `geo` | IBGE, malha dos municípios | `municipios_localizacao` | distância até os hospitais de câncer |
| `sia` | SIA/SUS, APACs de quimio (AQ) e radio (AR) | `oncologia_ambulatorial` | tratamento fora da internação |
| `sim` | SIM, declarações de óbito (`DOSP`) | `obitos_sim` | mortes por câncer dentro e fora do hospital |
| `cnes` | CNES, equipamentos (EQ) e leitos (LT) | `cnes_equipamentos`, `cnes_leitos` | capacidade (códigos crus, ainda não usados na Lia) |

Só **agregados** vão para o banco: nenhum nome, CPF, cartão SUS, CEP ou
nascimento. Detalhes e o que foi conferido em `docs\FONTE_DOS_DADOS.md`.

---

## O painel e a Lia

O dashboard (`dashboard\app.py`) é organizado por perguntas, em portas
onde cada informação tem uma casa só:

- **Panorama** — o que está acontecendo? Barras por internações, valor
  hospitalar registrado, óbitos ou dias, e a ficha "o que chama
  atenção" do câncer em foco.
- **Evolução** — como mudou? Linha 2013–2025 com camadas (ritmo do
  Estado, anos fora do padrão, projeção de tendência) e a caixa de
  confiabilidade da informação.
- **Investigar** — o que merece ser pesquisado? Anos fora do padrão,
  quando cada câncer aparece, faixa etária, **fluxo de pacientes**
  (mulheres de outros estados atendidas em SP, e para onde vão as
  moradoras da cidade) com um mapa de estados de origem que pode mostrar
  também **onde ficam os hospitais habilitados em oncologia**, **comparar
  cidades** e download dos dados.
- **Planejamento** — se nada mudar, onde a cidade pode ter problema até
  daqui a 3 anos? O radar do futuro, sem valores de orçamento: quem
  decide é o gestor.
- **Método** — como ler e o que os dados não permitem responder.

Páginas à parte (as duas primeiras, pelos botões no topo; a terceira, por um link dentro do Apoio):

- **Apoio à mulher** (`dashboard\pages\apoio.py`): para quem **procura
  cuidado**, não para quem planeja. Catálogo com fonte oficial e data de
  conferência (rede oncológica, regulação, direitos, 23 hospitais de
  câncer por região, Rio Claro e Barretos). Boas-vindas com 4 entradas
  (prevenção e exames, exame alterado, diagnóstico de câncer, não sei por
  onde começar). **As carretas da mamografia não têm itinerário no código**
  (muda a cada ~15 dias): a página manda para o canal oficial.
- **Onde ser atendida** (`dashboard\pages\onde_ser_atendida.py`): unidades
  de saúde da cidade (CNES) junto do catálogo conferido de Rio Claro, com
  "Como chegar" e "Ligar". A busca de "Exames e especialistas" procura nos
  serviços e nas especialidades médicas do cadastro, separa o que a unidade
  faz sozinha do que só tem por terceiro, e mostra públicas e particulares em
  dois grupos. Cadastro não é vaga nem serviço aberto.
- **Hospitais habilitados em oncologia** (`dashboard\pages\hospitais_cancer.py`):
  mapa dos hospitais que o Ministério da Saúde habilitou para tratar câncer
  (lista de 2023: 361 no Brasil, 88 em SP), com nome, tipo (UNACON, CACON...),
  telefone, "Como chegar" e os mais próximos de uma cidade de SP, em linha reta.
  Só aparece no mapa o hospital cuja posição passou nas conferências; o resto
  fica na lista, com o motivo. A página explica UNACON e CACON e lembra que
  **habilitado não é vaga**: o acesso é pela regulação. O mapa mostra onde
  ficam os hospitais, não explica por que as pacientes vêm de outros estados.

Quem conduz é a **Lia** (`docs\LIA.md`): no primeiro acesso ela aparece
no centro; depois fica na lateral com os caminhos em botões, e o painel
acompanha cada resposta. O **Passeio pelo Escudo** conta o essencial em
6 paradas. Embaixo de cada gráfico vem a leitura em texto.

### Pergunte à Lia (a IA do Escudo)

Abaixo do balão da Lia há uma caixa de perguntas em texto (`docs\IA_DO_ESCUDO.md`).
Fluxo: a pergunta é entendida por regras e busca de palavras
(`entendimento.py`, com segurança primeiro: violência, suicídio e emergência
vão para 190/180/188/192), os números saem de `inteligencia.py`
(`assistente.py`) e o **Gemini só reescreve** a resposta em linguagem
simples; tudo o que ele escreve é conferido (número que não está nos
cálculos, "vai ficar" ou explicação de causa são descartados e a resposta
direta da Lia aparece). Sem chave, sem rede ou sem cota, o painel responde
igual, só sem a reescrita. O texto da pergunta nunca é gravado. Ela responde,
entre outros assuntos: o que mais aparece, se está aumentando, comparar com o
Estado, óbitos, valores, idade, a tendência, **ranking por 100 mil mulheres**,
**cidades que mais tratam** (hospital x residência), **quimio e radioterapia**,
**mortalidade real (SIM)**, e onde procurar hospital de câncer a partir da
cidade que a pessoa cita (com a distância em linha reta). Perguntas do tipo
"o que é APAC?" ou "o que é UNACON?" são respondidas por um **glossário** de
texto fixo (`glossario.py`): a IA não improvisa definição.

### Onde está a inteligência artificial

| Parte | O que é | Onde |
|---|---|---|
| **Gemini (modelo de linguagem)** | Reescreve em linguagem simples as respostas de **dados** e, quando as regras não entendem a pergunta, escolhe o assunto numa **lista fechada** (a escolha só vale se a busca local concordar). Tudo o que ele escreve é conferido; sem chave, rede ou cota, a resposta direta aparece | `ia_linguagem.py`, `assistente.py`, `entendimento.py` |
| **Entendimento da pergunta** | Busca local por palavras e letras (aguenta erro de digitação), com vocabulário popular e segurança primeiro, sem dependências | `entendimento.py` |
| **Projeção de tendência** | 5 modelos pequenos (ingênuo, média dos 3 últimos anos, tendência, tendência recente e Holt) escolhidos por **teste de acerto** sobre anos que já se conhecem; a faixa vem do erro medido e é sempre comparada com "repetir o último ano". Sem anos suficientes, não prevê | `inteligencia.py` (seção "Previsão com validação") |
| **Anos fora do padrão** | Compara cada ano com o esperado pela tendência dos outros anos | `inteligencia.py` |

O que **não** é IA, de propósito: textos de segurança (190/180/188/192), de
sintomas, do catálogo do Apoio e do glossário são fixos. No **Apoio à mulher**
nenhuma IA escreve sobre serviço; o Gemini fica desligado por padrão e, se
ligado, só ajuda a escolher o assunto. A IA nunca afirma causa, nunca promete
("vai ficar") e nunca fala de orçamento.

Conferido: os testes dessa parte (`teste_previsao.py`, `teste_entendimento.py`,
`teste_assistente.py`, `teste_glossario.py` e o cenário da caixa em
`dashboard\teste_painel.py`) passam na nuvem com um Gemini simulado. O Gemini
real foi testado pelo autor em 17/10/2026 (`Testar IA (Gemini).bat`; painel com
o banco real). Só com as regras, o entendimento acerta direto 80 de 91, 47 de 62 e
33 de 35 perguntas dos gabaritos; com o Gemini, 91, 62 e 35, sem resposta errada.
Ressalva: as perguntas dos gabaritos foram escritas pela própria equipe.

### Testes

A integração contínua roda tudo em `.github/workflows/testes.yml` (mais
de 40 testes, sem o banco real, com dados sintéticos). Os principais, da pasta
do projeto:

```powershell
python algoritimos\teste_inteligencia.py   # os números (inclui ranking e polos)
python algoritimos\teste_lia.py
python algoritimos\teste_entendimento.py   # entender a pergunta + medição com gabaritos
python algoritimos\teste_assistente.py     # respostas, conferência da IA, segurança
python algoritimos\teste_apoio.py          # catálogo do Apoio
python algoritimos\teste_apoio_busca.py
python dashboard\teste_painel.py           # abre o painel e clica em tudo (~4 min)
python dashboard\teste_apoio_tela.py
python dashboard\teste_onde_atendida_tela.py
python algoritimos\teste_hospitais_oncologia.py
python dashboard\teste_hospitais_cancer_tela.py
py -m streamlit run dashboard\app.py
```

Cuidados que a inteligência central já aplica:
- **Uma fonte por cidade.** A carga lê só os arquivos estaduais.
  Assim Rio Claro não é contada em dobro.
- **Meses que o DATASUS não oferece.** Faltam 35 dos 156 meses de 2013
  a 2025 no SIH (2018 só tem 6), os mesmos para todos os cânceres — não
  foi falha de download (ver `docs\FONTE_DOS_DADOS.md`). Para comparar anos,
  o Escudo usa a média dos meses disponíveis × 12; os totais do período
  são os registrados. O ano incompleto aparece com marcador e a Lia avisa.
- **Projeção de tendência**, não previsão: sai da reta dos anos
  observados, com faixa e teste de acerto.

---

## Estrutura do projeto

```
dashboard/     → o painel (app.py), as páginas (pages/apoio.py, pages/onde_ser_atendida.py,
                 pages/hospitais_cancer.py),
                 o rosto da Lia e os testes de aceitação
algoritimos/   → inteligencia.py (única fonte dos números), lia.py, passeio.py,
                 entendimento.py + assistente.py + ia_linguagem.py (caixa "Pergunte à Lia"),
                 apoio.py + apoio_busca.py, onde_atendida.py + unidades_saude.py,
                 hospitais_oncologia.py, glossario.py, localizacao.py,
                 configuracao_geografica.py, conversa.py; testes e gabaritos
etl/           → carga, download (SIH, população, SIA, SIM, CNES, centros), conferências e testes
analises/      → base pública usada pelos testes (base_preditiva_2013_2025.csv)
dados_geograficos/ → catálogo conferido de serviços de Rio Claro e a lista de hospitais
                 habilitados em oncologia (Ministério da Saúde); o arquivo com as posições
                 (hospitais_oncologia_br_geo.csv) é gerado no computador de quem usa
docs/          → LIA.md, IA_DO_ESCUDO.md, FONTE_DOS_DADOS.md, INTEGRACAO_GEOGRAFICA.md, INVENTARIO_DO_CODIGO.md
banco/         → escudo_feminino.db (não versionado; no site único, o painel monta o seu banco do Parquet)
etl/exportar_banco_parquet.py e algoritimos/fonte_parquet.py → ponte entre o banco e o Parquet (ver "Dados em Parquet")
```

O que saiu na limpeza de 09/2026 (cadeia das 13 tabelas, chat de
terminal, scripts avulsos) e por quê: `docs\INVENTARIO_DO_CODIGO.md`.

## Metodologia — limites que o sistema respeita

- Nenhuma resposta afirma causa a partir de uma correlação ou tendência.
  **A inteligência calcula, a IA só explica.**
- Números pequenos (média de menos de 10 internações por ano) aparecem
  sempre com aviso de que variações podem ser acaso.
- Mês ausente não é zero; ano incompleto não é ano normal.
- Projeção é "projeção de tendência", nunca previsão de casos.
- Dinheiro é sempre "valor hospitalar registrado no SIH/SUS": não é
  orçamento nem custo total do tratamento. O Escudo não calcula orçamento.
- Internação não é pessoa (a mesma mulher pode ser internada várias vezes),
  e APAC (quimio e radio) também não é número de mulheres.
- **SIH x SIM não se subtraem.** O SIH só conta a morte durante uma
  internação por câncer; o SIM conta toda morte por câncer, em qualquer
  lugar. Em Rio Claro, em 2023, foram 71 mortes pelo SIM e 10 óbitos na
  internação: o Escudo mostra os dois e não explica a diferença.
- O ranking por 100 mil mulheres conta onde a mulher **mora**; "cidades
  que mais tratam" conta onde a internação **acontece**. São perguntas
  diferentes, e a diferença é justamente o fluxo de pacientes.
- A distância até um hospital é em **linha reta entre os centros das
  cidades**; hospital de câncer pelo SUS não se escolhe por proximidade, a
  regulação (CROSS) decide.
- **Hospital habilitado não é vaga.** A lista do Ministério (habilitação 2023)
  diz onde há serviço habilitado; o acesso é pela unidade de saúde e pela
  regulação. Não se ranqueia hospital nem se diz qual é melhor.
- Nada que identifique paciente entra no banco ou no GitHub.
- Toda recomendação é apoio à decisão — a responsabilidade final é do
  gestor responsável.
