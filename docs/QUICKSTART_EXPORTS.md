# 🚀 Quick Start - Exportações Excel + HTML

## ⚡ Uso Rápido (30 segundos)

### 1. Executar Validação
```bash
cd construct-cost-ai
python examples/test_validador_lpu.py
```

### 2. Escolher Opção
```
Menu:
1. Presets
2. Customizado
3. Validação simples  ← ESCOLHA ESTA
4. Ajuda
```

### 3. Verificar Resultados
```bash
cd outputs
dir  # Windows
```

**4 arquivos gerados:**
- ✅ `validacao_lpu.xlsx` (Excel básico)
- ✅ `validacao_lpu.csv` (CSV)
- ✅ `relatorio_completo_validacao_lpu.xlsx` (Excel completo)
- ✅ `relatorio_validacao_lpu.html` (HTML interativo)

---

## 📊 Visualizar Relatórios

### Excel Completo (11+ abas)
```bash
# Abrir Excel completo
start outputs\relatorio_completo_validacao_lpu.xlsx  # Windows
open outputs/relatorio_completo_validacao_lpu.xlsx   # Mac
xdg-open outputs/relatorio_completo_validacao_lpu.xlsx  # Linux
```

**Abas importantes:**
- **Estatísticas:** Resumo geral
- **Top 10/20 Div Absoluta:** Maiores divergências em R$
- **Itens Para Ressarcimento:** Todos os itens problemáticos

### HTML Interativo
```bash
# Abrir no navegador
start outputs\relatorio_validacao_lpu.html  # Windows
open outputs/relatorio_validacao_lpu.html   # Mac
xdg-open outputs/relatorio_validacao_lpu.html  # Linux
```

**Dashboard visual com:**
- Cards coloridos (estatísticas)
- Tabelas formatadas
- Top 10 divergências
- Análises por categoria/UPE

---

## 💻 Uso em Código Python

### Básico
```python
from construct_cost_ai.domain.validador_lpu import validar_lpu

df = validar_lpu(
    caminho_orcamento="data/orcamento.xlsx",
    caminho_lpu="data/lpu.xlsx",
    output_dir="outputs"
)

# 4 arquivos gerados automaticamente ✅
```

### Avançado
```python
from examples.test_validador_lpu import executar_validacao

df = executar_validacao(
    gerar_estatisticas=True,
    gerar_top_divergencias=True,
    gerar_analise_categorias=True,
    top_n=20,
    verbose=True
)

# Terminal: análises impressas
# Arquivos: 4 relatórios completos
```

---

## 🧪 Testar Exportações

```bash
python examples/test_exports.py
```

**Gera em `outputs/test_exports/`:**
- Todos os 4 arquivos padrão
- Arquivo de teste Excel completo
- Arquivo de teste HTML

---

## 📖 Estrutura dos Arquivos

### Excel Básico (4 abas)
```
validacao_lpu.xlsx
├─ Validação Completa
├─ Resumo por Status
├─ Resumo por Categoria
└─ Resumo por UPE
```

### Excel Completo (11+ abas)
```
relatorio_completo_validacao_lpu.xlsx
├─ Estatísticas ⭐
├─ Resumo por Status
├─ Top 10/20 Div Absoluta ⭐
├─ Top 10/20 Div Percentual
├─ Itens Para Ressarcimento ⭐
├─ Itens Abaixo LPU
├─ Análises por Categoria
├─ Análises por UPE
└─ Dados Completos
```

### HTML
```
relatorio_validacao_lpu.html
├─ Header (gradiente roxo)
├─ Estatísticas (7 cards)
├─ Resumo por Status
├─ Top 10 Divergências (R$)
├─ Top 10 Divergências (%)
└─ Análises Categoria/UPE
```

---

## ⚠️ Troubleshooting

### Erro: "No module named 'openpyxl'"
```bash
pip install openpyxl
```

### Erro: "Permission denied"
- Feche os arquivos Excel abertos
- Execute como administrador

### HTML não abre
```bash
# Windows
start chrome outputs\relatorio_validacao_lpu.html

# Mac
open -a "Google Chrome" outputs/relatorio_validacao_lpu.html
```

---

## 📚 Documentação Completa

| Documento | Descrição |
|-----------|-----------|
| **EXPORT_REPORTS.md** | Documentação completa (500 linhas) |
| **CHANGELOG_EXPORTS.md** | Changelog detalhado |
| **SUMMARY_EXPORTS.md** | Resumo visual |
| **QUICKSTART_EXPORTS.md** | Este guia rápido |

---

## 🎯 Próximos Passos

1. ✅ Execute `test_exports.py`
2. ✅ Abra `relatorio_validacao_lpu.html` no navegador
3. ✅ Abra `relatorio_completo_validacao_lpu.xlsx` no Excel
4. ✅ Explore as 11+ abas
5. ✅ Compartilhe os relatórios

---

## 💡 Dicas Rápidas

### Para Análise Rápida
→ Abrir `relatorio_validacao_lpu.html` no navegador

### Para Análise Detalhada
→ Abrir `relatorio_completo_validacao_lpu.xlsx` no Excel

### Para Processamento Automatizado
→ Importar `validacao_lpu.csv` em Python/R

### Para Apresentação
→ Imprimir HTML ou usar abas do Excel

---

**🎉 Tudo pronto! Comece a usar agora!**

```bash
python examples/test_validador_lpu.py
```

**📧 Dúvidas?** Leia `docs/EXPORT_REPORTS.md`
