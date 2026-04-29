# Cine-Content

Backend da plataforma **Cine-Content** construído com [Flask](https://flask.palletsprojects.com/). Fornece uma API REST para listagem de filmes e gerenciamento de avaliações.

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

| Método | Rota                          | Descrição                         |
|--------|-------------------------------|-----------------------------------|
| GET    | `/api/movies/`                | Lista todos os filmes             |
| GET    | `/api/movies/?genre=<gênero>` | Filtra filmes por gênero          |
| GET    | `/api/movies/<id>`            | Retorna um filme pelo ID          |
| POST   | `/api/movies/`                | Adiciona um novo filme            |

#### Body – POST `/api/movies/`

```json
{
  "title": "Título do Filme",
  "year": 2024,
  "original_title": "Movie Title",
  "genre": ["Ação", "Drama"],
  "director": "Nome do Diretor",
  "synopsis": "Breve descrição do filme.",
  "rating": 8.5
}
```

> Campos obrigatórios: `title`, `year`.

### Avaliações

| Método | Rota                               | Descrição                              |
|--------|------------------------------------|----------------------------------------|
| GET    | `/api/movies/<id>/reviews`         | Lista as avaliações de um filme        |
| POST   | `/api/movies/<id>/reviews`         | Adiciona uma avaliação a um filme      |

#### Body – POST `/api/movies/<id>/reviews`

```json
{
  "author": "Nome do Usuário",
  "rating": 9,
  "comment": "Comentário sobre o filme."
}
```

> Campos obrigatórios: `author`, `rating` (1–10).

---

## Testes

```bash
python -m pytest tests/ -v
```
