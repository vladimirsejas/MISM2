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
pronto. Para fechar, feche a janela "Escudo Feminino - painel". Dá para
criar um atalho na Área de Trabalho (botão direito no arquivo → Enviar
para → Área de trabalho).

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
  residência); pastas municipais antigas (ex.: `cancer_mama_rio_claro`)
  são ignoradas com aviso, para Rio Claro não ser contada em dobro;
- recusa rodar se houver mais de um CSV na mesma pasta (não escolhe um
  sozinha);
- detecta se o CSV usa `;` ou `,`;
- guarda o **mês** de cada internação, que o Escudo usa para lidar com
  os meses que o DATASUS não oferece (ver `docs\FONTE_DOS_DADOS.md`).

Para conferir quais meses existem nos arquivos: `py etl\completude_meses.py`.
Para baixar de novo do DATASUS: `py -3.12 etl\baixar_sih_sp.py` (o
`pysus` não funciona no Python 3.14).

### Painel novo e inteligência central

O dashboard (`dashboard\app.py`) foi reescrito do zero em 09/2026: o
anterior tinha 7 abas que repetiam os mesmos números. O novo é
organizado por perguntas, em portas onde cada informação tem uma casa
só:

- **Panorama** — o que está acontecendo? Barras por internações, valor
  hospitalar registrado, óbitos ou dias, e a ficha "o que chama
  atenção" do câncer em foco.
- **Evolução** — como mudou? Linha 2013–2025 com camadas (ritmo do
  Estado, anos fora do padrão, projeção de tendência) e a caixa de
  confiabilidade da informação.
- **Investigar** — o que merece ser pesquisado? Anos fora do padrão de
  todos os cânceres, quando cada câncer aparece, faixa etária ao longo
  do tempo, download dos dados.
- **Planejamento** — se nada mudar, onde a cidade pode ter problema até
  daqui a 3 anos? O radar do futuro: cada câncer em alerta, observar ou
  estável, com os sinais, os dias de leito a mais e a linha de ação do
  INCA. Sem valores de orçamento: quem decide é o gestor.
- **Método** — como ler e o que os dados não permitem responder.

Quem conduz é a **Lia**, a guia do Escudo (ver `docs\LIA.md`): no
primeiro acesso ela aparece no centro com 4 portas de entrada; depois
fica na lateral, num balão, com os caminhos, e o painel acompanha cada
resposta dela. **Não há caixa de texto livre** (saiu por decisão do
autor): a Lia conduz só por botões. Logo abaixo dela, o **Passeio pelo
Escudo** (cartão verde-água) conta o essencial em 6 paradas, na ordem,
levando o painel a cada gráfico. Embaixo de cada gráfico vem a leitura
em texto. A tela não calcula nada: tudo vem de
`algoritimos\inteligencia.py`, que lê `internacoes` direto (não depende
da cadeia de scripts acima). O chat `algoritimos\conversa.py` continua
no repositório, fora do painel.

Testes (sem o banco):

```powershell
python algoritimos\teste_inteligencia.py
python algoritimos\teste_lia.py
python algoritimos\teste_conversa.py
python dashboard\teste_painel.py      # abre o painel e clica em tudo (~2,5 min)
py -m streamlit run dashboard\app.py
```

Cuidados que a inteligência central já aplica:
- **Uma fonte por cidade.** A carga lê só os arquivos estaduais (que já
  trazem a cidade de residência); as pastas municipais antigas são
  ignoradas. Assim Rio Claro não é contada em dobro.
- **Meses que o DATASUS não oferece.** Faltam 35 dos 156 meses de 2013
  a 2025 na própria fonte (2018 só tem 6), os mesmos para todos os
  cânceres — não foi falha de download (ver `docs\FONTE_DOS_DADOS.md`).
  Para comparar anos, o Escudo usa a média dos meses disponíveis × 12;
  os totais do período são os registrados. O ano incompleto aparece
  com marcador vazado no gráfico de Evolução, e a Lia avisa. Para isso
  a carga guarda o mês: depois de atualizar, rode a carga de novo.
- **Projeção de tendência**, não previsão: sai da reta dos anos
  observados (não do último ano), com faixa e teste de acerto.

---

## Estrutura do projeto

```
dashboard/     → o painel (app.py), o rosto da Lia e o teste de aceitação
algoritimos/   → inteligencia.py (única fonte dos números), lia.py, passeio.py,
                 configuracao_geografica.py; conversa.py + ia_linguagem.py
                 (perguntas em texto com Gemini, fora do painel hoje); testes
etl/           → carga, catálogo IBGE, completude dos meses, download e testes
analises/      → base pública usada pelos testes (base_preditiva_2013_2025.csv)
docs/          → LIA.md, FONTE_DOS_DADOS.md, INVENTARIO_DO_CODIGO.md, historico/
banco/         → escudo_feminino.db (não versionado)
```

O que saiu na limpeza de 09/2026 (cadeia das 13 tabelas, chat de
terminal, scripts avulsos) e por quê: `docs\INVENTARIO_DO_CODIGO.md`.

## Metodologia — limites que o sistema respeita

- Nenhuma resposta afirma causa a partir de uma correlação ou tendência.
- Números pequenos (média de menos de 10 internações por ano) aparecem
  sempre com aviso de que variações podem ser acaso.
- Mês ausente não é zero; ano incompleto não é ano normal (ver
  `docs\FONTE_DOS_DADOS.md`).
- Projeção é "projeção de tendência", nunca previsão de casos.
- Toda recomendação é apoio à decisão — a responsabilidade final é do
  gestor responsável.
