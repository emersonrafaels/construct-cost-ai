# DataCraft - Verificador Inteligente de Orçamentos de Obras

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Construct Cost AI** é um serviço inteligente de orquestração para validação de orçamentos de obras. Ele combina **validações determinísticas baseadas em regras** com **análises impulsionadas por IA** (via StackSpot AI) para identificar anomalias de preços, desvios de quantidades e itens fora de catálogo em orçamentos de construção.

---

## 🎯 Objetivo

Este serviço valida orçamentos de obras enviados por fornecedores, aplicando:
- **Regras de negócio e limites** (limites de quantidade, faixas de preços, validação de catálogo)
- **Agentes de IA** para análise contextual e avaliação de riscos
- **Resultados estruturados** com níveis de severidade e explicações em linguagem natural
- Suporte a múltiplas interfaces: **API REST**, **UI Streamlit** e **CLI**

---

## 🏗️ Arquitetura

O **Construct Cost AI** foi projetado como uma **camada de orquestração** (não um monolito):

- **Design orientado a objetos** para extensibilidade
- **Validadores determinísticos**: Checagens baseadas em regras (LPU, Match Fuzzy, Match por Contexto)
- **Agentes de IA**: Análise probabilística via API HTTP do StackSpot AI
- **Separação limpa**: Lógica de domínio, infraestrutura, API e camadas de UI

```
src/construct_cost_ai/
├── api/                 # Endpoints REST do FastAPI
├── domain/              # Lógica de negócio principal
│   ├── models.py        # Modelos de domínio do Pydantic
│   ├── orchestrator.py  # Classe principal de orquestração
│   └── validators/      # Validadores determinísticos
├── infra/               # Camada de infraestrutura
│   ├── ai/              # Cliente do StackSpot AI
│   ├── config/          # Configuração do Dynaconf
│   └── logging/         # Configuração do Loguru
app/                     # Frontend Streamlit
cli/                     # CLI baseado em Rich
tests/                   # Testes com pytest
```

---

## ✨ Funcionalidades

### Capacidades Principais
- ✅ **Detecção de desvios de quantidade** (comparação com dados de referência)
- ✅ **Detecção de anomalias de preço unitário** (comparação com tabelas SINAPI/LPU)
- ✅ **Validação de itens fora de catálogo** (identificação de itens não padronizados)
- ✅ **Análise contextual com IA** (avaliação de riscos, explicações)
- ✅ **Agregação de resultados** (por item e por grupo de serviços)
- ✅ **Cálculo de nível de risco** (BAIXO, MÉDIO, ALTO, CRÍTICO)

### Interfaces
- 🌐 **API REST FastAPI** (para integração M2M, ex.: Salesforce)
- 🖥️ **UI Web Streamlit** (upload interativo de arquivos e visualização)
- 💻 **CLI Rich** (validação via terminal com tabelas formatadas)

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.11+
- pip ou uv

### Instalação

```bash
# Clone o repositório
git clone https://github.com/emersonrafaels/construct-cost-ai.git
cd construct-cost-ai

# Crie e ative o ambiente virtual
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### Configuração

1. Copie o arquivo de exemplo `.env`:
```bash
copy .env.example .env
```

2. Edite o arquivo `src/config` e adicione suas credenciais do StackSpot AI:
```env
STACKSPOT_AI_BASE_URL=https://api.stackspot.ai/v1
STACKSPOT_AI_API_KEY=sua-chave-de-api-aqui
```

---

## 📖 Uso

### 1️⃣ Executando o `main_backtest.py`

O arquivo `main_backtest.py` é um exemplo prático para validar orçamentos de obras. Ele pode ser executado diretamente para processar arquivos de entrada e gerar resultados.

**Exemplo de execução:**
```bash
python examples/main_backtest.py
```

## ⚙️ Configuração

A configuração é gerenciada via **Dynaconf** com múltiplas fontes:

1. **`settings.toml`** - Configurações padrão
2. **`.env`** - Variáveis de ambiente
3. **`.secrets.toml`** - Segredos (ignorados pelo git)

## 📊 Logging

O logging é tratado pelo **Loguru** com saída estruturada e nivelada:

- **Console**: Logs coloridos e legíveis
- **Arquivo**: Logs em formato JSON com rotação (configurável)

Os logs são armazenados em `logs/construct_cost_ai.log` (configurável via `settings.toml`).

**Níveis de Log**: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **API Framework**: FastAPI
- **Web UI**: Streamlit
- **CLI**: Typer + Rich
- **Configuration**: Dynaconf
- **Logging**: Loguru
- **Data Validation**: Pydantic
- **HTTP Client**: httpx
- **Testing**: pytest

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 📞 Suporte

Para dúvidas ou problemas:
- Abra uma issue no GitHub
- Contate: Alvaro Antonio Borges (julgalv), Clarissa Simoyama (simoyam), Emerson Vinicius Rafael (emervin), Lucas Ken (kushida), Fabiana Marques Fernandes (fmfcwdv)

---


**Produto: Verificador Inteligente de Orçamentos de Obras**

**Construído com ❤️ por DataCraft.**
