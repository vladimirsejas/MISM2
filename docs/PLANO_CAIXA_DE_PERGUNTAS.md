# Plano: a IA volta ao Escudo (caixa de perguntas) — 17/10/2026

**Estado (17/10/2026): IMPLEMENTADO, depois de o autor aprovar ("a caixa deve ficar junto da Lia").**
O que foi feito, como foi medido e o que falta comprovar no computador do autor está em
`docs/IA_DO_ESCUDO.md`. O texto abaixo é o plano original e fica como registro da decisão.
Desvios do plano: não usa LSA (corpus pequeno demais; o Gemini faz esse papel na segunda chance) e
o motor aproveitou a árvore da Lia em vez de criar um segundo sistema de cálculo.

## 1. Por que voltar

- Ter IA é requisito do trabalho (professora). Hoje o painel mostra cálculo e
  regras fixas; o Gemini (`ia_linguagem.py`, chave no `.env`, API paga) ficou
  sem nenhum ponto de chamada desde o commit `237896f` (caixa de texto livre
  removida). O código do Gemini continua no projeto.
- A caixa antiga tinha um problema real: **vocabulário escasso e em descompasso
  com quem pergunta**. `conversa.entender` pontua palavras-chave (`ASSUNTOS`,
  `SINONIMOS_CANCER`). "Caroço no peito", "tá piorando?", "morre muita gente?"
  não casam com nada e a pergunta cai no assunto errado ou no genérico.

## 2. O que o MISM3 fez (lido em 17/10/2026, repositório vladimirsejas/mism3)

Resultado medido no MISM3: o "assistente anterior" (classificador + regras,
parecido com o `conversa.py` de hoje) acertava o destino específico em
**40%**; o orientador novo, em **87%** na primeira rodada (91% depois de
ajustes — o próprio documento deles avisa que o 87% é o número honesto).

O que mudou, em ordem de importância:

1. **Destinos fechados.** O sistema não "responde qualquer coisa": ele aponta
   para uma lista fixa de destinos que o projeto já tem e verificou (161 lá).
   Nunca inventa.
2. **Vocabulário popular escrito à mão para cada destino**
   (`VOCABULARIO` em `pipeline/indice_orientacao.py`): "sem grana pra comer"
   leva ao CRAS. É conhecimento do domínio, revisável linha a linha.
3. **Quatro sinais somados**, cada um cobrindo a falha do outro:
   palavras (TF-IDF com raízes de 5 letras), letras (n-gramas de 3 a 5, tolera
   erro de digitação), significado (LSA/SVD de 64 dimensões, calculado offline
   em Python e só multiplicado na hora) e intenção (regressão logística).
   Pesos: palavras 0,4 / letras 0,6 / significado 0,3 / intenção 0,1.
4. **Abstenção honesta.** Se a nota é baixa, diz que não achou e mostra as
   áreas (nunca fica mudo, nunca chuta). Ponto fraco deles (69–77%).
5. **Avaliação séria:** 210+ perguntas com gabarito, conjuntos separados
   (desenvolvimento / teste / independente / reserva / final), ablação
   (tirar cada sinal e ver quanto cai: sem LSA, 91% -> 75%) e relato do que
   *não* deu certo. Isso é ótimo material de trabalho acadêmico.
6. **Sem modelo de linguagem** lá, por privacidade (mulheres em risco). Esse
   motivo **não vale aqui**: a pergunta do Escudo é sobre estatística pública
   de câncer, sem dado pessoal. Então o Gemini pode entrar (ver 4).

## 3. A tradução para o Escudo

