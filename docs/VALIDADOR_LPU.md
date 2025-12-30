# Validador LPU - Conciliação de Orçamentos

Módulo Python para validação e conciliação de orçamentos de construção civil contra bases de preços LPU (Lista de Preços Unitários).

## 📋 Descrição

O Validador LPU realiza a conciliação automática entre:
- **Orçamento da construtora** (valores propostos)
- **Base LPU oficial** (preços de referência)

Identificando divergências de valores **sem tolerância** e classificando cada item automaticamente.

## 🎯 Funcionalidades

### ✅ Validação Completa
- Carregamento automático de Excel e CSV
- Merge inteligente por `cod_item` + `unidade`
- Cálculo de divergências unitárias e totais
- Classificação automática sem tolerância
- Exportação em múltiplos formatos

### 📊 Cálculos Realizados

```python
valor_total_orcado = qtde * unitario_orcado
dif_unitario = unitario_orcado - unitario_lpu
dif_total = dif_unitario * qtde
perc_dif = (dif_unitario / unitario_lpu) * 100
```

### 🏷️ Classificação de Status

**Regra: Tolerância ZERO** - qualquer diferença é registrada

| Status | Condição | Descrição |
|--------|----------|-----------|
| **OK** | `unitario_orcado == unitario_lpu` | Preços idênticos |
| **Para ressarcimento** | `unitario_orcado > unitario_lpu` | Orçamento acima da referência |
| **Abaixo LPU** | `unitario_orcado < unitario_lpu` | Orçamento abaixo da referência |

## 📁 Estrutura de Arquivos

### Arquivo de Orçamento
**Localização:** `data/orcamento_exemplo.xlsx`

**Colunas obrigatórias:**
- `cod_upe` - Código da UPE (orçamento)
- `cod_item` - Código do item (chave primária com unidade)
- `nome` - Descrição do item
- `categoria` - Categoria do serviço
- `unidade` - Unidade de medida (m², m³, un, etc.)
- `qtde` - Quantidade orçada
- `unitario_orcado` - Preço unitário proposto
- `total_orcado` - Valor total (opcional, será calculado)
- `observacoes` - Observações (opcional)

### Arquivo LPU
**Localização:** `data/lpu_exemplo.xlsx`

**Colunas obrigatórias:**
- `cod_item` - Código do item (chave primária com unidade)
- `descricao` - Descrição oficial
- `unidade` - Unidade de medida
- `unitario_lpu` - Preço unitário de referência
- `fonte` - Fonte do preço (SINAPI, SICRO, etc.)
- `data_referencia` - Data da tabela (opcional)
- `composicao` - Composição do preço (opcional)
- `fornecedor` - Fornecedor (opcional)
- `observacoes` - Observações (opcional)

### Chave de Relacionamento
```python
chave = ["cod_item", "unidade"]
tipo_join = "inner"
```

## 🚀 Uso

### Uso Básico

```python
from construct_cost_ai.domain.validador_lpu import validar_lpu

# Validação completa
df_resultado = validar_lpu(
    caminho_orcamento="data/orcamento_exemplo.xlsx",
    caminho_lpu="data/lpu_exemplo.xlsx",
    output_dir="outputs",
    verbose=True
)
```

### Uso Modular

```python
from construct_cost_ai.domain.validador_lpu import (
    carregar_orcamento,
    carregar_lpu,
    cruzar_orcamento_lpu,
    calcular_divergencias,
    salvar_resultado
)

# Carregar dados
df_orcamento = carregar_orcamento("data/orcamento_exemplo.xlsx")
df_lpu = carregar_lpu("data/lpu_exemplo.xlsx")

# Cruzar dados
df_cruzado = cruzar_orcamento_lpu(df_orcamento, df_lpu)

# Calcular divergências
df_resultado = calcular_divergencias(df_cruzado)

# Salvar resultados
salvar_resultado(df_resultado, "outputs")
```

### Execução via Terminal

```bash
# Executar validação com arquivos padrão
python src/construct_cost_ai/domain/validador_lpu.py

# Executar exemplos interativos
python examples/test_validador_lpu.py
```

## 📊 Arquivos de Saída

### 1. Excel com Múltiplas Abas
**Arquivo:** `outputs/validacao_lpu.xlsx`

#### Aba 1: Validação Completa
Todos os itens com colunas:
- Dados do orçamento (cod_upe, cod_item, nome, categoria, unidade, qtde)
- Preços (unitario_orcado, unitario_lpu)
- Divergências (dif_unitario, perc_dif, dif_total)
- Classificação (status_conciliacao)
- Dados LPU (fonte, descricao, data_referencia, etc.)

#### Aba 2: Resumo por Status
| Status | Qtd Itens | Dif Total (R$) | Valor Total Orçado (R$) |
|--------|-----------|----------------|-------------------------|
| OK | 45 | 0.00 | 250.000,00 |
| Para ressarcimento | 18 | 35.420,50 | 180.000,00 |
| Abaixo LPU | 12 | -8.500,00 | 95.000,00 |

#### Aba 3: Resumo por Categoria
| Categoria | Status | Qtd Itens | Dif Total (R$) |
|-----------|--------|-----------|----------------|
| Estrutura | OK | 8 | 0.00 |
| Estrutura | Para ressarcimento | 3 | 12.500,00 |

