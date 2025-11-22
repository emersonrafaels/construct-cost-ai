# 🏗️ Construct Cost AI - Verificador Inteligente de Obras

## 📋 Visão Geral

**Construct Cost AI** é um sistema inteligente para validação e conciliação de orçamentos de obras contra bases de preços de referência (LPU - Lista de Preços Unitários). O sistema automatiza a análise de divergências, identifica itens que necessitam ressarcimento e gera relatórios detalhados em múltiplos formatos.

### 🎯 Objetivo

Fornecer uma ferramenta robusta e automatizada para:
- ✅ Validar orçamentos de obras contra bases de preços referenciais
- ✅ Identificar divergências e irregularidades
- ✅ Calcular potencial de ressarcimento
- ✅ Gerar relatórios executivos e técnicos
- ✅ Facilitar auditorias e análises gerenciais

### 🏆 Benefícios

- **Produtividade:** Análises que levavam horas agora levam minutos
- **Precisão:** Cálculos automatizados eliminam erros manuais
- **Rastreabilidade:** Todos os dados e análises documentados
- **Flexibilidade:** Múltiplos formatos de saída (Excel, CSV, HTML)
- **Escalabilidade:** Processa milhares de itens rapidamente

---

## 📚 Documentação Completa

### 🚀 Para Começar

#### 1. [QUICKSTART.md](../QUICKSTART.md) - Início Rápido (5 min)
**Primeiro documento a ler!**

- Instalação e configuração inicial
- Primeiro uso do sistema
- Exemplos básicos de execução
- Verificação de instalação

**👉 Comece aqui se é sua primeira vez usando o sistema**

#### 2. [README.md](../README.md) - Visão Geral do Projeto
- Descrição geral do projeto
- Funcionalidades principais
- Requisitos de sistema
- Links para documentação

---

### 🏗️ Arquitetura e Desenvolvimento

#### 3. [ARCHITECTURE.md](./ARCHITECTURE.md) - Arquitetura do Sistema
**Para desenvolvedores e arquitetos**

- Arquitetura geral do sistema
- Estrutura de módulos e pacotes
- Diagrama de componentes
- Fluxo de dados
- Decisões arquiteturais
- Padrões de projeto utilizados

#### 4. [DEVELOPMENT.md](./DEVELOPMENT.md) - Guia de Desenvolvimento
**Para desenvolvedores contribuindo com o projeto**

- Ambiente de desenvolvimento
- Estrutura do código
- Padrões de código
- Como contribuir
- Testes e validações
- Processo de CI/CD

---

### 📊 Funcionalidade Principal - Validador LPU

#### 5. [README_EXPORTS.md](./README_EXPORTS.md) - Índice de Exportações
**Ponto de entrada para documentação de exportações**

- Índice completo de documentos sobre exportações
- Guia de navegação
- Qual documento ler para cada necessidade

#### 6. [QUICKSTART_EXPORTS.md](./QUICKSTART_EXPORTS.md) - Uso Rápido de Exportações (2 min)
**Como usar as exportações em 30 segundos**

- Comandos básicos
- Como visualizar relatórios
- Troubleshooting rápido
- Dicas práticas

#### 7. [EXPORT_REPORTS.md](./EXPORT_REPORTS.md) - Documentação Completa de Exportações (15 min)
**Documentação técnica detalhada (~500 linhas)**

- Descrição de todos os arquivos gerados
- Estrutura do Excel completo (11+ abas)
- Características do relatório HTML
- Casos de uso avançados
- Personalização e customização
- Troubleshooting detalhado
- Referências técnicas

#### 8. [SUMMARY_EXPORTS.md](./SUMMARY_EXPORTS.md) - Resumo Visual de Exportações (5 min)
**Resumo visual da implementação**

- Fluxo de execução
- Estrutura dos arquivos
- Estatísticas de código
- Casos de uso
- Exemplos práticos

#### 9. [CHANGELOG_EXPORTS.md](./CHANGELOG_EXPORTS.md) - Changelog de Exportações (8 min)
**Histórico de implementação**

- Objetivo alcançado
- Arquivos criados/modificados
- Novas funções implementadas
- Linhas de código adicionadas
- Como testar
- Benefícios alcançados

#### 10. [CHECKLIST_EXPORTS.md](./CHECKLIST_EXPORTS.md) - Checklist de Implementação (5 min)
**Validação da implementação**

- Checklist de código
- Checklist de funcionalidades
- Checklist de testes
- Estatísticas finais
- Status de validação

