# Arquitetura do MISM e lugar do MISM2

O **MISM** (Monitoramento Inteligente da Saúde da Mulher) é o projeto completo,
reunido em https://github.com/MISM-Saude-da-Mulher/MISM. O **MISM2** e o trabalho
de Kauê F. Lima (https://github.com/KaueFLima/MISM) são componentes dele. Nenhum
é um projeto independente.

## Componentes

- **MISM2 (este repositório)**: módulo de inteligência e central de informações.
  Contém o painel de dados do SIH/SUS (`dashboard/`), a inteligência que calcula os
  números (`algoritimos/inteligencia.py`), a projeção de tendência validada por
  avaliação aninhada, o assistente de perguntas (Lia) com camada de segurança, as
  páginas de apoio (Apoio à mulher, Onde ser atendida, Hospitais habilitados em
  oncologia) e as cargas de dados públicos (`etl/`).
- **Componente de Kauê F. Lima**: trabalho de georreferenciamento e mapa do MISM.
- **MISM (repositório da organização)**: reúne os componentes em um só site. Ele
  incorpora o MISM2 e o estende com páginas próprias.

## Qual cópia é qual

Este repositório (`vladimirsejas/MISM2`) é a **versão de referência** do módulo: é
a que foi testada e a que o informe técnico avalia. A cópia do MISM2 dentro do MISM
pode ter páginas e ajustes a mais. Para reproduzir o que o artigo descreve, use a
versão marcada (release) deste repositório.

## Dados

Os componentes usam as mesmas fontes públicas (SIH/SUS, SIA, SIM, CNES, IBGE).
Nenhum dado pessoal e nenhum texto de pergunta de usuária fazem parte deste
repositório.

## Identificadores

Cada componente tem o seu registro com DOI próprio. O DOI do MISM identifica o
conjunto. Os registros se ligam por relações de metadados (`isPartOf` / `hasPart`),
para que a publicação de um componente nunca apareça como projeto separado do MISM.
