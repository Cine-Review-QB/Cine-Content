import mongomock
import pytest

from app import create_app
from app.db import set_collection


@pytest.fixture
def client():
    fake_coll = mongomock.MongoClient()["cinedb"]["content"]
    set_collection(fake_coll)

    app = create_app("testing")
    with app.test_client() as test_client:
        yield test_client