---

### 📝 Documentos de Referência

#### 11. [PROJECT_SUMMARY.md](../PROJECT_SUMMARY.md) - Resumo do Projeto
- Visão geral executiva
- Histórico de desenvolvimento
- Status atual
- Próximos passos

---

## 🗂️ Estrutura do Projeto

```
construct-cost-ai/
├── 📄 README.md                    # Visão geral do projeto
├── 📄 QUICKSTART.md                # Guia de início rápido
├── 📄 PROJECT_SUMMARY.md           # Resumo executivo
├── 📄 LICENSE                      # Licença do projeto
├── 📄 pyproject.toml               # Configuração do projeto Python
├── 📄 requirements.txt             # Dependências de produção
├── 📄 requirements-dev.txt         # Dependências de desenvolvimento
├── 📄 settings.toml                # Configurações gerais
│
├── 📁 docs/                        # Documentação
│   ├── 📄 INDEX.md                 # Este arquivo (índice principal)
│   ├── 📄 ARCHITECTURE.md          # Arquitetura do sistema
│   ├── 📄 DEVELOPMENT.md           # Guia de desenvolvimento
│   ├── 📄 README_EXPORTS.md        # Índice de exportações
│   ├── 📄 QUICKSTART_EXPORTS.md    # Guia rápido de exportações
│   ├── 📄 EXPORT_REPORTS.md        # Documentação completa de exportações
│   ├── 📄 SUMMARY_EXPORTS.md       # Resumo visual de exportações
│   ├── 📄 CHANGELOG_EXPORTS.md     # Changelog de exportações
│   └── 📄 CHECKLIST_EXPORTS.md     # Checklist de implementação
│
├── 📁 src/                         # Código-fonte
│   └── construct_cost_ai/
│       ├── __init__.py
│       ├── 📁 api/                 # API REST (FastAPI)
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── routes.py
│       │   └── schemas.py
│       │
│       ├── 📁 domain/              # Lógica de negócio
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── orchestrator.py
│       │   ├── validador_lpu.py    # ⭐ Módulo principal
│       │   └── validators/
│       │       ├── __init__.py
│       │       ├── base.py
│       │       └── deterministic.py
│       │
│       └── 📁 infra/               # Infraestrutura
│           ├── __init__.py
│           ├── 📁 ai/              # Integrações com IA
│           │   ├── __init__.py
│           │   └── stackspot_client.py
│           ├── 📁 config/          # Configurações
│           │   ├── __init__.py
│           │   └── config.py
│           └── 📁 logging/         # Sistema de logs
│               ├── __init__.py
│               └── logging_config.py
│
├── 📁 app/                         # Interface Streamlit
│   └── streamlit_app.py
│
├── 📁 cli/                         # Interface CLI
│   └── main.py
│
├── 📁 examples/                    # Exemplos de uso
│   ├── test_validador_lpu.py      # ⭐ Script principal de teste
│   ├── test_exports.py            # Teste de exportações
│   ├── api_request.json           # Exemplo de requisição API
│   └── sample_budget.json         # Exemplo de orçamento
│
├── 📁 tests/                       # Testes automatizados
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_orchestrator.py
│   └── test_validators.py
│
├── 📁 data/                        # Dados de exemplo (não versionado)
│   ├── orcamento_exemplo.xlsx     # Orçamento de exemplo
│   └── lpu_exemplo.xlsx           # LPU de exemplo
│
└── 📁 outputs/                     # Saída de relatórios (não versionado)
    ├── validacao_lpu.xlsx
    ├── validacao_lpu.csv
    ├── relatorio_completo_validacao_lpu.xlsx
    └── relatorio_validacao_lpu.html
```

---

## 🚀 Funcionalidades Principais

### 1. ⭐ Validador LPU - Módulo Principal

**Arquivo:** `src/construct_cost_ai/domain/validador_lpu.py`

#### Funções Principais

##### `validar_lpu()`
Orquestra todo o processo de validação:
1. Carrega orçamento
2. Carrega base LPU
3. Cruza dados por código de item
4. Calcula divergências
5. Gera relatórios automáticos

**Gera 4 arquivos automaticamente:**
- Excel básico (4 abas)
- CSV completo
- Excel completo (11+ abas)
- HTML interativo

##### `gerar_relatorio_excel_completo()`
Gera Excel com 11+ abas:
- Estatísticas gerais
- Top 10/20 divergências (R$ e %)
- Itens para ressarcimento
- Análises por categoria/UPE
- Dataset completo

