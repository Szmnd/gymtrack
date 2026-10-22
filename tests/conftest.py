import pytest

from gymtrack.db import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()
