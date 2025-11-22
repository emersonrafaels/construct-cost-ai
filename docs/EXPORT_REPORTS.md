# Exportação de Relatórios - Validador LPU

## 📋 Visão Geral

O Validador LPU agora gera automaticamente **4 tipos de arquivos** para cada validação:

1. **Excel Básico** (4 abas)
2. **CSV** (dados completos)
3. **Excel Completo** (11+ abas com análises detalhadas)
4. **HTML** (relatório visual interativo)

## 📁 Arquivos Gerados

### 1. `validacao_lpu.xlsx` - Excel Básico (4 abas)

Exportação rápida com os dados essenciais:

| Aba | Descrição |
|-----|-----------|
| **Validação Completa** | Todos os itens com divergências calculadas |
| **Resumo por Status** | Agrupamento por OK/Para ressarcimento/Abaixo LPU |
| **Resumo por Categoria** | Análise agregada por categoria de serviço |
| **Resumo por UPE** | Análise agregada por código UPE |

**Uso:** Análise rápida e compartilhamento básico de resultados.

---

### 2. `validacao_lpu.csv` - Exportação CSV

Arquivo CSV com todos os dados (separador `;`).

**Uso:** Importação em outras ferramentas, análises customizadas, scripts Python/R.

---

### 3. `relatorio_completo_validacao_lpu.xlsx` - Excel Completo (11+ abas)

Relatório detalhado com análises aprofundadas:

#### 📊 Abas Principais:

1. **Estatísticas**
   - Total de itens analisados
   - Distribuição por status (OK, Ressarcimento, Abaixo)
   - Valores totais e divergências
   - Percentuais calculados

2. **Resumo por Status**
   - Quantidade de itens por status
   - Divergência total por status
   - Valor total orçado por status

3. **Top 10 Div Absoluta**
   - 10 maiores divergências em valor (R$)
   - Ordenado por `dif_total` decrescente

4. **Top 20 Div Absoluta**
   - 20 maiores divergências em valor (R$)

5. **Top 10 Div Percentual**
   - 10 maiores divergências em percentual (%)
   - Ordenado por `perc_dif_abs` decrescente

6. **Top 20 Div Percentual**
   - 20 maiores divergências em percentual (%)

7. **Itens Para Ressarcimento**
   - Todos os itens com preço acima da LPU
   - Ordenado por divergência total
   - Campos: código, nome, categoria, preços, divergências

8. **Itens Abaixo LPU**
   - Todos os itens com preço abaixo da LPU
   - Ordenado por divergência total (negativa)

9. **Resumo por Categoria**
   - Agrupamento por categoria e status
   - Quantidade de itens e divergência total

10. **Dif por Categoria**
    - Divergência total por categoria
    - Valor total orçado por categoria

11. **Resumo por UPE**
    - Agrupamento por UPE e status
    - Quantidade de itens e divergência total

12. **Dif por UPE**
    - Divergência total por UPE
    - Valor total orçado por UPE

13. **Dados Completos**
    - Dataset completo com todas as colunas
    - Todos os itens processados

**Uso:** Análise gerencial, apresentações executivas, auditorias.

---

### 4. `relatorio_validacao_lpu.html` - Relatório HTML

Dashboard interativo com design moderno e responsivo.

#### 🎨 Características:

- **Design Profissional**
  - Gradiente roxo/azul
  - Cards coloridos para estatísticas
  - Tabelas formatadas e responsivas

- **Estatísticas Visuais**
  - Cards com valores grandes e coloridos
  - Status OK (verde), Ressarcimento (amarelo), Abaixo (vermelho)
  - Totais financeiros destacados

- **Tabelas Interativas**
  - Hover effects nas linhas
  - Formatação de valores monetários (R$)
  - Formatação de percentuais (%)
  - Status com badges coloridos

- **Seções Incluídas**
  - Estatísticas Gerais (7 cards)
  - Resumo por Status
  - Top 10 Divergências (Valor Absoluto)
  - Top 10 Divergências (Percentual)
  - Resumo por Categoria (se disponível)
  - Resumo por UPE (se disponível)

- **Recursos Adicionais**
  - Pronto para impressão (CSS print-friendly)
  - Responsivo (mobile-friendly)
  - Encoding UTF-8 (suporta acentuação)
  - Timestamp de geração

**Uso:** Apresentações, relatórios executivos, compartilhamento web, impressão.

---

## 🚀 Como Usar

### Opção 1: Validação Completa Automática

