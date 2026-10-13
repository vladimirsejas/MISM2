# Integração geográfica — MISM2

Esta camada acrescenta uma primeira camada independente para consulta de serviços públicos de Rio Claro. Ela não modifica o banco de internações, os cálculos epidemiológicos, a Lia nem o painel analítico existente.

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

