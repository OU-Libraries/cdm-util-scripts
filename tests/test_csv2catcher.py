import pytest
import vcr
import requests

import sys
from pathlib import Path

sys.path.append(str(Path('.').absolute()))
import csv2catcher


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/csv2catcher',
    record_mode='once'
)


@pytest.fixture(scope='module')
def session():
    with requests.Session() as session:
        yield session


def test_get_cdm_collection(session):
    with cdm_vcr.use_cassette('test_get_cdm_collection.yml'):
        cdm_collection = csv2catcher.get_cdm_collection(repo_url='https://media.library.ohio.edu',
                                                        alias='p15808coll15',
                                                        id_field_nick='identi',
                                                        session=session)
        assert cdm_collection


def test_get_cdm_page_pointers(session):
    with cdm_vcr.use_cassette('test_get_cdm_page_pointers.yml'):
        pointers = csv2catcher.get_cdm_page_pointers(repo_url='https://media.library.ohio.edu',
                                                     alias='p15808coll15',
                                                     dmrecord='969',
                                                     session=session)
        assert pointers


