# Onde ser atendida: catálogo conferido + CNES

A página **Onde ser atendida** (`dashboard/pages/onde_ser_atendida.py`) junta duas fontes numa lista só:

- **CNES** (`algoritimos/unidades_saude.py`, arquivo em `banco\cnes`, fora do GitHub): cadastro oficial e completo das
  unidades de saúde da cidade. Não traz horário e quase não traz telefone.
- **Catálogo conferido** (`dados_geograficos/catalogo_servicos_rioclaro.json`, 164 registros de serviços públicos de Rio Claro
  vindos do MISM3 em 12/10/2026): cada item tem fonte e data de verificação, e muitos têm telefone e horário. Daqui vêm os
  dados extras das unidades de saúde e todo o **apoio à mulher** (Secretaria da Mulher, DDM, Patrulha Maria da Penha, Defensoria,
  CRAS, CREAS e acolhimento). Creche, cursos, farmácia e convivência não entram (não são saúde da mulher).

Regras: a lógica de união está em `algoritimos/onde_atendida.py` (sem Streamlit; teste `algoritimos/teste_onde_atendida.py`).
Unidade do CNES e do catálogo se cruzam pelo código CNES ou pelo nome; o telefone do CNES nunca é trocado, e só preenche
telefone/horário que faltam. Sem o arquivo do CNES a página continua útil, só com o catálogo. Item "não conferido" aparece
com ⚠. O botão **Como chegar** abre a rota no Google Maps a partir da posição de quem abre o link; **Ligar** usa o primeiro
telefone. Mapa só com coordenada cadastrada na fonte e dentro de Rio Claro; nada de ponto inventado.

A página que existia à parte ("Mapa de serviços") e o índice de CEP aproximado (IBGE/CNEFE) foram removidos por responderem
à mesma pergunta; estão no histórico do Git (commits de 12/10/2026). O catálogo envelhece: reconferir as fontes de tempos em tempos.
