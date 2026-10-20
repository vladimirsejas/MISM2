# Roteiro da apresentação à Secretaria de Saúde (terça-feira, 20/10/2026)

Documento de apoio, só texto. Não muda nada no sistema. Todos os números abaixo vêm do banco do autor, do que ele
conferiu no notebook ou das listas oficiais; onde algo ainda precisa ser conferido antes de falar, está marcado com ☐.

## 1. A ideia central (30 segundos)

> O Escudo Feminino reúne os dados de internação por câncer em mulheres do SUS (SIH/SUS, 2013 a 2025) e mostra o que
> acontece em Rio Claro comparado ao Estado de São Paulo. Ele não afirma causas e não fala em orçamento: aponta o que
> merece atenção no planejamento, com a fonte e o limite de cada número. E tem uma segunda parte, o Apoio à Mulher,
> que ajuda uma mulher a achar o próximo passo na rede de saúde.

Duas frases que protegem você: **"são internações, não casos novos"** e **"é um guia de onde procurar, não orientação médica"**.

## 2. Roteiro de 10 a 12 minutos (tela a tela)

| Min | Onde | O que mostrar | O que dizer |
|-----|---------------|------------------------------|--------------------------------------------------|
| 0–1 | Primeira tela | Município Rio Claro, os 3 números, a régua de meses | "1.668 internações por câncer em mulheres de Rio Claro, 140 óbitos durante a internação, R$ 4.022.281 de valor hospitalar registrado no SIH/SUS. Não é orçamento nem custo total: é o que o SIH registrou." Apontar a régua: "o vazio é mês que o DATASUS não oferece, não é zero." |
| 1–3 | Aba **Panorama** | Barras por câncer; trocar a medida (internações, valor, óbitos, dias) | "Qual câncer mais leva as mulheres da cidade ao hospital." Ler o texto de leitura que está abaixo do gráfico. |
| 3–4 | Aba **Evolução** | Linha da cidade e do Estado, anos fora do padrão, caixa de confiabilidade | "A projeção é de **tendência**, com teste de acerto: é um exercício, não uma previsão de casos novos." |
| 4–6 | Aba **Investigar** | Fluxo de pacientes e comparar cidades | "O Estado conta quem é atendida nos hospitais de SP, inclusive mulheres de outros estados (17.991 internações). A cidade conta por residência." Na comparação: "só o que não depende do tamanho da cidade." |
| 6–7 | Aba **Planejamento** | Radar do futuro | "Onde a cidade pode ter problema se nada mudar. Aponta atenção, não decide." |
| 7–9 | **Lia** (lateral) | 3 perguntas escritas na caixa (seção 5) | "A Lia calcula com os dados e o Gemini só ajuda a redigir; se a IA falha, ela responde direto dos cálculos." |
| 9–11 | **Apoio à mulher** | "Prevenção e exames" → passo "Ainda não fiz o exame" (Cadu, unidades) → "Unidades, telefones e como chegar" → Santa Casa de Rio Claro | "Para quem não sabe por onde começar. Cada cartão tem fonte, data de conferência e a marca **'a confirmar'** quando falta confirmar algo." |
| 11–12 | **Apoio → Hospitais no Estado → "Ver todos os hospitais habilitados no mapa"** (☐ só se o mapa já tiver as posições no notebook: `py etl\gerar_hospitais_oncologia_geo.py`) | Escolher Rio Claro: "o hospital habilitado mais próximo, em linha reta, é a Santa Casa". Trocar para Brasil: "são 361 habilitados no país, 88 em SP". Dizer: "o mapa mostra onde ficam; não explica por que as pessoas vêm de fora". |
| 11–12 | Aba **Método** e próximos passos | Fontes e limites | "O que vem: mapa por área de USF (com o projeto do Kauê), taxa por 100 mil mulheres, hospitais habilitados em oncologia." |

## 3. Números que podem ser ditos (e como dizê-los)

