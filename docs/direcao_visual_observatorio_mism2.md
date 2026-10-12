# Direção visual — Observatório MISM2

## Objetivo

Construir uma interface de inteligência em saúde da mulher voltada a gestores, pesquisadores e estudiosos. Não é um portal de atendimento à população nem uma cópia do MISM3. O MISM3 é referência de acabamento e coerência; o MISM2 terá linguagem editorial e analítica própria.

## Princípio de composição

A tela deve parecer um observatório que convida à investigação, não um conjunto de cartões padrão:
- cabeçalho editorial com **MISM2** e o nome por extenso **Monitoramento Inteligente da Saúde da Mulher**;
- município e período como controles de contexto visíveis, sem competir com o título;
- uma leitura principal em destaque e contexto metodológico junto aos números;
- visualizações organizadas como narrativa: panorama → mudança no tempo → diferenças territoriais → perguntas para investigação;
- espaços em branco, divisórias finas, grade assimétrica e poucos contornos; evitar cartões idênticos em sequência, gradientes decorativos e ícones genéricos.

## Paleta

- Berinjela: `#6B2E6F` — identidade, títulos e ações primárias.
- Tinta profunda: `#292541` — texto principal.
- Lavanda clara: `#F3ECF9` — áreas de orientação e realce.
- Lavanda média: `#A58AB8` — séries secundárias e detalhes.
- Branco: `#FFFFFF` — superfícies de leitura.
- Tons de alerta devem ser reservados a sinais reais e explicados; vermelho não será cor decorativa.

## Família de símbolos

O módulo `dashboard/simbolos_mism.py` introduz desenhos SVG originais para saúde, tendências, território, atualização, confiabilidade e pesquisa. Os símbolos partilham espessura de traço, cantos suaves e paleta lavanda/berinjela. Usar símbolos com rótulos: nunca depender apenas da cor ou do desenho para transmitir significado.

## Lia — identidade invariável

A Lia existente em `dashboard/lia_rosto.py` é o desenho de referência. Preservar pele negra, cabelo crespo curto mesclado preto/grisalho, óculos arredondados e blusa berinjela com gola clara. Não substituir por foto, avatar genérico ou personagem nova. A expressão pode mudar conforme o estado dos dados; rosto, proporções e identidade permanecem consistentes. Ela orienta e explica, mas os dados e gráficos ocupam o protagonismo do painel.

## Transparência científica

Cada indicador deve permitir identificar fonte, período, cobertura e limitações. Não inventar indicadores nem interpretar ausência de registro como zero. Alertas precisam ser sustentados pelos dados; projeções devem ser apresentadas como tendências, com limites explícitos.

## Implementação segura

Esta direção visual deve ser aplicada gradualmente em uma branch separada, sem alterar banco de dados, cálculos epidemiológicos, rotas existentes ou o conteúdo de apoio à mulher. Primeiro validar cabeçalho, hierarquia e símbolos; depois ajustar componentes e gráficos. Comparar as telas reais e executar os testes antes de integrar.