#### Aba 4: Resumo por UPE
| Código UPE | Status | Qtd Itens | Dif Total (R$) |
|------------|--------|-----------|----------------|
| UPE_00001 | OK | 5 | 0.00 |
| UPE_00002 | Para ressarcimento | 2 | 8.450,00 |

### 2. CSV Simplificado
**Arquivo:** `outputs/validacao_lpu.csv`

Mesmas colunas da aba "Validação Completa" em formato CSV com separador `;` e encoding UTF-8.

## 📈 Análises Disponíveis

### 1. Top Divergências Absolutas
```python
top_divergencias = df_resultado.nlargest(10, 'dif_total')
```

### 2. Top Divergências Percentuais
```python
df_resultado['perc_dif_abs'] = abs(df_resultado['perc_dif'])
top_percentual = df_resultado.nlargest(10, 'perc_dif_abs')
```

### 3. Itens para Ressarcimento
```python
ressarcimento = df_resultado[
    df_resultado['status_conciliacao'] == 'Para ressarcimento'
]
total_ressarcimento = ressarcimento['dif_total'].sum()
```

### 4. Filtros por Categoria
```python
categoria_especifica = df_resultado[
    df_resultado['categoria'] == 'Estrutura e Alvenaria'
]
```

### 5. Filtros por UPE
```python
upe_especifica = df_resultado[
    df_resultado['cod_upe'] == 'UPE_00001'
]
```

## ⚠️ Tratamento de Erros

O módulo possui exceções customizadas:

```python
from construct_cost_ai.domain.validador_lpu import (
    ValidadorLPUError,           # Erro base
    ArquivoNaoEncontradoError,   # Arquivo não existe
    ColunasFaltandoError,        # Colunas obrigatórias ausentes
)

try:
    df_resultado = validar_lpu()
except ArquivoNaoEncontradoError as e:
    print(f"Arquivo não encontrado: {e}")
except ColunasFaltandoError as e:
    print(f"Colunas faltando: {e}")
except ValidadorLPUError as e:
    print(f"Erro na validação: {e}")
```

## 🔍 Validações Automáticas

### Durante Carregamento
- ✅ Verificação de existência dos arquivos
- ✅ Validação de colunas obrigatórias
- ✅ Conversão automática de tipos de dados
- ✅ Tratamento de valores nulos

### Durante Merge
- ✅ Verificação de chaves duplicadas
- ✅ Alerta de itens sem correspondência
- ✅ Contagem de itens cruzados

### Durante Cálculos
- ✅ Proteção contra divisão por zero
- ✅ Validação de consistência de total_orcado
- ✅ Arredondamento padronizado (2 casas decimais)

## 📝 Exemplos Práticos

Veja o arquivo `examples/test_validador_lpu.py` com 4 exemplos completos:

1. **Validação Completa** - Fluxo básico end-to-end
2. **Análise de Divergências** - Top 10 maiores diferenças
3. **Filtros Customizados** - Aplicação de filtros avançados
4. **Uso Modular** - Uso individual de cada função

Execute:
```bash
python examples/test_validador_lpu.py
```

## 🛠️ Requisitos

```txt
pandas>=2.0.0
openpyxl>=3.1.0  # Para leitura/escrita Excel
```

## 📊 Estatísticas Exibidas

```
================================================================================
VALIDADOR LPU - Conciliação de Orçamento vs Base de Preços
================================================================================

📂 Carregando arquivos...
   ✅ Orçamento carregado: 77 itens
   ✅ LPU carregado: 100 itens

🔗 Cruzando orçamento com LPU...
   ✅ Itens cruzados: 75

🧮 Calculando divergências (tolerância ZERO)...

📊 ESTATÍSTICAS DA VALIDAÇÃO
--------------------------------------------------------------------------------
   Total de itens validados: 75
   ✅ OK: 45 (60.0%)
   ⚠️  Para ressarcimento: 18 (24.0%)
   📉 Abaixo LPU: 12 (16.0%)

   💰 Valor total orçado: R$ 525,000.00
   💵 Divergência total: R$ 26,920.50
   💸 Potencial ressarcimento: R$ 35,420.50

💾 Salvando resultados...
✅ Excel salvo em: outputs/validacao_lpu.xlsx
✅ CSV salvo em: outputs/validacao_lpu.csv

================================================================================
✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!
================================================================================
```

## 🎓 Conceitos

### O que é LPU?
**LPU (Lista de Preços Unitários)** são bases de preços de referência para obras públicas e privadas, como:
- **SINAPI** (Caixa Econômica Federal)
- **SICRO** (DNIT - Rodovias)
- **ORSE** (Estados - São Paulo, Rio, etc.)
- **Tabelas Fornecedores** (fabricantes específicos)

### Por que Tolerância Zero?
A validação **sem tolerância** permite:
- ✅ Identificar **todas** as divergências
- ✅ Permitir análise posterior com critérios flexíveis
- ✅ Rastreabilidade completa
- ✅ Aplicar filtros customizados após validação

Se precisar aplicar tolerância, faça no filtro posterior:
```python
# Aplicar tolerância de 5% após validação
tolerancia = 5.0
df_filtrado = df_resultado[abs(df_resultado['perc_dif']) > tolerancia]
```

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os exemplos em `examples/test_validador_lpu.py`
2. Consulte os logs de erro detalhados
3. Valide a estrutura dos arquivos de entrada

## 📄 Licença

Este módulo faz parte do projeto Construct Cost AI.