| Número | Fonte | Como dizer / ressalva |
|-----------------------------------|-------------------------|----------------------------------------|
| 1.668 internações, 140 óbitos, R$ 4.022.281 (Rio Claro) | SIH/SUS no banco, 7 cânceres | Internações, não pessoas nem casos novos; só os meses que o DATASUS oferece. Valor = valor hospitalar registrado, não custo do tratamento. |
| 464.340 internações no Estado; 17.991 de mulheres de outros estados | Banco do autor | O Estado conta o atendimento nos hospitais de SP. |
| **89,1%** das internações por câncer do banco (413.557 de 464.340) foram em hospitais da lista oficial de habilitados em SP (88 estabelecimentos) | `py etl\cruzar_hospitais_oncologia.py`, rodado em 18/10/2026 | A lista é do Ministério da Saúde, **habilitação 2023**; o banco vai de 2013 a 2025. Contam internações, não pessoas. Não dizer o motivo do restante (10,9%): pode ser hospital geral, habilitação antiga ou nova. |
| **88** estabelecimentos habilitados em oncologia em SP (61 UNACON, 14 CACON, 8 hospitais gerais com cirurgia oncológica, 5 serviços de radioterapia) e **361** no Brasil | Ministério da Saúde (planilha de 2023) | Estar na lista não é ter vaga: o acesso é pela regulação. *(Corrigido em 18/10: a primeira contagem, 80, perdeu 8 linhas da planilha por células mescladas.)* |
| Santa Casa de Rio Claro: **UNACON** habilitada na cidade, 1.711 internações no SIH | Lista do Ministério + banco | Telefone (19) 3535-7000 vem do CNES e da lista da Secretaria de 2021: "a confirmar". |
| Na mama, 89% das moradoras de Rio Claro se tratam na cidade; 87% das mulheres de outros estados atendidas na mama são em Barretos | Fluxo de pacientes no banco | Confirmar na tela da aba Investigar antes de citar (☐). |

## 4. O que NÃO dizer

- Nada de causa ("por que aumentou"): o Escudo detecta, não explica.
- Nada de orçamento ("a cidade precisa investir R$ X"): só "merece atenção no planejamento".
- Nada de "vai aumentar" ou "IA preditiva": é "a tendência aponta" e "projeção de tendência".
- Não chamar internação de "caso" nem de "pessoa".
- Não dizer que um hospital "trata todos os cânceres" só porque está na lista (há hospitais gerais com cirurgia oncológica e serviço só de radioterapia).
- Não afirmar que o telefone ou o serviço de um cartão "a confirmar" está funcionando.

## 5. Três perguntas para a Lia na demonstração (ensaiar antes)

Use perguntas que o sistema já foi testado para entender. **Ensaie no notebook, com o banco real**, e anote o que a Lia responde:

1. "O câncer de mama está aumentando em Rio Claro?"
2. "Quais cidades têm mais casos proporcionalmente?" (usa a população do IBGE; já respondeu com o banco real em 17/10)
3. "Onde faço mamografia pelo SUS?" (no Apoio, texto fixo, sem IA)

Se a internet ou o Gemini falhar, a Lia responde direto dos cálculos; vale saber como isso aparece (selo "sem IA").

## 6. Perguntas prováveis da Secretaria

