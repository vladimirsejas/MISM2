# Apoio à mulher: cobertura por tipo de câncer (10/2026)

Registro do que foi feito depois que o autor apontou que o Apoio girava em torno do câncer de mama e que quem
perguntava de outro câncer ("tenho câncer no intestino") recebia mamografia.

## O defeito (medido antes de mexer)

- Só **2 das 8 portas** eram de um câncer (mama e colo do útero). Dos sete cânceres que o Escudo acompanha, **cinco
  não tinham conteúdo próprio**: colorretal (5 menções, todas de hospitais), ovário (1), pulmão, tireoide e pele
  (nenhuma). O corpo do útero (endométrio) também não existia.
- A busca (`apoio_busca.py`) comparava só a semelhança de palavras, então "câncer no intestino" caía em mamografia ou em
  "Rede Feminina". Até "quero informações sobre câncer de mama" levava à Rede Feminina (verificado no código antigo).
- Palavras soltas ("caroço", "nódulo") estavam no vocabulário da mama e decidiam o câncer sozinhas.

## O que mudou

| Onde | Mudança |
|---|---|
| `algoritimos/apoio.py` | Porta nova **Outros cânceres** na mesma lâmina "Encontre um caminho" (as 8 portas de antes continuam, na mesma ordem). 7 itens novos: um cartão por câncer (intestino, ovário, pele, pulmão, tireoide, corpo do útero) e o das páginas do INCA para os tipos que o guia não detalha. Campo `cancer` em cada item (a que câncer ele é específico; vazio = serve a todos) e `topicos` (o que é, fatores de risco, sinais, prevenção x rastreamento, como se investiga, tratamento, depois do diagnóstico). Os itens de mama e colo que já existiam foram marcados, sem reescrever. |
| `algoritimos/apoio_busca.py` | **Trava por tipo de câncer** antes da semelhança de palavras: quem cita um câncer não vê conteúdo específico de outro. Cartão principal do câncer citado ganha prioridade. Dois cânceres na mesma frase, ou "câncer de útero", viram uma pergunta de volta (colo ou corpo?). Câncer que o guia não detalha: diz isso e aponta o INCA. Palavra ambígua sozinha ("caroço", "sangramento", "barriga") pergunta em que parte do corpo é. Sintoma com pista de um câncer mostra o texto fixo de sintoma **mais** um botão para os sinais daquele câncer. "E os sinais?" segue o câncer em foco (só memória da sessão). Falha inesperada na consulta vira aviso seguro. |
| `dashboard/pages/apoio.py` | Passa à busca o câncer em foco da resposta que está na tela; atalho da porta nova. Nenhuma mudança visual no resto. |
| Testes | `teste_apoio_cancer.py` (novo, independente), `gabarito_apoio_cancer.json` (40 perguntas às cegas), cenários novos em `dashboard/teste_apoio_tela.py`, e o teste das "8 portas" passou a exigir as 8 de antes **mais** a nova (a intenção dele foi mantida). Entrou no GitHub Actions. |

## Matriz de auditoria

Situação de verificação: **fonte consultada** = a página oficial foi localizada; **conteúdo conferido** = o texto foi
comparado com a página; **a confirmar** = ainda falta essa comparação.

| Câncer | Itens antes | Itens agora | Lacunas encontradas | Fonte (INCA) | Consulta | Situação | Testes |
|---|---|---|---|---|---|---|---|
| Mama | ~17 | iguais (marcados `cancer=mama`) | nenhuma de cobertura | (já no catálogo) | 24/09/2026 em diante | como antes | A2, A3, B, D16 |
| Colo do útero | ~6 | iguais (marcados `cancer=colo`) | nenhuma de cobertura | (já no catálogo) | 24/09/2026 em diante | como antes | A2, A3, B, D16 |
| Colorretal (intestino) | 0 próprio | `cancer_intestino` + `jornada_exame_intestino` | sem sinais, exames, rastreamento x sintoma, passo a passo do FIT e da colonoscopia | `.../tipos/intestino/...` e notícia do INCA de 21/05/2026 | 18/10/2026 | **rastreamento (FIT, 50 a 75 anos) conferido na notícia do INCA**; resto do cartão a confirmar | A4-A7, B, C4, G, I |
| Ovário | 0 próprio | `cancer_ovario` | sem nada; "não há rastreamento" não dito | `.../tipos/ovario/versao-para-populacao` | 18/10/2026 | **a confirmar** | A4-A7, B, C3, G |
| Pele não melanoma | 0 | `cancer_pele` | sem nada; melanoma não diferenciado | `.../tipos/pele-nao-melanoma/versao-para-populacao` | 18/10/2026 | **a confirmar** | A4-A7, B, C3, G |
| Pulmão | 0 | `cancer_pulmao` | sem nada; tabaco e cessação não ditos | `.../tipos/pulmao/versao-para-populacao` | 18/10/2026 | **a confirmar** | A4-A7, B, C3, G |
| Tireoide | 0 | `cancer_tireoide` | sem nada | `.../tipos/tireoide/versao-para-populacao` | 18/10/2026 | **a confirmar** | A4-A7, B, C3, G |
| Corpo do útero (endométrio) | 0 | `cancer_corpo_utero` | não existia; risco de confundir com colo e ovário | `.../tipos/corpo-do-utero/versao-para-populacao` | 18/10/2026 | **a confirmar** | A4-A7, B, C6, D1, D2 |
| Outros tipos | 0 | `inca_tipos_cancer` | cânceres fora do guia caíam em mamografia | `.../tipos/` | 18/10/2026 | **a confirmar** (link) | D6, D7 |

