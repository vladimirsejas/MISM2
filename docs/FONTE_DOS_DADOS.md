# Fonte dos dados — o que o DATASUS oferece e o que não oferece

## De onde vêm os números

Internações hospitalares do SUS (**SIH/SUS, arquivos RD — AIH
reduzida**) do Estado de São Paulo, baixadas do DATASUS com o
`pysus`, de 2013 a 2025. Filtros (os mesmos em todos os cânceres):

- mulher: `SEXO == "3"`;
- residência: **não filtra mais** (desde 10/2026). O Estado conta o
  atendimento em SP, inclusive moradoras de outros estados, que a carga
  grava como `OUTRO_ESTADO`. A cidade de residência vem de `MUNIC_RES`
  (Rio Claro = `354390`) e as cidades seguem contadas por residência.
  Os CSVs baixados antes de 10/2026 (exceto o colorretal) só tinham
  moradoras de SP (`MUNIC_RES` começando com `35`);
- câncer pelo diagnóstico principal (`DIAG_PRINC`): mama `C50`, colo
  do útero `C53`, colorretal `C18`–`C20`, ovário `C56`, pulmão `C34`,
  tireoide `C73`, pele não melanoma `C44`.

O ano é o de **competência** da AIH (`ANO_CMPT`, o mês em que a
internação foi processada), não necessariamente o da internação.

## Meses que o DATASUS não oferece

Em 23/09/2026, `etl/completude_meses.py` mostrou que **35 dos 156
meses** de 2013 a 2025 não existem nos arquivos — **os mesmos meses
nos 7 cânceres**. O `etl/baixar_sih_sp.py` consultou o DATASUS de
novo, e a fonte **não lista** esses arquivos mensais (confirmado para
2013: o DATASUS oferece 10 arquivos, sem fevereiro e março —
`2013/02: NÃO LISTADO pelo DATASUS`; a lista final do script completa
a conferência dos outros anos). **Não foi falha de download do
projeto** — o autor já sabia disso antes da conferência.

| Ano | Meses disponíveis | Meses que faltam na fonte |
|---|---|---|
| 2013 | 10 | fev, mar |
| 2014 | 10 | mar, ago |
| 2015 | 8 | mar, jun, jul, set |
| 2016 | 9 | jan, fev, nov |
| 2017 | 11 | jan |
| 2018 | 6 | jan, abr, mai, out, nov, dez |
| 2019 | 7 | mar, jul, ago, out, dez |
| 2020 | 8 | fev, mai, set, nov |
| 2021 | 11 | jan |
| 2022 | 10 | jul, ago |
| 2023 | 11 | abr |
| 2024 | 8 | fev, jun, ago, dez |
| 2025 | 12 | — |

Para refazer a conferência: `py etl\completude_meses.py` (lê os CSVs)
e `py -3.12 etl\baixar_sih_sp.py` (consulta o DATASUS; o `pysus` não
funciona no Python 3.14). O `baixar_sih_sp.py` só troca os CSVs se
vierem os 156 meses; com a fonte como está isso nunca acontece, então
use `--aceitar-lacunas-da-fonte`: ele troca pelos meses que existem, mas
só se o único problema for "a fonte não lista o mês" (erro de download
de verdade continua barrando). Os atuais vão para `dados\_backup_<data>\`.

## Como o Escudo lida com isso

Um ano com meses faltando tem total menor **sem que menos mulheres
tenham sido internadas**. Comparar esses totais criava quedas e
saltos falsos (o "salto de 2025" era só 2025 ter os 12 meses; a
"queda de 2024" eram 4 meses a menos).

- **Para comparar anos** (evolução, ritmo, anos fora do padrão,
  comparação com o Estado, projeção de tendência, radar), cada ano
  vale a **média dos meses disponíveis × 12**
  (`inteligencia.ajustar_meses`). O número de meses de cada ano vem
  do Estado: o arquivo que falta é o do Estado inteiro, então falta
  também para cada cidade.
- **Totais do período** (quantas internações, óbitos, valor
  registrado, letalidade) são sempre os **registrados**, sem ajuste.
- O painel mostra o ano incompleto com **marcador vazado** no gráfico
  de Evolução (o registrado aparece ao passar o mouse), e a caixa de
  confiabilidade e a Lia avisam quais anos estão incompletos.

**Limite:** a média × 12 supõe que os meses que faltam se parecem com
os que existem. Em cidade pequena, um ano com 6 ou 7 meses é uma
estimativa menos firme — por isso o aviso fica sempre visível.

Por mês, no Estado, o crescimento é suave em todos os cânceres (mama:
1.387, 1.557, 1.794, 1.908 e 1.982 AIHs por mês de 2021 a 2025), o
que confirma que os saltos anuais vinham da falta de meses.
