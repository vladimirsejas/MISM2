# Inventário das bases Escudo Feminino — 2013–2025

Este arquivo identifica as 14 bases de origem usadas na construção da base analítica pública.

O conjunto original possui 7 cânceres e 2 recortes de residência:
Rio Claro e São Paulo.

Os arquivos CSV e Parquet completos permanecem fora do repositório público. O GitHub recebe a camada analítica agregada e a documentação de controle para manter o projeto versionado sem transformar o repositório em depósito de microdados.

A base Colorretal/São Paulo tem duas versões: 91.341 registros (só moradoras de SP) e 94.005 (com 2.664 moradoras de outros estados). Desde 10/2026 o Escudo conta o atendimento em SP e usa a de 94.005 inteira; as moradoras de outros estados entram como `OUTRO_ESTADO` (ver `docs/DADOS_2013_2025.md`).

A ausência de registros em um determinado ano não significa perda da série: na base anual, o ano permanece presente com zero internações quando não há registros.