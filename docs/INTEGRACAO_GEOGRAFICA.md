# Integração geográfica — MISM2

Esta branch acrescenta uma primeira camada independente para consulta de serviços públicos de Rio Claro. Ela não modifica o banco de internações, os cálculos epidemiológicos, a Lia nem o painel analítico existente.

## Arquivos adicionados

- `dados_geograficos/catalogo_servicos_rioclaro.json`: catálogo de serviços públicos, com 164 registros na origem consultada. Cada registro conserva sua fonte e data de verificação quando esses campos existem.
- `dados_geograficos/indice_cep_rioclaro.json`: índice de 1.387 CEPs gerado a partir do CNEFE do IBGE/Censo 2022. Contém centros aproximados, raios de incerteza e referências territoriais, não endereços residenciais.
- `algoritimos/geografia_servicos.py`: implementação independente para validar e resolver localizações.
- `dashboard/pages/mapa_servicos.py`: página adicional de consulta e mapa no Streamlit, disponível pela navegação multipágina.
- `tests/test_geografia_servicos.py`: testes da lógica de localização e filtros.

## Regras de segurança geográfica

1. Coordenadas precisam estar dentro de uma caixa de referência ampla para Rio Claro/SP.
2. Coordenadas já registradas no serviço têm prioridade.
3. O centro aproximado do CEP só é usado se o raio de incerteza for de até 800 metros.
4. Sem localização confiável, o serviço permanece na lista, mas não recebe um ponto inventado.
5. A página não solicita CEP da usuária; portanto, não precisa enviar uma localização pessoal para procurar os serviços.
6. Distância em linha reta não é apresentada como tempo de viagem nem como cobertura efetiva.

## Proveniência e limites

O catálogo e o índice foram obtidos dos artefatos de dados públicos versionados no repositório MISM3 em 12/10/2026. A implementação desta branch é nova; não importa nem executa os scripts ou o frontend do MISM3. Os registros preservam as fontes originais disponíveis no catálogo. O índice geográfico usa CNEFE/IBGE, Censo Demográfico 2022, e deve ser tratado como referência aproximada, não como endereço exato.

Os dados de serviços podem envelhecer. A página orienta a confirmar endereço, telefone e horário na fonte antes do deslocamento. O catálogo deve ser atualizado por conferência de suas fontes, não apenas pela data do arquivo.

## Validação pendente

Esta branch foi criada separada da branch principal para permitir revisão. Os testes unitários estão incluídos, mas precisam ser executados em ambiente Python local e a página deve ser aberta no Streamlit antes de integrar ou mesclar qualquer coisa. Nenhuma alteração foi feita em `main`.

## Integração dos CSVs CNES já baixados

O script `etl/geografia_cnes.py` processa os arquivos nacionais já presentes em `banco/cnes/` sem carregar a base inteira na memória. Por padrão, mantém estabelecimentos públicos e entidades sem fins lucrativos, filtra Rio Claro pelo código IBGE `354390` e também considera CEPs do índice local quando esse índice está disponível.

Execute na raiz do repositório, com o ambiente Python do MISM2 ativado:

```powershell
python etl/geografia_cnes.py
```

A saída é gravada em `banco/geografia_cnes/cnes_servicos_rioclaro.json`. A página `dashboard/pages/mapa_servicos.py` detecta esse arquivo automaticamente e combina o resultado com os 164 registros manuais já existentes. O catálogo derivado e os dados brutos ficam ignorados pelo Git; não use `git add .` para incluir o acervo nacional.

O ETL consulta apenas `tbEstabelecimento`, `rlEstabServClass`, `tbServicoEspecializado`, `tbClassificacaoServico`, `tbEstabHorarioAtend`, `tbEquipe` e `rlEquipeNasfEsf`. Ele não abre `tbDadosProfissionalSus`, `rlEstabEquipeProf` nem `rlCooperativa`, pois não são necessários para o catálogo público. O banco `banco/escudo_feminino.db`, os cálculos epidemiológicos e os fluxos da Lia não são modificados.

Para rodar os testes da camada geográfica:

```powershell
python tests/test_geografia_servicos.py
python tests/test_geografia_cnes.py
```

O CNES registra dados administrativos declarados pelos estabelecimentos; presença de um serviço, equipe ou horário no cadastro não garante disponibilidade atual. A página deve ser tratada como localizador com fonte, e não como confirmação de vaga ou atendimento.

