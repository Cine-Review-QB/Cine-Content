# Cine-Content

**Content Service** da plataforma CineReviews — microsserviço responsável pelo catálogo de filmes. Construído com [Flask](https://flask.palletsprojects.com/) e MongoDB Atlas.

> Reviews, usuários e likes vivem em outros microsserviços (Review Service, Auth Service).

---

## Requisitos

- Python 3.10+

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/Cine-Review-QB/Cine-Content.git
cd Cine-Content

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente (opcional)
cp .env.example .env
```

---

## Executando o servidor

```bash
python app.py
```

O servidor estará disponível em `http://localhost:5000`.

---

## Endpoints da API

### Health

| Método | Rota      | Descrição                    |
|--------|-----------|------------------------------|
| GET    | `/health` | Verifica se a API está no ar |

### Filmes

| Método | Rota                                          | Descrição                                          |
|--------|-----------------------------------------------|----------------------------------------------------|
| GET    | `/api/movies/`                                | Lista filmes paginados (default 20, max 100)       |
| GET    | `/api/movies/?genre=<gênero>&limit=&skip=`    | Filtra por gênero e/ou pagina                      |
| GET    | `/api/movies/<id>`                            | Retorna um filme pelo `_id` (ObjectId)             |
| POST   | `/api/movies/`                                | Adiciona um novo filme                             |

#### Body – POST `/api/movies/`

```json
{
  "title": "Título do Filme",
  "original_title": "Movie Title",
  "year": 2024,
  "genres": ["Ação", "Drama"],
  "director": "Nome do Diretor",
  "overview": "Breve descrição do filme.",
  "rating": 8.5,
  "runtime": 120,
  "poster_url": "https://...",
  "cast": ["Ator 1", "Ator 2"],
  "language": "pt",
  "imdb_id": "tt1234567"
}
```

> Campos obrigatórios: `title`, `year`.

---

## Popular o banco

```bash
# Configure MONGO_URI no .env e KAGGLE_API_TOKEN
uv run python scripts/seed_movies_from_kaggle.py
```

---

## Testes

```bash
python -m pytest tests/ -v
```
