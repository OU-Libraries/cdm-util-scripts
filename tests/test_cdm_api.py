import pytest

from cdm_util_scripts import cdm_api


@pytest.mark.vcr
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


@pytest.mark.vcr
def test_get_cdm_page_pointers(session):
    pointers = cdm_api.get_cdm_page_pointers(
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        dmrecord='4613',
        session=session
    )
    assert pointers


@pytest.mark.vcr
def test_get_cdm_collection_field_vocab(session):
    vocab = cdm_api.get_cdm_collection_field_vocab(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        cdm_field_nick='subjec',
        session=session
    )
    assert vocab