```python
from construct_cost_ai.domain.validador_lpu import validar_lpu

# Executa validação e gera TODOS os relatórios automaticamente
df_resultado = validar_lpu(
    caminho_orcamento="data/orcamento.xlsx",
    caminho_lpu="data/lpu.xlsx",
    output_dir="outputs",
    verbose=True
)
```

**Resultado:**
- ✅ `outputs/validacao_lpu.xlsx` (4 abas)
- ✅ `outputs/validacao_lpu.csv`
- ✅ `outputs/relatorio_completo_validacao_lpu.xlsx` (11+ abas)
- ✅ `outputs/relatorio_validacao_lpu.html`

### Opção 2: Relatórios Individuais

```python
from construct_cost_ai.domain.validador_lpu import (
    validar_lpu,
    gerar_relatorio_excel_completo,
    gerar_relatorio_html
)

# Executar validação sem relatórios adicionais
df = validar_lpu(..., verbose=False)

# Gerar apenas relatório Excel completo
gerar_relatorio_excel_completo(
    df=df,
    output_dir="outputs",
    nome_base="relatorio_customizado"
)

# Gerar apenas relatório HTML
gerar_relatorio_html(
    df=df,
    output_dir="outputs",
    nome_base="dashboard_customizado"
)
```

### Opção 3: Script de Teste Interativo

```bash
# Executar menu interativo
python examples/test_validador_lpu.py

# Ou executar diretamente
cd examples
python test_validador_lpu.py
```

**Menu disponível:**
1. Presets pré-configurados
2. Configuração customizada
3. Validação simples
4. Ajuda

---

## 📊 Análises Disponíveis

### No Terminal (Opcionais)

Controladas pelos parâmetros da função `executar_validacao()`:

| Parâmetro | Descrição |
|-----------|-----------|
| `gerar_estatisticas` | Estatísticas resumidas no console |
| `gerar_top_divergencias` | Top N divergências no console |
| `gerar_analise_categorias` | Análise por categoria no console |
| `gerar_analise_upes` | Análise por UPE no console |

### Em Arquivos (Sempre Geradas)

**IMPORTANTE:** Todas as análises são **SEMPRE** exportadas para Excel e HTML, independente dos parâmetros acima. Os parâmetros controlam apenas a exibição no terminal.

---

## 💡 Casos de Uso

### 1. Análise Rápida
```python
# Apenas validação básica
df = validar_lpu(caminho_orcamento, caminho_lpu, output_dir)
# Resultado: 4 arquivos gerados automaticamente
```

### 2. Análise Completa no Terminal + Arquivos
```python
from examples.test_validador_lpu import executar_validacao

df = executar_validacao(
    gerar_estatisticas=True,
    gerar_top_divergencias=True,
    gerar_analise_categorias=True,
    gerar_analise_upes=True,
    top_n=20
)
# Terminal: todas as análises impressas
# Arquivos: 4 arquivos com relatórios completos
```

### 3. Filtragem Específica
```python
df = executar_validacao(
    filtro_percentual=15.0,          # Divergências > 15%
    filtro_categoria="Estrutura",    # Apenas categoria específica
    filtro_valor_minimo=1000.00,     # Apenas itens > R$ 1.000
    gerar_top_divergencias=True,
    top_n=10
)
# Arquivos: dados filtrados + análises completas
```

### 4. Auditoria Detalhada
```python
df = executar_validacao(
    verbose=True,               # Progresso detalhado
    analise_modular=True,       # Análise passo a passo
    gerar_estatisticas=True,
    gerar_top_divergencias=True,
    gerar_analise_categorias=True,
    gerar_analise_upes=True,
    top_n=20
)
# Terminal: análise passo a passo completa
# Arquivos: Excel completo (11+ abas) + HTML interativo
```

---

## 📈 Estrutura dos Dados

### Colunas Principais no DataFrame

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `cod_item` | str | Código do item do orçamento |
| `nome` | str | Descrição do serviço |
| `categoria` | str | Categoria do serviço (ex: "Estrutura e Alvenaria") |
| `unidade` | str | Unidade de medida (m², m³, un, etc.) |
| `qtde` | float | Quantidade orçada |
| `cod_upe` | str | Código UPE (Unidade Padrão de Execução) |
| `unitario_orcado` | float | Preço unitário do orçamento (R$) |
| `unitario_lpu` | float | Preço unitário da LPU (R$) |
| `dif_unitario` | float | Diferença unitária (orçado - LPU) |
| `perc_dif` | float | Divergência percentual (%) |
| `valor_total_orcado` | float | Valor total do item (qtde × unitário) |
| `dif_total` | float | Divergência total (qtde × dif_unitário) |
| `status_conciliacao` | str | Status: "OK", "Para ressarcimento", "Abaixo LPU" |
| `fonte` | str | Fonte da LPU (SINAPI, SICRO, etc.) |

