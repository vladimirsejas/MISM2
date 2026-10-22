# Inventário do painel principal (gerado do código em 20/10/2026)

Gerado a partir de `dashboard/app.py` (as chamadas `pergunta(...)`). Serve para a regra do projeto: **cada informação tem uma casa só**, 
e todo bloco diz de quem são os números (🌎 Estado ou 📍 cidade). Para refazer: procurar `pergunta(` em cada seção `if aba == ...`.

| Aba | Pergunta | Números de quem |
|---|---|---|
| Panorama | (título montado em código) | 📍 cidade escolhida |
| Panorama | O que chama atenção no …? | 📍 cidade escolhida |
| Evolução | Como as internações por … mudaram de … a …? | 📍 cidade escolhida |
| Evolução | Qual modelo errou menos ao prever anos que já conhecemos? | 📍 cidade escolhida |
| Rede hospitalar | De onde vêm as mulheres de outros estados atendidas em São Paulo? | 🌎 Estado de SP |
| Rede hospitalar | Em quais estados elas moram? | 🌎 Estado de SP |
| Rede hospitalar | Quais hospitais de SP mais atendem mulheres de outros estados? | 🌎 Estado de SP |
| Rede hospitalar | Como é o atendimento em um hospital específico? | 🌎 Estado de SP |
| Rede hospitalar | Quantas internações … registrou em cada ano? | 🌎 Estado de SP |
| Rede hospitalar | A parcela de mulheres de fora está crescendo? | 🌎 Estado de SP |
| Rede hospitalar | Quem vem de fora, de qual câncer e para qual hospital? Pesquise tudo | 🌎 Estado de SP |
| Rede hospitalar | Quem é atendida nos hospitais de …, e para onde vão as moradoras? | 📍 cidade escolhida |
| Rede hospitalar | De quais cidades de SP vêm as mulheres de fora? (mapa ou barras; dentro da visão "Mulheres de fora da cidade atendidas na cidade") | 📍 cidade escolhida |
| Investigar | Qual câncer cresce mais rápido, e quando foi o ponto mais alto? | 📍 cidade escolhida |
| Investigar | A idade das mulheres internadas por câncer mudou? | 📍 cidade escolhida |
| Investigar | A idade das mulheres internadas … mudou? | 📍 cidade escolhida |
| Investigar | Como … se compara com outra cidade? | 📍 cidade escolhida |
| Planejamento | Se nada mudar, onde … pode ter problema até …? | 📍 cidade escolhida |
| Planejamento | Crescimento x gravidade: onde fica cada câncer? | 📍 cidade escolhida |
| Método | Como ler estes dados | — |

## Como as abas se dividem hoje

- **Panorama**: o quadro geral dos 7 cânceres e a ficha do câncer em foco.
- **Evolução**: como as internações mudaram, com Estado, anos fora do padrão e projeção de tendência.
- **Rede hospitalar** (nova, 20/10/2026): de onde vêm as mulheres de outros estados, hospitais, mapa e a tabela de fluxo; no fim, a cidade escolhida.
- **Investigar**: só perguntas sobre a cidade escolhida (câncer que cresce, idade, comparação com outra cidade).
- **Planejamento**: radar do futuro e quadrante crescimento x letalidade.
- **Método**: como ler, fontes e limites.

## O que o painel NÃO mostra ainda (só a Lia usa)

- SIA/SUS (quimio e radio por APAC), SIM (mortalidade por município) e CNES (leitos e equipamentos, códigos ainda sem nome).
  Entrarão no painel só depois de conferir o perfil dos códigos com o banco real (no notebook).
