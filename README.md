[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.129.0-009688.svg)](https://fastapi.tiangolo.com/)

# Tinnova API (FastAPI)

API REST para gerenciamento de veículos, desenvolvida em Python 3.12 com FastAPI, seguindo arquitetura em camadas, autenticação JWT, rate limiting e testes automatizados.

## Requisitos Mínimos

- Python 3.12 (ou 3.10+)
- PostgreSQL
- Redis 7+
- (Opcional) Pipenv

## Configuração do Ambiente

1. **Crie e ative um Ambiente Virtual:**
    ```bash
    python -m venv .venv
    .venv/Scripts/activate
    ```

2. **Configuração de Variáveis de Ambiente:**
   Certifique-se de definir as seguintes variáveis de ambiente no arquivo `.env`:

    ```plaintext
    DATABASE_URL
    DATABASE_URL_SYNC
    JWT_SECRET
    REDIS_URL
   
   (Opcionais)

   JWT_ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES
    EMAIL_ALLOW_DOMAINS
    EMAIL_BLOCK_DOMAINS
    EMAIL_REQUIRE_MX
    PASSWORD_MIN_LENGTH
    PASSWORD_REQUIRE_UPPER
    PASSWORD_REQUIRE_LOWER
    PASSWORD_REQUIRE_DIGIT
    PASSWORD_REQUIRE_SPECIAL
    PASSWORD_SPECIAL_CHARS
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS
    LOGIN_RATE_LIMIT_WINDOW_SECONDS
    LOGIN_RATE_LIMIT_BLOCK_SECONDS
    ```

3. **Instale as dependências do projeto:**
- Com Pipenv
    ```bash
    pipenv shell
    pipenv install
    ```
- Com requirements
    ```bash
    pip install -r requirements-dev.txt
    ```

4. **Migrar o Banco de Dados:**
   1. **Aplicar migrações**
    ```bash
    alembic upgrade head
    ```
   
   2. **Gerar uma nova migração (quando alterar models)**
    ```bash
    alembic revision --autogenerate -m "descricao da migracao"
    ```

## Executando a API

Para iniciar o servidor de desenvolvimento, utilize o comando:

```bash
uvicorn main:app --reload
```

## Rotas da API

Abaixo estão as rotas disponíveis na API:

- **Documentação**

**GET** /docs/ - Swagger UI da API.

**GET** /redoc/ - Documentação interativa da API (ReDoc).

- **Usuários**

**POST** /auth/register - Registra usuário.

**POST** /auth/login - Login via JSON (retorna JWT).

**POST** /auth/login/form - Login via form (usado pelo cadeado do Swagger).

**PATCH** /auth/users/{user_id}/desativar - Desativa usuário (ADMIN).

**PATCH** /auth/users/{user_id}/role — Altera role (ADMIN)

- **Veículos**

**GET** /veiculos — Lista (com filtros e paginação).

**GET** /veiculos/{veiculo_id} — Detalha veículo pelo ID.

**POST** /veiculos — Registra veículo (ADMIN)

**PUT** /veiculos/{veiculo_id} — Atualização total (ADMIN).

**PATCH** /veiculos/{veiculo_id} — Atualização parcial (ADMIN).

**DELETE** /veiculos/{veiculo_id} — Soft delete (ADMIN).

**GET** /veiculos/relatorios/por-marca — Relatório agrupado por marca.

- **Healthcheck**

**GET** /health/ready — Readiness (db/redis/fx)

**Obs: as rotas redirecionam para a documentação Swagger quando acessadas pela rota principal (/).**

## Rodando Testes e Gerando Cobertura

Para garantir que a API está funcionando corretamente, você pode executar os testes e gerar um relatório de cobertura.

### Executando os Testes

1. Para rodar os testes unitários e de integração, utilize o comando:

```bash
pytest -q
```

2. Rodar testes com cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

3. Gerar HTML de cobertura:

```bash
pytest --cov=app --cov-report=html
```

4. Abra o relatório em:

```bash
htmlcov/index.html
```