(`...` = `https://www.gov.br/inca/pt-br/assuntos/cancer`.)

## Limites e honestidade

- **As páginas do INCA não puderam ser abertas.** A nuvem não alcança `gov.br` (o `CLAUDE.md` já registrava isso). O
  conteúdo dos seis cartões foi escrito a partir de conhecimento geral consolidado e de trechos de busca na web de
  18/10/2026, que só citam o INCA de forma indireta. Por isso **todos levam "a confirmar"** e o cartão mostra a marca
  laranja. Os links são os que o projeto indicou; o endereço de cada um também ainda precisa ser aberto.
- Para tirar a marca: abrir a página, comparar o texto do cartão (`apoio.py`, procurar `cancer_`), corrigir o que
  divergir e então trocar a data em `conferido` e apagar o `confirmar`. Itens que dependem de regra vigente merecem
  atenção especial: **rastreamento colorretal** (a busca citou notícias sobre o teste de sangue oculto nas fezes no SUS,
  que não foram confirmadas; por isso o cartão **não diz idade nem intervalo**) e **tomografia para pulmão**.
- Regras clínicas seguidas: nada de diagnóstico, remédio, dose ou promessa de cura; sintoma "não confirma câncer";
  rastreamento de ovário, tireoide, pele, pulmão e corpo do útero **não é apresentado como recomendação para todas as
  mulheres**; idade e intervalo de exame não entram (dependem das diretrizes vigentes e do histórico). Não foi
  criado nenhum telefone, hospital ou serviço novo; o único número citado é o 192 que o guia já usava.
- **Gemini:** continua desligado por padrão no Apoio e só escolhe uma porta numa lista fechada (agora com a porta
  "Outros cânceres"); nunca escreve texto clínico. Testado só com **dublê** na nuvem (erro, `None`, lixo, texto, id
  inexistente, sem chave). **Não houve teste com a API real**; isso depende do notebook do autor (`py algoritimos\testar_gemini.py`
  e ligar o toggle no Apoio).
- Medição às cegas (`gabarito_apoio_cancer.json`): 1ª execução 36/40 (tipo de resposta) e 25/28 (câncer certo); a causa
  das falhas foi corrigida, chegando a 40/40 e 28/28, mas o conjunto deixou de ser independente. Perguntas da equipe, não
  de usuárias reais. Teste com pessoas de verdade continua pendente.
- A pergunta digitada nunca é gravada; o que a página guarda na sessão é só **qual câncer está em foco** (por exemplo
  `ovario`), para o "e os sinais?" funcionar, e some quando ela clica em outro botão.

## Pendências para a equipe

1. Conferir os seis cartões e o das páginas do INCA com as páginas oficiais (ver acima).
2. Confirmar o que a rede de Rio Claro oferece para cada câncer (por exemplo, quem recebe o encaminhamento de dermatologia
   ou de ginecologia oncológica): hoje o cartão só aponta o caminho geral (unidade de saúde, regulação/CROSS).
3. Revisar o vocabulário popular novo (`apoio_busca.EXTRA` e `PISTAS`).
4. Testar com pessoas reais e com o Gemini real.

## Atualização de 18/10/2026 (tarde): fontes oficiais anexadas pelo autor

Duas fontes reais (impressões em PDF, lidas como imagem) entraram no catálogo:

1. **INCA, notícia de 21/05/2026, "SUS adota novo exame para detectar câncer de intestino antes de sintomas".** Conferido nela:
   o Ministério da Saúde adotou o teste imunoquímico fecal (FIT) como exame de referência no SUS para homens e mulheres de
   **50 a 75 anos, sem sintomas**; kit coletado em casa e enviado ao laboratório; sem preparo do intestino, sem dieta e com uma
   amostra; resultado com sangue oculto leva a exames complementares, e a **colonoscopia é o padrão-ouro** (olha o intestino e
   retira pólipos). **Não conferido** (a página não diz): de quanto em quanto tempo repetir o teste e onde, em Rio Claro, se pega o
   kit e se faz a colonoscopia pelo SUS. O texto **não** traz intervalo, e o catálogo também não. Resultado: cartão `cancer_intestino`
   com o rastreamento confirmado e o novo cartão **`jornada_exame_intestino`** (6 passos: unidade de saúde, rastreamento ou sintomas,
   FIT, FIT positivo, regulação, resultado).