### Status de Conciliação

| Status | Critério | Ação |
|--------|----------|------|
| **OK** | `-3% ≤ divergência ≤ +3%` | ✅ Aprovado |
| **Para ressarcimento** | `divergência > +3%` | ⚠️ Preço acima da referência |
| **Abaixo LPU** | `divergência < -3%` | 🔴 Preço muito abaixo da referência |

---

## 🔧 Personalização

### Alterar Tolerância de Conciliação

Editar `validador_lpu.py`, função `calcular_divergencias()`:

```python
def calcular_divergencias(df: pd.DataFrame) -> pd.DataFrame:
    # Alterar tolerância (padrão: 3%)
    tolerancia = 5.0  # Agora 5% de tolerância
    
    df['status_conciliacao'] = df['perc_dif'].apply(
        lambda x: 'OK' if -tolerancia <= x <= tolerancia else
                  'Para ressarcimento' if x > tolerancia else
                  'Abaixo LPU'
    )
```

### Customizar Cores do HTML

Editar `gerar_relatorio_html()`, seção `<style>`:

```css
/* Alterar gradiente principal */
background: linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%);

/* Alterar cores dos status */
.stat-ok { color: #2ecc71; }      /* Verde */
.stat-warning { color: #f39c12; }  /* Laranja */
.stat-danger { color: #e74c3c; }   /* Vermelho */
```

### Adicionar Nova Aba no Excel Completo

Editar `gerar_relatorio_excel_completo()`:

```python
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    # ... abas existentes ...
    
    # Nova aba customizada
    df_custom = df.groupby('categoria').agg({
        'dif_total': ['sum', 'mean', 'std']
    }).reset_index()
    df_custom.to_excel(writer, sheet_name='Análise Estatística', index=False)
```

---

## 📚 Referências

### Arquivos do Projeto

- **Módulo principal:** `src/construct_cost_ai/domain/validador_lpu.py`
- **Script de teste:** `examples/test_validador_lpu.py`
- **Script de exportação:** `examples/test_exports.py`
- **Dados de exemplo:** `data/orcamento_exemplo.xlsx`, `data/lpu_exemplo.xlsx`

### Funções Principais

| Função | Arquivo | Descrição |
|--------|---------|-----------|
| `validar_lpu()` | `validador_lpu.py` | Orquestra toda a validação |
| `salvar_resultado()` | `validador_lpu.py` | Gera Excel básico (4 abas) + CSV |
| `gerar_relatorio_excel_completo()` | `validador_lpu.py` | Gera Excel completo (11+ abas) |
| `gerar_relatorio_html()` | `validador_lpu.py` | Gera relatório HTML interativo |
| `executar_validacao()` | `test_validador_lpu.py` | Interface com opções configuráveis |

---

## ⚠️ Troubleshooting

### Erro: "No module named 'openpyxl'"
```bash
pip install openpyxl
```

### Erro: "Permission denied" ao salvar arquivos
- Feche os arquivos Excel que estiverem abertos
- Execute com permissões de administrador (se necessário)
- Verifique se o diretório `outputs/` existe

### HTML não exibe corretamente
- Abra em navegador moderno (Chrome, Firefox, Edge)
- Verifique encoding UTF-8
- Se imprimir, use "Paisagem" para melhor visualização

### Excel muito pesado
- Use filtros para reduzir dataset antes de exportar
- Considere exportar apenas Excel básico (4 abas)
- Exporte relatório completo apenas quando necessário

---

## 📝 Changelog

### v2.0.0 (Atual)
- ✅ Adicionado relatório Excel completo (11+ abas)
- ✅ Adicionado relatório HTML interativo
- ✅ Exportação automática de todas as análises
- ✅ Top 10/20 divergências (absoluta e percentual)
- ✅ Análises detalhadas por categoria e UPE
- ✅ Dashboard visual com cards e tabelas formatadas
- ✅ Suporte para impressão e responsividade

### v1.0.0 (Anterior)
- ✅ Validação básica LPU vs Orçamento
- ✅ Excel básico (4 abas)
- ✅ Exportação CSV
- ✅ Análises no terminal

---

## 📧 Suporte

Para dúvidas ou sugestões, consulte:
- **Documentação:** `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`
- **README principal:** `README.md`
- **Quickstart:** `QUICKSTART.md`

---

**Desenvolvido com ❤️ pelo time Construct Cost AI**
