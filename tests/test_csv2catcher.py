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


@pytest.fixture()
def cdm_collection():
    return [
        csv2catcher.CdmObject(pointer='1', identifier='test01', is_cpd=False),
        csv2catcher.CdmObject(pointer='2', identifier='test02', is_cpd=False),
        csv2catcher.CdmObject(pointer='457',
                              identifier='ryan_box09-tld_f11',
                              is_cpd=True,
                              page_pointers=['452', '453', '454', '455', '456'])
    ]


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


def test_build_cdm_identifier_index(cdm_collection):
    cdm_index = csv2catcher.build_cdm_identifier_index(cdm_collection)
    assert len(cdm_collection) == len(cdm_index)
    for cdm_object in cdm_collection:
        assert cdm_object.identifier in cdm_index

    with pytest.raises(ValueError):
        cdm_collection.append(cdm_collection[0])
        csv2catcher.build_cdm_identifier_index(cdm_collection)
