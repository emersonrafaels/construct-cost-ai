# 📊 Geradores de Datasets - Agências Bancárias Itaú

Scripts robustos em POO para geração de datasets realistas de orçamentos e preços unitários para obras de agências bancárias do Itaú Unibanco.

## 🎯 Visão Geral

Este módulo fornece duas ferramentas principais:

1. **`create_sample_dataset_budget.py`** - Gerador de Orçamentos Completos
2. **`create_sample_dataset_lpu.py`** - Gerador de Lista de Preços Unitários (LPU)

## 🏗️ Características

### Gerador de Orçamento (`BankBranchBudgetGenerator`)

#### Categorias de Itens
- ✅ Demolição e Remoção
- ✅ Estrutura e Alvenaria
- ✅ Revestimentos e Acabamentos
- ✅ Forros e Divisórias
- ✅ Pisos
- ✅ Pintura
- ✅ Fachada e Comunicação Visual (padrão Itaú)
- ✅ Instalações Hidráulicas
- ✅ Instalações Elétricas
- ✅ Climatização (HVAC)
- ✅ Segurança e Automação
- ✅ Mobiliário Corporativo
- ✅ Limpeza Final

#### Recursos
- 🔹 **130+ itens** detalhados de orçamento
- 🔹 Preços baseados em mercado real (2024)
- 🔹 Especificações técnicas completas
- 🔹 Fornecedores homologados
- 🔹 Padrões Itaú Unibanco (cores, materiais, acabamentos)
- 🔹 Cálculo automático de totais
- 🔹 Resumos por categoria
- 🔹 Metadados completos do projeto

### Gerador de LPU (`BankBranchLPUGenerator`)

#### Fontes de Preços
- 📋 **SINAPI** - Caixa Econômica Federal
- 📋 **TCPO** - Tabela de Composições de Preços
- 📋 **EMOP** - Empresa de Obras Públicas RJ
- 📋 **Fornecedores Especializados**
- 📋 **Pesquisa de Mercado**
- 📋 **Contratos Itaú Unibanco**

#### Recursos
- 🔹 **100+ preços unitários** de referência
- 🔹 Múltiplas fontes de precificação
- 🔹 Composições SINAPI quando aplicável
- 🔹 Identificação de fornecedores
- 🔹 Data de referência dos preços
- 🔹 Observações técnicas

## 📦 Instalação

Certifique-se de ter as dependências instaladas:

```bash
pip install pandas openpyxl
```

## 🚀 Uso Básico

### Gerar Orçamento Completo

```python
from create_sample_dataset_budget import BankBranchBudgetGenerator, BudgetMetadata

# Criar metadados customizados
metadata = BudgetMetadata(
    projeto="Reforma Agência Itaú - Av. Paulista, 1234",
    local="São Paulo - SP",
    area_total_m2=450.0,
    tipo_obra="Reforma Completa - Padrão 2024"
)

# Gerar orçamento
generator = BankBranchBudgetGenerator(metadata)
generator.generate_standard_budget()

# Obter DataFrame
df = generator.get_dataframe()
print(df)

# Obter resumo
summary = generator.get_summary()
print(f"Valor Total: R$ {summary['estatisticas']['valor_total']:,.2f}")
print(f"Valor por m²: R$ {summary['estatisticas']['valor_por_m2']:,.2f}")

# Salvar arquivos
generator.save_to_csv("orcamento.csv")
generator.save_to_excel("orcamento.xlsx")
```

### Gerar LPU (Lista de Preços)

```python
from create_sample_dataset_lpu import BankBranchLPUGenerator

# Criar gerador
lpu_generator = BankBranchLPUGenerator(data_referencia="2024-11")
lpu_generator.generate_standard_lpu()

# Obter DataFrame
df_lpu = lpu_generator.get_dataframe()
print(df_lpu)

# Obter resumo
summary = lpu_generator.get_summary()
print(f"Total de Itens: {summary['metadata']['total_itens']}")
print(f"Preço Médio: R$ {summary['estatisticas']['preco_medio']:,.2f}")

# Salvar arquivos
lpu_generator.save_to_csv("lpu.csv")
lpu_generator.save_to_excel("lpu.xlsx")
```

