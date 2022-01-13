import pytest
from requests import Session


@pytest.fixture(scope='session')
def session():
    with Session() as session:
        yield session
