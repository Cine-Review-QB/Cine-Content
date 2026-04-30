# Cine-Content

**Content Service** da plataforma **CineReviews** — microsserviço responsável pelo **catálogo de filmes**.
Construído com [Flask](https://flask.palletsprojects.com/) e MongoDB Atlas.

> Reviews, usuários, likes e follows vivem em outros microsserviços (`Cine-Review`, `Cine-Users`).
> Autenticação e roteamento são responsabilidade do `Cine-Api-Gateway`.

---

## Sumário

- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Executando](#executando-o-servidor)
- [Endpoints da API](#endpoints-da-api)
- [Modelo de dados](#modelo-de-dados)
- [Populando o banco](#populando-o-banco)
- [Testes](#testes)
- [Estrutura do projeto](#estrutura-do-projeto)

---

## Arquitetura

O Content Service é um dos serviços de domínio da plataforma CineReviews. Ele é consumido por:

- **API Gateway** (`Cine-Api-Gateway`) — expõe a rota pública `/movies/*` e faz proxy.
- **Review Service** (`Cine-Review`) — chama `GET /api/movies/<id>` para validar a existência de um filme antes de persistir uma review.

```
                ┌──────────┐         ┌──────────────────┐
   Browser ───▶ │ Gateway  │ ──────▶ │  Content Service │ ──▶ MongoDB Atlas
                └──────────┘         └──────────────────┘
                                              ▲
                                              │ HTTP (validação)
                                       ┌──────────────┐
                                       │ Review Svc   │
                                       └──────────────┘
```

---

## Requisitos

- Python **3.10+**
- MongoDB Atlas (ou um Mongo local para desenvolvimento)
- (Opcional) [`uv`](https://docs.astral.sh/uv/) para gerenciar dependências
- API key do [TMDB](https://www.themoviedb.org/settings/api) para popular o banco

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/Cine-Review-QB/Cine-Content.git
cd Cine-Content

# Opção A — uv (recomendado, usa o uv.lock)
uv sync

# Opção B — pip + venv
python -m venv .venv
source .venv/bin/activate         # Linux/macOS
# .venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```bash
MONGO_URI="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
TMDB_API_KEY="<sua_chave_tmdb_v3>"
FLASK_ENV=development
PORT=5000
```

| Variável        | Obrigatória              | Descrição                                                                  |
|-----------------|--------------------------|----------------------------------------------------------------------------|
| `MONGO_URI`     | sim                      | string de conexão MongoDB                                                  |
| `TMDB_API_KEY`  | só para o seed           | chave v3 da TMDB (https://www.themoviedb.org/settings/api)                |
| `FLASK_ENV`     | não (default `development`) | `development` / `testing` / `production`                                |
| `PORT`          | não (default `5000`)     | porta HTTP                                                                 |
| `SECRET_KEY`    | não                      | chave de sessão Flask                                                      |

---

## Executando o servidor

```bash
# Via uv
uv run python app.py

# Ou diretamente (se a venv já estiver ativa)
python app.py
```

Saída esperada:

```
 * Running on http://0.0.0.0:5000
```

Verifique:

```bash
curl http://localhost:5000/health
# {"status":"ok","message":"Cine-Content API está funcionando!"}
```

---

## Endpoints da API

### Health

| Método | Rota      | Descrição                    |
|--------|-----------|------------------------------|
| GET    | `/health` | Verifica se a API está no ar |

### Filmes

| Método | Rota                                       | Descrição                                          |
|--------|--------------------------------------------|----------------------------------------------------|
| GET    | `/api/movies/`                             | Lista filmes paginados (default 20, max 100)       |
| GET    | `/api/movies/?genre=<gênero>&limit=&skip=` | Filtra por gênero e/ou pagina                      |
| GET    | `/api/movies/<id>`                         | Retorna um filme pelo `_id` (ObjectId em string)   |
| POST   | `/api/movies/`                             | Adiciona um novo filme                             |

#### Exemplos

**Listar (paginado, filtro por gênero):**
```bash
curl "http://localhost:5000/api/movies/?genre=Drama&limit=10&skip=0"
```
```json
{
  "movies": [ { "_id": "...", "title": "...", ... } ],
  "total": 1234,
  "limit": 10,
  "skip": 0
}
```

**Buscar por id:**
```bash
curl http://localhost:5000/api/movies/664abc1234567890abcdef12
```

**Criar filme:**
```bash
curl -X POST http://localhost:5000/api/movies/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Um Sonho de Liberdade",
    "original_title": "The Shawshank Redemption",
    "year": 1994,
    "genres": ["Drama"],
    "director": "Frank Darabont",
    "overview": "Andy Dufresne...",
    "rating": 9.3,
    "runtime": 142,
    "imdb_id": "tt0111161"
  }'
```

> Campos obrigatórios no POST: `title`, `year`. Demais campos são opcionais.

#### Códigos de resposta

| Status | Quando                                                   |
|--------|----------------------------------------------------------|
| 200    | GET com sucesso                                          |
| 201    | POST com sucesso                                         |
| 400    | corpo inválido, campos obrigatórios ausentes ou paginação fora dos limites |
| 404    | filme inexistente ou `id` mal formado                    |

---

## Modelo de dados

Collection: **`cinedb.content`** (não `movies`).

```jsonc
{
  "_id": "ObjectId — gerado pelo Mongo",
  "tmdb_id": 862,
  "imdb_id": "tt0111161",
  "title": "string",
  "original_title": "string | null",
  "year": 1999,
  "genres": ["Action", "Drama"],
  "director": "string | null",
  "overview": "string | null",
  "rating": 9.3,
  "runtime": 142,
  "poster_url": "https://image.tmdb.org/t/p/w500/...",
  "backdrop_url": "https://image.tmdb.org/t/p/original/...",
  "cast": ["Tim Robbins", "Morgan Freeman"],
  "language": "en"
}
```

### Índices (criados pelo seed)

| Campo              | Tipo     | Finalidade                                  |
|--------------------|----------|---------------------------------------------|
| `tmdb_id`          | UNIQUE   | chave canônica do TMDB; idempotência do seed|
| `imdb_id`          | UNIQUE   | lookup cruzado por IMDb                     |
| `title`            | TEXT     | busca full-text por nome do filme           |
| `genres`           | ASC      | filtro por gênero                           |
| `rating`           | ASC      | ordenação dos mais bem avaliados            |
| `year`             | ASC      | filtro por ano / década                     |

---

## Populando o banco

O seed busca filmes diretamente da [TMDB API](https://developer.themoviedb.org/) via `/discover/movie` ordenado por popularidade descendente. Para cada filme, faz uma segunda chamada em `/movie/{id}?append_to_response=credits` para obter elenco e diretor.

**Pré-requisitos:**
1. `MONGO_URI` no `.env`.
2. `TMDB_API_KEY` no `.env` (chave v3, gratuita em https://www.themoviedb.org/settings/api).

```bash
# Default: 100 páginas (~2000 filmes mais populares)
uv run python scripts/seed_movies_from_tmdb.py

# Smoke test rápido (~100 filmes)
uv run python scripts/seed_movies_from_tmdb.py --pages 5

# Mais filmes (TMDB limita /discover a 500 páginas = ~10k filmes)
uv run python scripts/seed_movies_from_tmdb.py --pages 250

# Mais agressivo na concorrência
uv run python scripts/seed_movies_from_tmdb.py --concurrency 50
```

O script é **idempotente** (usa `UpdateOne` com `upsert=True` em `tmdb_id`), pode ser executado múltiplas vezes sem duplicar registros — chamadas subsequentes só atualizam dados que mudaram (ex.: pôsteres trocados pelo TMDB).

---

## Testes

```bash
# Rodando com uv
uv run pytest -v

# Ou via venv
python -m pytest tests/ -v
```

Os testes usam [`mongomock`](https://github.com/mongomock/mongomock) — não precisam de um Mongo real. A fixture `client` (em `tests/conftest.py`) injeta a collection fake antes de cada teste.

---

## Estrutura do projeto

```
Cine-Content/
├── app.py                       # entrypoint (carrega .env, sobe Flask)
├── app/
│   ├── __init__.py              # create_app() / registro de blueprints
│   ├── config.py                # configs por ambiente
│   ├── db.py                    # cliente Mongo (singleton)
│   ├── models/movie.py          # operações na collection
│   └── routes/
│       ├── health.py            # GET /health
│       └── movies.py            # /api/movies/*
├── scripts/
│   └── seed_movies_from_tmdb.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Roadmap

- [ ] Cache em Redis para listagem, busca e detalhes (`movies:search:*`, `movies:detail:*`, `movies:popular:*`).
- [ ] Endpoint de busca full-text aproveitando o índice TEXT em `title`.
- [ ] Endpoint `/api/genres` com gêneros distintos.
- [ ] Avaliar migração para FastAPI alinhando com o diagrama de arquitetura.