##### `gerar_relatorio_html()`
Gera dashboard HTML interativo:
- Cards estatísticos coloridos
- Tabelas responsivas
- Top 10 divergências
- Design moderno e profissional

#### Status de Conciliação

| Status | Critério | Ação |
|--------|----------|------|
| **OK** | `-3% ≤ divergência ≤ +3%` | ✅ Aprovado |
| **Para ressarcimento** | `divergência > +3%` | ⚠️ Preço acima da referência |
| **Abaixo LPU** | `divergência < -3%` | 🔴 Preço muito abaixo |

---

### 2. 📊 Sistema de Exportações

#### 4 Arquivos Gerados por Validação

##### 1. Excel Básico (4 abas)
- Validação Completa
- Resumo por Status
- Resumo por Categoria
- Resumo por UPE

##### 2. CSV Completo
- Todos os dados (separador `;`)
- Encoding UTF-8

##### 3. Excel Completo (11+ abas)
- Estatísticas
- Resumo por Status
- Top 10/20 Div Absoluta
- Top 10/20 Div Percentual
- Itens Para Ressarcimento
- Itens Abaixo LPU
- Resumo por Categoria
- Dif por Categoria
- Resumo por UPE
- Dif por UPE
- Dados Completos

##### 4. HTML Interativo
- Dashboard visual
- Cards coloridos
- Tabelas formatadas
- Responsivo e print-friendly

**📖 Documentação:** [EXPORT_REPORTS.md](./EXPORT_REPORTS.md)

---

### 3. 🌐 API REST (FastAPI)

**Arquivo:** `src/construct_cost_ai/api/app.py`

Endpoints disponíveis:
- `POST /validate` - Validar orçamento
- `GET /health` - Status da API
- `GET /docs` - Documentação Swagger

**Como executar:**
```bash
python run_api.py
# Acesse: http://localhost:8000/docs
```

---

### 4. 🖥️ Interface Web (Streamlit)

**Arquivo:** `app/streamlit_app.py`

Interface visual para:
- Upload de arquivos
- Configuração de validação
- Visualização de resultados
- Download de relatórios

**Como executar:**
```bash
streamlit run app/streamlit_app.py
```

---

### 5. 💻 Interface CLI

**Arquivo:** `cli/main.py`

Linha de comando para automação:
```bash
python -m cli.main validate \
  --orcamento data/orcamento.xlsx \
  --lpu data/lpu.xlsx \
  --output outputs/
```

---

## 🔧 Tecnologias Utilizadas

### Core
- **Python 3.10+** - Linguagem principal
- **Pandas** - Manipulação de dados
- **openpyxl** - Geração de Excel

### APIs e Interfaces
- **FastAPI** - API REST
- **Streamlit** - Interface web
- **Click** - Interface CLI

### Infraestrutura
- **Dynaconf** - Gerenciamento de configurações
- **Loguru** - Sistema de logs
- **Pydantic** - Validação de dados

### Desenvolvimento
- **pytest** - Testes automatizados
- **black** - Formatação de código
- **ruff** - Linting

---

## 📊 Fluxo de Validação

```
┌─────────────────────────────────────────────────────────────┐
│                   VALIDADOR LPU                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. CARREGAR ORÇAMENTO                                      │
│     ├─ Ler arquivo Excel                                    │
│     ├─ Validar estrutura                                    │
│     └─ Normalizar dados                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. CARREGAR LPU (Base de Preços)                           │
│     ├─ Ler múltiplas fontes (SINAPI, SICRO, etc.)          │
│     ├─ Consolidar bases                                     │
│     └─ Indexar por código                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. CRUZAR DADOS                                            │
│     ├─ Merge por código de item                             │
│     ├─ Identificar itens sem correspondência                │
│     └─ Preparar dataset unificado                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. CALCULAR DIVERGÊNCIAS                                   │
│     ├─ Diferença unitária (orçado - LPU)                    │
│     ├─ Divergência percentual                               │
│     ├─ Divergência total (qtde × dif_unitária)              │
│     └─ Status de conciliação (OK/Ressarcimento/Abaixo)      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. GERAR RELATÓRIOS                                        │
│     ├─ Excel Básico (4 abas)                                │
│     ├─ CSV Completo                                         │
│     ├─ Excel Completo (11+ abas)                            │
│     └─ HTML Interativo                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ✅ CONCLUÍDO
```

---

## 🎯 Casos de Uso

