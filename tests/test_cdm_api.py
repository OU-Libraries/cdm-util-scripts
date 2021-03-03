import pytest
import requests
import vcr

import cdm_api


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/cdm_api',
    record_mode='new_episodes'
)


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@cdm_vcr.use_cassette()
def test_get_cdm_item_info(session):
    item_info = cdm_api.get_cdm_item_info(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        dmrecord='102',
        session=session
    )
    assert item_info['dmrecord']
    for key, value in item_info.items():
        assert isinstance(value, str)

    with pytest.raises(cdm_api.DmError):
        cdm_api.get_cdm_item_info(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='999',
            session=session
        )


@cdm_vcr.use_cassette()
def test_get_cdm_page_pointers(session):
    pointers = cdm_api.get_cdm_page_pointers(
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        dmrecord='4613',
        session=session
    )
    assert pointers