"""
Baixa o dataset 'rounakbanik/the-movies-dataset' do Kaggle e popula a coleção
`movies` no MongoDB Atlas seguindo o schema definido na arquitetura do
CineReviews.

Uso:
    python scripts/seed_movies_from_kaggle.py
    python scripts/seed_movies_from_kaggle.py --limit 1000   # teste rápido
    python scripts/seed_movies_from_kaggle.py --skip-download # se já baixou

Pré-requisitos:
    - ~/.kaggle/kaggle.json com credenciais (chmod 600)
    - MONGO_URI no .env apontando para o cluster
"""

import argparse
import ast
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne, ASCENDING, TEXT
from pymongo.errors import BulkWriteError
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATASET = "rounakbanik/the-movies-dataset"
DB_NAME = "cinedb"
COLL_NAME = "content"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
CHUNK_SIZE = 1000


def download_dataset() -> None:
    """Baixa e descompacta o dataset do Kaggle em data/."""
    DATA_DIR.mkdir(exist_ok=True)
    # Import tardio: a lib `kaggle` valida credenciais no import.
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    print(f"[download] baixando {DATASET} para {DATA_DIR}/ ...")
    api.dataset_download_files(DATASET, path=str(DATA_DIR), quiet=False)

    zip_path = DATA_DIR / "the-movies-dataset.zip"
    if zip_path.exists():
        print("[download] descompactando ...")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(DATA_DIR)
        zip_path.unlink()
    print("[download] OK")


def safe_literal_eval(value):
    """Parse seguro de strings tipo "[{'id':1,'name':'Drama'}]"."""
    if pd.isna(value) or value == "":
        return []
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []


def parse_year(release_date) -> int | None:
    if pd.isna(release_date) or not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except (ValueError, TypeError):
        return None


def parse_int(value) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_float(value) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def build_document(row) -> dict | None:
    """Monta o documento conforme schema do MongoDB. Retorna None se inválido."""
    imdb_id = row.get("imdb_id")
    if pd.isna(imdb_id) or not imdb_id:
        return None

    title = row.get("title")
    if pd.isna(title) or not title:
        return None

    genres = [g["name"] for g in safe_literal_eval(row.get("genres")) if "name" in g]

    cast_list = safe_literal_eval(row.get("cast"))
    cast_list.sort(key=lambda c: c.get("order", 999))
    cast_top5 = [c["name"] for c in cast_list[:5] if "name" in c]

    crew_list = safe_literal_eval(row.get("crew"))
    director = next(
        (c["name"] for c in crew_list if c.get("job") == "Director"),
        None,
    )

    poster_path = row.get("poster_path")
    poster_url = (
        f"{POSTER_BASE}{poster_path}"
        if isinstance(poster_path, str) and poster_path
        else None
    )

    return {
        "title": title,
        "original_title": row.get("original_title")
            if not pd.isna(row.get("original_title")) else None,
        "genres": genres,
        "rating": parse_float(row.get("vote_average")),
        "year": parse_year(row.get("release_date")),
        "runtime": parse_int(row.get("runtime")),
        "overview": row.get("overview")
            if not pd.isna(row.get("overview")) else None,
        "poster_url": poster_url,
        "director": director,
        "cast": cast_top5,
        "language": row.get("original_language")
            if not pd.isna(row.get("original_language")) else None,
        "imdb_id": imdb_id,
    }


def load_and_merge(limit: int | None = None) -> pd.DataFrame:
    metadata_path = DATA_DIR / "movies_metadata.csv"
    credits_path = DATA_DIR / "credits.csv"

    if not metadata_path.exists() or not credits_path.exists():
        sys.exit(
            f"[erro] CSVs não encontrados em {DATA_DIR}. "
            "Rode sem --skip-download primeiro."
        )

    print("[load] lendo movies_metadata.csv ...")
    # low_memory=False evita warnings de tipos mistos
    meta = pd.read_csv(metadata_path, low_memory=False)
    # Algumas linhas têm 'id' inválido (ex: datas mal formatadas) — descartamos.
    meta = meta[meta["id"].apply(lambda x: str(x).isdigit())].copy()
    meta["id"] = meta["id"].astype(int)

    print("[load] lendo credits.csv ...")
    credits = pd.read_csv(credits_path)
    credits["id"] = credits["id"].astype(int)

    print("[load] merge ...")
    df = meta.merge(credits, on="id", how="left")

    if limit:
        df = df.head(limit)

    print(f"[load] {len(df)} linhas após merge")
    return df


def upsert_chunk(collection, ops: list[UpdateOne]) -> tuple[int, int]:
    """Executa bulk_write tolerando erros de duplicata residuais."""
    if not ops:
        return 0, 0
    try:
        result = collection.bulk_write(ops, ordered=False)
        return result.upserted_count, result.modified_count
    except BulkWriteError as bwe:
        # Mostra apenas o resumo — erros de duplicata podem aparecer em
        # corridas concorrentes. Não interrompe a ingestão.
        print(f"[warn] bulk_write parcial: {bwe.details.get('writeErrors', [])[:3]}")
        return 0, 0


def seed(df: pd.DataFrame, mongo_uri: str) -> None:
    client = MongoClient(mongo_uri)
    coll = client[DB_NAME][COLL_NAME]

    print(f"[mongo] conectado a {DB_NAME}.{COLL_NAME}")

    seen_imdb_ids = set()
    ops: list[UpdateOne] = []
    total_upserted = 0
    total_modified = 0
    skipped = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc="processando"):
        doc = build_document(row)
        if doc is None:
            skipped += 1
            continue

        # Deduplicação intra-batch: o índice unique já cobre, mas evita
        # WriteError barulhento quando o mesmo imdb_id aparece duas vezes.
        if doc["imdb_id"] in seen_imdb_ids:
            skipped += 1
            continue
        seen_imdb_ids.add(doc["imdb_id"])

        ops.append(
            UpdateOne(
                {"imdb_id": doc["imdb_id"]},
                {"$set": doc},
                upsert=True,
            )
        )

        if len(ops) >= CHUNK_SIZE:
            up, mod = upsert_chunk(coll, ops)
            total_upserted += up
            total_modified += mod
            ops = []

    # Resto
    up, mod = upsert_chunk(coll, ops)
    total_upserted += up
    total_modified += mod

    print(
        f"[mongo] inseridos: {total_upserted} | atualizados: {total_modified} "
        f"| pulados: {skipped}"
    )

    print("[mongo] criando índices ...")
    coll.create_index([("imdb_id", ASCENDING)], unique=True, name="imdb_id_unique")
    # default_language="none" desativa stemming; language_override aponta para
    # um campo inexistente para que o Mongo nunca tente usar o `language` do
    # doc como override (códigos como "zh"/"ja" não são stemmers válidos).
    coll.create_index(
        [("title", TEXT)],
        name="title_text",
        default_language="none",
        language_override="_text_language",
    )
    coll.create_index([("genres", ASCENDING)], name="genres_idx")
    coll.create_index([("rating", ASCENDING)], name="rating_idx")
    coll.create_index([("year", ASCENDING)], name="year_idx")
    print("[mongo] índices OK")

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-download", action="store_true",
        help="pula o download (usa CSVs já em data/)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="processa apenas as N primeiras linhas (debug)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        sys.exit("[erro] MONGO_URI ausente no .env")

    if not args.skip_download:
        download_dataset()

    df = load_and_merge(limit=args.limit)
    seed(df, mongo_uri)


if __name__ == "__main__":
    main()
