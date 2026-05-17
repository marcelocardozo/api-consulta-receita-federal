# API Consulta CNPJ

API que consulta dados de CNPJ na Receita Federal do Brasil, com resolução automática de hCaptcha via Google Gemini AI.

## Requisitos

- Python 3.11+
- Google Gemini API Key ([obter aqui](https://aistudio.google.com/apikey))

## Instalação

```bash
# Criar e ativar virtualenv
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Instalar browsers do Playwright
playwright install chromium
```

## Configuração

Copie o arquivo de exemplo e preencha com suas chaves:

```bash
cp .env.example .env
```

Variáveis disponíveis:

| Variável | Obrigatória | Default | Descrição |
|----------|:-----------:|---------|-----------|
| `GEMINI_API_KEYS` | Sim* | — | Chaves Gemini separadas por vírgula |
| `GEMINI_API_KEY` | Sim* | — | Chave única (fallback) |
| `APP_HOST` | Não | `0.0.0.0` | Host do servidor |
| `APP_PORT` | Não | `8000` | Porta do servidor |
| `BROWSER_HEADLESS` | Não | `true` | Executar browser sem interface |
| `BROWSER_TIMEOUT` | Não | `30000` | Timeout de navegação (ms) |
| `LOG_LEVEL` | Não | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `IP_LOCK_TTL_SECONDS` | Não | `300` | TTL dos locks por IP (segundos) |

*Pelo menos uma das duas variáveis de chave deve ser definida.

## Uso

```bash
venv\Scripts\activate
python run.py
```

A API estará disponível em `http://localhost:8000`. Documentação interativa (Swagger) em `http://localhost:8000/docs`.

## Endpoints

### `GET /cnpj/{cnpj}`

Consulta dados de um CNPJ.

```bash
curl http://localhost:8000/cnpj/11222333000181
```

Resposta:

```json
{
  "sucesso": true,
  "cnpj": "11.222.333/0001-81",
  "razao_social": "EMPRESA EXEMPLO LTDA",
  "nome_fantasia": "EXEMPLO",
  "situacao_cadastral": "ATIVA",
  "cnae_principal": "62.01-5-01 - Desenvolvimento de programas de computador sob encomenda",
  "logradouro": "RUA EXEMPLO",
  "municipio": "SAO PAULO",
  "uf": "SP",
  "socios": [
    { "nome": "FULANO DE TAL", "qualificacao": "Sócio-Administrador" }
  ],
  "tempo_segundos": 12.3
}
```

### `GET /health`

Health check do serviço.

```json
{
  "status": "ok",
  "gemini_keys": 3,
  "ips_ativos": 1
}
```

## Estrutura do Projeto

```
├── app/
│   ├── config.py          # Configuração centralizada (Pydantic Settings)
│   ├── main.py            # App factory, lifespan, logging
│   ├── routes/
│   │   └── cnpj.py        # Endpoints da API
│   ├── services/
│   │   ├── browser.py     # Automação do browser + hCaptcha
│   │   ├── consulta.py    # Validação e orquestração de consulta
│   │   └── parser.py      # Extração de dados do HTML
│   └── models/
│       └── schemas.py     # Modelos de request/response
├── run.py                 # Entry point
├── requirements.txt
├── .env.example
└── iniciar.bat
```