## 🎨 Uso Avançado

### Adicionar Itens Customizados ao Orçamento

```python
from create_sample_dataset_budget import (
    BankBranchBudgetGenerator,
    BudgetItem,
    ItemCategory
)

generator = BankBranchBudgetGenerator()
generator.generate_standard_budget()

# Adicionar item customizado
item_custom = BudgetItem(
    cod_item="CUSTOM001",
    nome="Sistema de monitoramento avançado",
    categoria=ItemCategory.SECURITY,
    unidade="un",
    qtde=1.0,
    unitario_orcado=25000.00,
    observacoes="Sistema completo de CFTV 4K"
)
generator.add_item(item_custom)

# Salvar
generator.save_to_excel("orcamento_customizado.xlsx")
```

### Adicionar Preços Customizados à LPU

```python
from create_sample_dataset_lpu import (
    BankBranchLPUGenerator,
    UnitPriceItem,
    PriceSource
)

lpu_gen = BankBranchLPUGenerator()
lpu_gen.generate_standard_lpu()

# Adicionar preço customizado
price_custom = UnitPriceItem(
    cod_item="CUSTOM001",
    descricao="Sistema de monitoramento avançado",
    unidade="un",
    unitario_lpu=22500.00,
    fonte=PriceSource.SUPPLIER,
    data_referencia="2024-11",
    fornecedor="Tech Security Ltda",
    observacoes="Inclui instalação e configuração"
)
lpu_gen.add_item(price_custom)

# Salvar
lpu_gen.save_to_excel("lpu_customizada.xlsx")
```

## 📊 Estrutura dos Dados

### Orçamento (Budget)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `cod_upe` | str | Código UPE (Unidade de Planejamento e Execução) - formato UPE_XXXXX |
| `cod_item` | str | Código único do item |
| `nome` | str | Descrição completa do item |
| `categoria` | str | Categoria do item |
| `unidade` | str | Unidade de medida (m², un, m, etc.) |
| `qtde` | float | Quantidade orçada |
| `unitario_orcado` | float | Preço unitário orçado |
| `total_orcado` | float | Valor total (calculado) |
| `observacoes` | str | Observações técnicas |

**Códigos UPE (Unidade de Planejamento e Execução):**
- `UPE_00001` - Demolição e Remoção
- `UPE_00002` - Estrutura e Alvenaria
- `UPE_00003` - Revestimentos e Acabamentos
- `UPE_00004` - Forros e Divisórias
- `UPE_00005` - Pisos
- `UPE_00006` - Pintura
- `UPE_00007` - Fachada e Comunicação Visual
- `UPE_00008` - Instalações Hidráulicas
- `UPE_00009` - Instalações Elétricas
- `UPE_00010` - Climatização (HVAC)
- `UPE_00011` - Segurança e Automação
- `UPE_00012` - Mobiliário
- `UPE_00013` - Limpeza Final

Cada código UPE representa um orçamento distinto, agrupando um conjunto de itens relacionados por categoria ou finalidade.

### LPU (Unit Prices)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `cod_item` | str | Código único do item |
| `descricao` | str | Descrição do item |
| `unidade` | str | Unidade de medida |
| `unitario_lpu` | float | Preço unitário de referência |
| `fonte` | str | Fonte do preço (SINAPI, TCPO, etc.) |
| `data_referencia` | str | Data de referência (YYYY-MM) |
| `composicao` | str | Código de composição (quando aplicável) |
| `fornecedor` | str | Fornecedor de referência |
| `observacoes` | str | Observações |

## 🏢 Especificações Itaú Unibanco