### 1. Análise Rápida de Orçamento
```python
from construct_cost_ai.domain.validador_lpu import validar_lpu

df = validar_lpu(
    caminho_orcamento="data/orcamento.xlsx",
    caminho_lpu="data/lpu.xlsx",
    output_dir="outputs"
)

# 4 arquivos gerados automaticamente
# Abrir relatorio_validacao_lpu.html no navegador
```

### 2. Auditoria Detalhada
```python
from examples.test_validador_lpu import executar_validacao

df = executar_validacao(
    verbose=True,
    gerar_estatisticas=True,
    gerar_top_divergencias=True,
    gerar_analise_categorias=True,
    gerar_analise_upes=True,
    top_n=20
)

# Análises completas no terminal + 4 arquivos
```

### 3. Filtrar Itens Problemáticos
```python
df = executar_validacao(
    filtro_percentual=15.0,        # > 15% de divergência
    filtro_categoria="Estrutura",  # Categoria específica
    gerar_top_divergencias=True
)
```

### 4. Integração via API
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: multipart/form-data" \
  -F "orcamento=@orcamento.xlsx" \
  -F "lpu=@lpu.xlsx"
```

### 5. Automação em Lote
```bash
# Script CLI para múltiplos orçamentos
for file in data/orcamentos/*.xlsx; do
  python -m cli.main validate \
    --orcamento "$file" \
    --lpu data/lpu.xlsx \
    --output "outputs/$(basename $file)"
done
```

---

## 🧪 Como Testar

### 1. Verificar Instalação
```bash
python verify_installation.py
```

### 2. Teste Rápido
```bash
python examples/test_validador_lpu.py
# Menu: escolha opção 3 (Validação simples)
```

### 3. Teste de Exportações
```bash
python examples/test_exports.py
```

### 4. Testes Automatizados
```bash
pytest tests/ -v
```

### 5. Verificar Arquivos Gerados
```bash
cd outputs
dir  # Windows
ls   # Linux/Mac
```

**Arquivos esperados:**
- ✅ `validacao_lpu.xlsx`
- ✅ `validacao_lpu.csv`
- ✅ `relatorio_completo_validacao_lpu.xlsx`
- ✅ `relatorio_validacao_lpu.html`

---

## 📖 Guia de Leitura por Perfil

### 👔 Gestor / Tomador de Decisão
1. [INDEX.md](./INDEX.md) - Este documento (visão geral)
2. [README.md](../README.md) - Visão do projeto
3. [QUICKSTART_EXPORTS.md](./QUICKSTART_EXPORTS.md) - Como usar (2 min)
4. Executar: `python examples/test_validador_lpu.py`
5. Abrir: `outputs/relatorio_validacao_lpu.html`

### 👨‍💻 Desenvolvedor Novo no Projeto
1. [README.md](../README.md) - Visão geral
2. [QUICKSTART.md](../QUICKSTART.md) - Configuração inicial
3. [ARCHITECTURE.md](./ARCHITECTURE.md) - Arquitetura
4. [DEVELOPMENT.md](./DEVELOPMENT.md) - Guia de desenvolvimento
5. [INDEX.md](./INDEX.md) - Este documento (referência completa)

### 📊 Analista / Usuário Final
1. [QUICKSTART.md](../QUICKSTART.md) - Como começar
2. [QUICKSTART_EXPORTS.md](./QUICKSTART_EXPORTS.md) - Usar exportações
3. [EXPORT_REPORTS.md](./EXPORT_REPORTS.md) - Entender relatórios
4. Executar: `python examples/test_validador_lpu.py`

### 🏗️ Arquiteto de Software
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - Arquitetura completa
2. [INDEX.md](./INDEX.md) - Este documento
3. [DEVELOPMENT.md](./DEVELOPMENT.md) - Padrões e práticas
4. Revisar: `src/construct_cost_ai/domain/validador_lpu.py`

### 🔧 DevOps / Infraestrutura
1. [README.md](../README.md) - Requisitos de sistema
2. [DEVELOPMENT.md](./DEVELOPMENT.md) - Ambiente e deploy
3. Revisar: `requirements.txt`, `pyproject.toml`
4. Configurar: `settings.toml`

---

## 🔗 Links Rápidos

### Código-Fonte Principal
- [validador_lpu.py](../src/construct_cost_ai/domain/validador_lpu.py) - Módulo principal
- [test_validador_lpu.py](../examples/test_validador_lpu.py) - Script de teste
- [test_exports.py](../examples/test_exports.py) - Teste de exportações

### Documentação Essencial
- [INDEX.md](./INDEX.md) - Este documento
- [QUICKSTART.md](../QUICKSTART.md) - Início rápido
- [EXPORT_REPORTS.md](./EXPORT_REPORTS.md) - Exportações completas

### Configuração
- [settings.toml](../settings.toml) - Configurações gerais
- [pyproject.toml](../pyproject.toml) - Configuração do projeto
- [requirements.txt](../requirements.txt) - Dependências

---

## ⚠️ Troubleshooting Rápido

### Erro: "No module named 'construct_cost_ai'"
```bash
pip install -e .
# ou
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Erro: "No module named 'openpyxl'"
```bash
pip install openpyxl
```

### Arquivos não gerados
- Verificar permissões do diretório `outputs/`
- Fechar arquivos Excel abertos
- Verificar logs em `logs/`

### HTML não abre
```bash
# Windows
start chrome outputs\relatorio_validacao_lpu.html

# Mac
open -a "Google Chrome" outputs/relatorio_validacao_lpu.html
```

**Mais problemas?** Consulte [EXPORT_REPORTS.md](./EXPORT_REPORTS.md) - Seção Troubleshooting

---

## 🚀 Próximos Passos

### Curto Prazo (em desenvolvimento)
- [ ] Gráficos no relatório HTML (Chart.js)
- [ ] Exportação para PDF
- [ ] Dashboard web com filtros interativos
- [ ] Suporte a mais bases de preços

### Médio Prazo (planejado)
- [ ] Machine Learning para detecção de anomalias
- [ ] Análise preditiva de custos
- [ ] Integração com sistemas corporativos
- [ ] API de notificações

### Longo Prazo (roadmap)
- [ ] Módulo de análise temporal de preços
- [ ] Benchmarking entre projetos
- [ ] Recomendações automatizadas
- [ ] Integração com BI tools

---

## 📊 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| **Linhas de código** | ~2.500 |
| **Linhas de documentação** | ~3.500 |
| **Módulos principais** | 3 |
| **Funções públicas** | 15+ |
| **Testes automatizados** | 20+ |
| **Formatos de saída** | 4 |
| **Abas no Excel completo** | 11+ |

---

## 📧 Suporte e Contribuição

### Reportar Problemas
1. Verificar se já existe issue aberta
2. Incluir logs e arquivos de exemplo
3. Descrever passos para reproduzir

### Contribuir com Código
1. Ler [DEVELOPMENT.md](./DEVELOPMENT.md)
2. Fork do repositório
3. Criar branch feature
4. Enviar Pull Request

### Sugestões e Melhorias
- Abrir issue com tag "enhancement"
- Descrever caso de uso
- Incluir exemplos se possível

---

## 📜 Licença

Este projeto está sob a licença especificada no arquivo [LICENSE](../LICENSE).

---

## 🎯 Resumo Executivo

### O que é?
Sistema automatizado para validação de orçamentos de obras contra bases de preços de referência (LPU).

### Para que serve?
- Identificar divergências e irregularidades em orçamentos
- Calcular potencial de ressarcimento
- Gerar relatórios executivos e técnicos
- Facilitar auditorias e análises gerenciais

### Principais Benefícios?
- ⚡ **Rapidez:** Análises em minutos (antes: horas)
- 🎯 **Precisão:** Cálculos automatizados (zero erros manuais)
- 📊 **Relatórios:** 4 formatos (Excel básico, Excel completo, CSV, HTML)
- 🔍 **Rastreabilidade:** Tudo documentado e auditável
- 🚀 **Escalabilidade:** Milhares de itens processados rapidamente

### Como Começar?
1. Ler [QUICKSTART.md](../QUICKSTART.md) (5 minutos)
2. Executar `python examples/test_validador_lpu.py`
3. Abrir `outputs/relatorio_validacao_lpu.html` no navegador
4. Explorar os 4 arquivos gerados

---

**🏗️ Construct Cost AI - Verificador Inteligente de Obras**

**Versão:** 2.0.0  
**Data:** Novembro 2025  
**Status:** Produção ✅

---

*Desenvolvido com ❤️ para otimizar a gestão de custos em obras de infraestrutura*

**📖 Documentação Completa:** [docs/](.)  
**🚀 Início Rápido:** [QUICKSTART.md](../QUICKSTART.md)  
**💻 Código:** [src/construct_cost_ai/](../src/construct_cost_ai/)  
**📊 Exemplos:** [examples/](../examples/)
