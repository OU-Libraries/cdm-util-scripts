import pytest
import requests

from cdm_util_scripts import cdm_api


@pytest.mark.vcr
def test_get_cdm_item_info():
    item_info = cdm_api.get_cdm_item_info(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        dmrecord='102',
        session=requests,
    )
    assert item_info['dmrecord']
    for key, value in item_info.items():
        assert isinstance(value, str)

    with pytest.raises(cdm_api.DmError):
        cdm_api.get_cdm_item_info(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='999',
            session=requests,
        )


@pytest.mark.vcr
def test_get_cdm_page_pointers():
    session = requests.Session()
    pointers = cdm_api.get_cdm_page_pointers(
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        dmrecord='4613',
        session=requests,
    )
    assert pointers


@pytest.mark.vcr
def test_get_cdm_collection_field_vocab():
    session = requests.Session()
    vocab = cdm_api.get_cdm_collection_field_vocab(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        cdm_field_nick='subjec',
        session=requests,
    )
    assert vocab


@pytest.mark.parametrize('field_mapping, result', [
    ({'label': ['nick']}, {'nick': 'value'}),
    ({'label': ['nick1', 'nick2']}, {'nick1': 'value', 'nick2': 'value'}),
    ({'blank': ['nick'], 'label': ['nick']}, {'nick': 'value'}),
    ({'label': ['nick'], 'blank': ['nick']}, {'nick': 'value'}),
    ({'blank': ['nick', 'nick']}, {'nick': ''}),
    ({'label': ['nick', 'nick']}, {'nick': 'value; value'}),
    ({'label': ['nick'], 'label2': ['nick']}, {'nick': 'value; value2'}),
    ({'label2': ['nick'], 'label': ['nick']}, {'nick': 'value2; value'}),
])
def test_apply_mapping(field_mapping, result):
    ftp_fields = {
        'label': 'value',
        'label2': 'value2',
        'blank': ''
    }
    mapped = cdm_api.apply_field_mapping(ftp_fields, field_mapping)
    assert mapped == result


@pytest.fixture
def collection_field_info():
    with requests.Session() as session:
        return cdm_api.get_collection_field_info(
            repo_url='https://cdmdemo.contentdm.oclc.org',
            collection_alias='oclcsample',
            session=session,
        )


@pytest.mark.default_cassette("collection_field_info.yaml")
@pytest.mark.vcr
def test_build_vocabs_index(collection_field_info):
    vocabs_index = cdm_api.build_vocabs_index(collection_field_info)
    assert vocabs_index == {'subjec': {'type': 'vocdb', 'name': 'LCTGM'}}


@pytest.mark.default_cassette("collection_field_info.yaml")
@pytest.mark.vcr
def test_get_vocabs(collection_field_info):
    vocabs_index = cdm_api.build_vocabs_index(collection_field_info)
    vocabs = cdm_api.get_vocabs(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        vocabs_index=vocabs_index,
        session=requests,
    )
    assert len(vocabs_index) == (len(vocabs['vocab']) + len(vocabs['vocdb']))
    for nick, index in vocabs_index.items():
        assert index['name'] in vocabs[index['type']]
