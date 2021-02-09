import requests
import pytest
import vcr

import catcherdiff


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/catcherdiff',
    record_mode='none'
)


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@cdm_vcr.use_cassette()
def test_get_cdm_item_info(session):
    item_info = catcherdiff.get_cdm_item_info(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        dmrecord='102',
        session=session
    )
    assert item_info['dmrecord']
    for key, value in item_info.items():
        assert isinstance(value, str)
