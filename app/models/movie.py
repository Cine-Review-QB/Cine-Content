from datetime import datetime, timezone


# In-memory store acting as a simple database
_movies = [
    {
        "id": 1,
        "title": "O Poderoso Chefão",
        "original_title": "The Godfather",
        "year": 1972,
        "genre": ["Crime", "Drama"],
        "director": "Francis Ford Coppola",
        "synopsis": "A história de uma família mafiosa italiana que tenta proteger seu império do crime enquanto o filho mais novo luta contra sua resistência a se tornar parte dele.",
        "rating": 9.2,
    },
    {
        "id": 2,
        "title": "Interestelar",
        "original_title": "Interstellar",
        "year": 2014,
        "genre": ["Ficção Científica", "Drama", "Aventura"],
        "director": "Christopher Nolan",
        "synopsis": "Um grupo de astronautas viaja por um buraco de minhoca em busca de um novo lar para a humanidade enquanto a Terra está à beira do colapso.",
        "rating": 8.6,
    },
    {
        "id": 3,
        "title": "Parasita",
        "original_title": "Parasite",
        "year": 2019,
        "genre": ["Thriller", "Drama", "Comédia Negra"],
        "director": "Bong Joon-ho",
        "synopsis": "A história de duas famílias de classes sociais opostas na Coreia do Sul que se entrelaçam de maneiras inesperadas.",
        "rating": 8.5,
    },
]

_reviews = [
    {
        "id": 1,
        "movie_id": 1,
        "author": "João Silva",
        "rating": 10,
        "comment": "Uma obra-prima absoluta do cinema. Impossível não se emocionar.",
        "created_at": "2024-01-15T10:30:00",
    },
    {
        "id": 2,
        "movie_id": 2,
        "author": "Maria Souza",
        "rating": 9,
        "comment": "Visualmente deslumbrante e emocionalmente profundo. Nolan no seu melhor.",
        "created_at": "2024-02-20T14:00:00",
    },
]

_next_movie_id = 4
_next_review_id = 3


def get_all_movies():
    return list(_movies)


def get_movie_by_id(movie_id):
    return next((m for m in _movies if m["id"] == movie_id), None)


def create_movie(data):
    global _next_movie_id
    movie = {
        "id": _next_movie_id,
        "title": data["title"],
        "original_title": data.get("original_title", data["title"]),
        "year": data["year"],
        "genre": data.get("genre", []),
        "director": data.get("director", ""),
        "synopsis": data.get("synopsis", ""),
        "rating": data.get("rating"),
    }
    _movies.append(movie)
    _next_movie_id += 1
    return movie


def get_reviews_for_movie(movie_id):
    return [r for r in _reviews if r["movie_id"] == movie_id]


def create_review(movie_id, data):
    global _next_review_id
    review = {
        "id": _next_review_id,
        "movie_id": movie_id,
        "author": data["author"],
        "rating": data["rating"],
        "comment": data.get("comment", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _reviews.append(review)
    _next_review_id += 1
    return review