- **"Isso mostra casos novos de câncer?"** Não. Mostra internações no SUS. Para casos novos, o caminho são os registros de câncer (RHC/RCBP) e o SIM para mortalidade, que o projeto ainda não usa como base principal.
- **"Por que Rio Claro tem tantas/poucas?"** O Escudo não explica causa. Mostra o ritmo, compara com o Estado e com cidades parecidas.
- **"A IA está certa?"** Os números vêm sempre dos cálculos; o texto da IA é conferido e descartado se tiver número que não está nos cálculos. A IA não escreve sobre serviços de saúde no Apoio: o texto vem de um catálogo conferido.
- **"Os serviços do Apoio estão atualizados?"** Cada cartão tem fonte e data; os marcados "a confirmar" ainda dependem de verificação. Por isso o Apoio se apresenta como guia de onde procurar.
- **"Os dados são de pacientes?"** O banco guarda registros de internação **sem identificação**: nunca CEP, nascimento ou número da AIH. O texto das perguntas feitas à Lia não é gravado (só se conta o assunto, e relato de violência ou sintoma nem isso).
- **"Como uma mulher faz um exame pedido pelo médico?"** O Apoio segue o protocolo da Fundação (exames de média e alta complexidade, rev. 03, 2026): o pedido fica com o funcionário da unidade, que aciona a Central Municipal de Regulação; a Central e o médico auditor analisam (pedido incompleto volta à unidade); agendado, a Central avisa a unidade e a unidade avisa a paciente. Pedido de médico ou clínica particular também vale, em receituário próprio com CID e justificativa. Está marcado "a confirmar" porque veio do protocolo e de chefias, não de publicação aberta.
- **"O que é o Cadu? É da Prefeitura?"** Pela chefia de uma UBS (19/10): só faz agendamento para as unidades de saúde e é externo à Fundação. Quem opera o serviço **não foi identificado**: o Escudo não afirma contrato nem empresa.
- **"CEAD e AME são a mesma coisa?"** Não. O CEAD é municipal, da Fundação (Av. 24, nº 1040, entre as ruas 8 e 9; segunda a sexta, 7h às 16h; telefone ainda a confirmar). O AME é do Estado. Pelo protocolo de mama da Fundação, nódulo suspeito, BI-RADS 4 e 5 e alto risco vão ao mastologista do CEAD; câncer confirmado vai à Santa Casa.
- **"A mamografia começa aos 50 ou aos 40?"** O Apoio mostra a regra do Estado (50 a 69 anos, sem pedido, Mulheres de Peito). O protocolo municipal de mama (rev. 01, 2026) fala de 40 a 69 anos, anual. O Apoio **ainda não traz a regra municipal**: está nos próximos passos.
- **"Dá para ver por bairro ou por unidade de saúde?"** Ainda não. É o próximo passo, com o projeto do Kauê (áreas de USF), só com contagens agregadas e supressão de números pequenos.

## 7. Checklist do ensaio (segunda-feira, no notebook que vai à apresentação)

1. `git branch --show-current` (deve ser `main`), `git pull` e `git log --oneline -3`.
2. Abrir pelo `Abrir Escudo Feminino.bat`, com o painel fechado antes. Conferir a lateral (Lia) aberta.
3. ☐ Passar por todas as abas com o banco real, sem erro na tela.
4. ☐ Testar o Gemini (`py algoritimos\testar_gemini.py`) e as 3 perguntas da seção 5.
5. ☐ Apoio: "Prevenção e exames", "Meu exame deu alterado", "Não sei por onde começar". Abrir os botões do Cadu (Google Play, App Store, página da Prefeitura), o link da vacina HPV e "Unidades, telefones e como chegar".
6. ☐ Conferir o número de Rio Claro na aba Investigar (89% na mama e 87% em Barretos) antes de citar.
7. Plano B: capturas de tela de cada aba e um vídeo curto do painel, salvos fora do navegador, caso o Wi-Fi ou o notebook falhe.
8. Não rodar nenhuma carga de dados nem mexer em `banco\` perto da apresentação. Fechar o painel antes de qualquer script que leia o banco.
9. Congelar o código: depois do ensaio, só correção de erro.

## 8. Próximos passos para citar (sem prometer data)

1. Mapa por área de USF, com o projeto do Kauê (só agregados, com supressão de números pequenos).
2. Hospitais habilitados em oncologia: lista oficial do Ministério já no projeto e conferida com o CNES; próxima etapa é mostrar os mais próximos de cada cidade.
3. Apoio mais curto e guiado: uma pergunta por vez, resposta com próximo passo e contato.
4. Mais fontes de dados já carregadas (SIA, SIM, CNES, população) entrando na Lia.