2. **Página institucional do ICESP.** Conferido: unidade do HC-FMUSP com atendimento exclusivo pelo SUS; 4 unidades com endereço
   (Av. Dr. Arnaldo, 251; Osasco; Farmácia Ambulatorial, R. da Consolação, 2049; Itaci, R. Galeno de Almeida, 148); telefone
   (11) 3893-2000; números de fevereiro de 2024. O cartão `icesp` ganhou isso. A regra de acesso (pela regulação, não é porta de entrada)
   continua a da página "Como ser atendido".

A busca passou a distinguir **pedido de caminho** ("onde faço colonoscopia pelo SUS?") de **visão geral** ("o que é o teste FIT?"):
o primeiro abre a jornada, o segundo o cartão do câncer. "FIT" e "teste imunoquímico" agora reconhecem o intestino.

### Centros de referência sugeridos pelo autor (triagem, NÃO cadastrados)

Lista recebida em 18/10/2026, sem fonte. Regra do projeto: só entra serviço que dê para conferir.

| Sugestão | Situação |
|---|---|
| CAISM/Unicamp (colo, endométrio, ovário) e ICESP | **Já estão** no catálogo (`caism_unicamp`, `icesp`); o CAISM foi completado em 18/10/2026 com o texto do site do hospital (só SUS, 130 leitos, ~70 mil atendimentos em 2023, radioterapia, quimioterapia, equipe multiprofissional, paciente referenciada). Os detalhes "cirurgia robótica", "quimioterapia intraperitoneal" e "pesquisa em síndromes hereditárias" não têm fonte aqui e **não foram incluídos**. |
| HC da Unicamp (dermatologia oncológica) | O HC da Unicamp **já está** como hospital de câncer; o ambulatório de dermatologia oncológica **não foi confirmado**. |
| HC da USP/ICESP (melanoma: Mohs, terapia-alvo BRAF) | Sem fonte; o guia trata câncer de pele **não melanoma** e não detalha tratamento por mutação. |
| HCPA/UFRGS (Porto Alegre) e Hospital São Paulo/UNIFESP (colorretal) | **Não cadastrados.** O HCPA fica em outro estado e não é caminho de encaminhamento do SUS-SP; o HSP/UNIFESP precisa de página oficial e de regra de acesso. |

| Gastrocentro/Unicamp (diagnóstico do aparelho digestivo) | **Cadastrado** na porta Outros cânceres (`gastrocentro_unicamp`, 18/10/2026), só com o que a página diz (cerca de 700 exames gratuitos por mês, sistema hierarquizado). **A página não informa** quais exames faz, quem é encaminhada nem se atende Rio Claro/Piracicaba: ficou "a confirmar". Não foi para a área de hospitais de câncer, porque não é hospital oncológico completo. |
| Hospital Estadual Sumaré (HES-Unicamp) | **Não cadastrado.** Hospital geral 100% SUS; a página não menciona oncologia e a abrangência (Americana, Hortolândia, Monte Mor, Nova Odessa, Santa Bárbara d'Oeste e Sumaré, DRS 7) não inclui Rio Claro. Prêmios, orçamento e equipamentos da página não entram: não respondem "onde procurar cuidado". |

| UNESP Botucatu (oncologia, quimioterapia, centro oncológico) | O **HC da Faculdade de Medicina de Botucatu já está** no catálogo (`hc_botucatu`, página oficial do serviço de oncologia). O **Hospital Estadual de Botucatu (HEBo)** como local de quimioterapia e imunoterapia **não foi cadastrado**: a única fonte da sugestão é um cartão do Poupatempo que a nuvem não abre; entra com a página oficial. "Centro oncológico" em expansão e terapia CAR-T: sem fonte, não entram. |
| UNESP Botucatu (disciplina de oncologia, residência, Liga do Câncer, laboratório translacional, OncoToxLab, congresso) | **Ensino e pesquisa, não atendimento.** Não respondem "onde procurar cuidado" e o guia não os cadastra como serviço. O aconselhamento genético para famílias com histórico é um serviço possível: só entra com página oficial dizendo quem atende e como se chega. |

Para entrar: página oficial do serviço, quem atende pelo SUS, se exige encaminhamento e abrangência. Hospital de ensino ou de pesquisa
**não é porta de entrada**; a vaga vem pela regulação.

### Do plano geral (três frentes) — o que já existe e o que fica para decidir

- **Já feito:** 8 grupos de câncer com cartão próprio, trava de tipo na busca, jornada do intestino, ICESP completo, fontes e datas por item,
  marca "a confirmar" visível, testes antes e depois.
- **Para decidir com o autor:** jornada própria para ovário/endométrio (sangramento anormal, ultrassom, biópsia, ginecologia oncológica),
  tireoide (nódulo, ultrassom, punção) e pele (UBS, dermatologia, dermatoscopia, biópsia); lista nacional de CACON/UNACON (planilha do
  Ministério da Saúde de julho de 2026, que a nuvem não consegue abrir); validade (`valido_ate`) por item; confirmar com a Secretaria de
  Saúde de Rio Claro onde se faz FIT e colonoscopia pelo SUS.