### Padrões de Identidade Visual
- **Cor Laranja**: Pantone 1585C
- **ACM**: Dibond Platinum 4mm
- **Logo**: LED com iluminação noturna
- **Portal**: Modelo 2024 em ACM

### Materiais Padrão
- **Pisos**: Porcelanato 60x60cm classe A
- **Revestimentos**: Cerâmica 30x60cm específica
- **Forro**: Modular fibra mineral 625x625mm
- **Divisórias**: Gesso acartonado RU 48mm
- **Carpete**: Placas Interface/Beaulieu

### Segurança
- Portas corta-fogo 90min
- CFTV IP 4MP mínimo
- Controle de acesso biométrico
- Central de alarme monitorada
- Iluminação de emergência LED

## 📁 Arquivos Gerados

### CSV
- Formato: UTF-8 com BOM
- Separador: `;` (ponto e vírgula)
- Decimais: `,` (vírgula)

### Excel - Orçamento
- **Aba 1 - Orçamento**: Dados completos detalhados com cod_upe
- **Aba 2 - Resumo por Categoria**: Agrupamento por categoria
- **Aba 3 - Resumo por UPE**: Agrupamento por código UPE (orçamentos distintos)
- Formato: `.xlsx` (compatível com Excel 2007+)

### Excel - LPU
- **Aba 1 - LPU**: Preços unitários completos
- **Aba 2 - Resumo por Fonte**: Agrupamento por fonte de preço
- Formato: `.xlsx` (compatível com Excel 2007+)

## 🎯 Casos de Uso

1. **Planejamento de Obras**
   - Gerar orçamentos base para novos projetos
   - Estimar custos por m² de área
   - Agrupar itens por UPE para controle de execução

2. **Análise de Preços**
   - Comparar preços orçados vs. LPU
   - Identificar desvios e oportunidades
   - Analisar valores por UPE

3. **Treinamento de IA**
   - Datasets para modelos de validação
   - Análise de padrões de precificação
   - Agrupamento por categorias e UPE

4. **Documentação**
   - Registros históricos de preços
   - Baseline para futuras cotações
   - Controle de orçamentos por UPE

## 🔧 Customização

### Alterar Área Padrão
```python
metadata = BudgetMetadata(area_total_m2=600.0)
```

### Alterar Data de Referência
```python
lpu = BankBranchLPUGenerator(data_referencia="2025-01")
```

### Filtrar por Categoria
```python
df = generator.get_dataframe()
df_fachada = df[df['categoria'] == 'Fachada e Comunicação Visual']
```

## 📈 Estatísticas de Exemplo

### Orçamento Típico (450m²)
- **Total de Itens**: 130+
- **Valor Total**: R$ 1.200.000,00 - R$ 1.500.000,00
- **Valor por m²**: R$ 2.600,00 - R$ 3.300,00

### Distribuição por Categoria (%)
- Fachada e Comunicação: 25-30%
- HVAC e Elétrica: 20-25%
- Mobiliário e Segurança: 20-25%
- Acabamentos e Pisos: 15-20%
- Demais categorias: 10-15%

## 🤝 Contribuindo

Para adicionar novos itens ou melhorar os datasets:

1. Siga o padrão de nomenclatura de códigos
2. Use categorias existentes quando possível
3. Inclua fontes de preços confiáveis
4. Adicione observações técnicas relevantes
5. Mantenha consistência com padrão Itaú

## 📝 Notas

- Preços são valores de referência (mercado SP/2024)
- Verificar atualização de preços periodicamente
- Alguns itens podem ter variação regional
- Consultar fornecedores homologados para preços exatos

## 📞 Suporte

Para dúvidas ou sugestões sobre os datasets, entre em contato com a equipe de desenvolvimento.

---

**Versão**: 1.0  
**Última Atualização**: Novembro 2024  
**Compatibilidade**: Python 3.8+