| MISM3 | Escudo |
|---|---|
| Destino = serviço, seção, ferramenta | Destino = (assunto do painel) x (câncer), os caminhos/ações da Lia, e as páginas "Onde ser atendida" e "Apoio à mulher" |
| Vocabulário popular do serviço | Vocabulário popular de cada assunto e cada câncer: "caroço no peito", "preventivo/papanicolau" (colo do útero), "tá aumentando?", "morre muita?", "fica quanto tempo internada?", "quanto gasta o SUS?" |
| Catálogo verificado | `inteligencia.py` continua sendo a única fonte dos números |
| "Não achei" + áreas | "Não tenho certeza do que você quis dizer. Você quis saber sobre...?" com **botões da Lia** (3 melhores palpites) |

Pontos que **não mudam**: a inteligência calcula, o Gemini só explica; nunca
atribuir causa; nada de orçamento em reais; cada pergunta mostra o selo de
escopo (Estado / cidade); Lia segue conduzindo por botões, e a caixa é uma
porta a mais, não substitui a árvore.

## 4. Onde o Gemini entra (3 papéis, do mais seguro ao mais ousado)

1. **Explicar os fatos** (já existe, `responder_com_ia`). Fica como está.
2. **Segunda chance de entender** (novo): se a busca local tiver nota baixa,
   o Gemini recebe só a pergunta e a lista fechada de destinos e devolve o id
   do destino mais provável (ou "nenhum"). É classificação em conjunto
   fechado: ele escolhe, não inventa. Se a chave/rede falhar, cai na
   abstenção com botões. Custo: uma chamada só nas perguntas difíceis.
3. **Bastidor, offline:** gerar variações de perguntas (jeitos de falar) para
   ampliar o vocabulário e o conjunto de avaliação, **revisadas pelo autor**
   antes de entrar. Resolve o "vocabulário escasso" na raiz.

Cuidado: avisar na caixa "não escreva dados pessoais"; enviar ao Gemini apenas
a pergunta e os fatos agregados, nunca linhas do banco.

## 5. Parte "preditiva simples"

A projeção de tendência (reta + teste de acerto, `testar_projecao`) já existe.
Para o requisito de IA, o mais honesto é **mostrar a validação** (backtest:
"se eu tivesse previsto os últimos anos com esse método, o erro teria sido X")
e rotular como "aprendizado de máquina simples (regressão)". Não chamar de IA
preditiva avançada (regra já combinada). Proposta pequena, depois da caixa.

## 6. Entrega em etapas, todas aditivas (nada existente é apagado)

1. **Etapa 0 — diagnóstico no Windows (5 min):** chave funciona? nome do
   modelo está certo? (o código usa `gemini-3.8-flash`, não confirmado).
2. **Etapa 1 — material:** catálogo de destinos + vocabulário popular + ~150
   perguntas com gabarito (dev/teste), em arquivos novos em `algoritimos/`.
   Aqui o autor revisa o vocabulário (só ele sabe como as pessoas falam).
3. **Etapa 2 — motor local** (`entendimento.py`, novo): palavras + letras +
   LSA, abstenção, testes e **medição contra o `conversa.entender` atual**
   (a tabela antes/depois é o resultado do trabalho).
4. **Etapa 3 — Gemini na segunda chance**, com simulação nos testes.
5. **Etapa 4 — caixa "Pergunte à Lia"** no painel, em arquivo de integração
   mínimo; rodar `dashboard/teste_painel.py` e todos os testes antes de
   qualquer push. A árvore, o passeio e o resto ficam intactos.
6. **Etapa 5 (opcional):** backtest da projeção.

Dependência nova: `scikit-learn` só para o treino offline do LSA (o painel só
lê o arquivo gerado). Alternativa sem dependência: TF-IDF e letras em
Python/numpy puro e LSA via `numpy.linalg.svd`.

## 7. Perguntas ao autor

- Etapa 0 feita? (resultado do teste da chave e do modelo)
- A caixa fica na lateral junto da Lia ou como aba própria?
- Aprova o Gemini como "segunda chance" (papel 2) e para gerar variações
  (papel 3)? Ou prefere só explicar (papel 1)?
- Quem revisa o vocabulário popular? Sugestão: o autor lê a lista gerada e
  corta/ajusta antes de entrar.
