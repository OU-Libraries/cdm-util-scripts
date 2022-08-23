import pytest
import requests

from cdm_util_scripts import cdm_api


@pytest.mark.vcr
def test_request_collection_list():
    with requests.Session() as session:
        collection_list = cdm_api.request_collection_list(
            instance_url="https://cdmdemo.contentdm.oclc.org",
            session=session,
        )
    for collection_info in collection_list:
        assert isinstance(collection_info, cdm_api.CdmCollectionInfo)
        assert collection_info.alias
        assert collection_info.name


@pytest.mark.parametrize(
    "field_info, vocab_info",
    [
        (
            cdm_api.CdmFieldInfo(
                name="Subject",
                nick="subjec",
                type="TEXT",
                size=0,
                find="a5",
                req=0,
                search=1,
                hide=0,
                vocdb="LCTGM",
                vocab=1,
                dc="Subject",
                admin=0,
                readonly=0,
            ),
            cdm_api.CdmVocabInfo(vocab_type=cdm_api.CdmVocabType.builtin, key="LCTGM"),
        ),
        (
            cdm_api.CdmFieldInfo(
                name="Subject",
                nick="subjec",
                type="TEXT",
                size=0,
                find="a5",
                req=0,
                search=1,
                hide=0,
                vocdb="",
                vocab=1,
                dc="Subject",
                admin=0,
                readonly=0,
            ),
            cdm_api.CdmVocabInfo(vocab_type=cdm_api.CdmVocabType.custom, key="subjec"),
        ),
        (
            cdm_api.CdmFieldInfo(
                name="Title",
                nick="title",
                type="TEXT",
                size=0,
                find="a0",
                req=1,
                search=1,
                hide=0,
                vocdb="",
                vocab=0,
                dc="Title",
                admin=0,
                readonly=0,
            ),
            None,
        ),
    ],
)
def test_CdmFieldInfo_get_vocab_info(field_info, vocab_info):
    assert field_info.get_vocab_info() == vocab_info


@pytest.mark.default_cassette("field_infos.yaml")
@pytest.mark.vcr
def test_request_field_infos():
    with requests.Session() as session:
        field_infos = cdm_api.request_field_infos(
            instance_url="https://cdmdemo.contentdm.oclc.org",
            collection_alias="oclcsample",
            session=session
        )
    for field_info in field_infos:
        assert isinstance(field_info, cdm_api.CdmFieldInfo)
        assert field_info.name
        assert field_info.nick
        assert True if field_info.dc is None else field_info.dc.istitle()


@pytest.mark.vcr
def test_request_item_info():
    with requests.Session() as session:
        item_info = cdm_api.request_item_info(
            instance_url="https://cdmdemo.contentdm.oclc.org",
            collection_alias="oclcsample",
            dmrecord="102",
            session=session,
        )
    assert item_info["dmrecord"]
    for key, value in item_info.items():
        assert isinstance(value, str)

    with pytest.raises(cdm_api.DmError):
        with requests.Session() as session:
            cdm_api.request_item_info(
                instance_url="https://cdmdemo.contentdm.oclc.org",
                collection_alias="oclcsample",
                dmrecord="999",
                session=session,
            )


@pytest.mark.vcr
def test_request_field_vocab():
    with requests.Session() as session:
        vocab = cdm_api.request_field_vocab(
            instance_url="https://cdmdemo.contentdm.oclc.org",
            collection_alias="oclcsample",
            field_nick="subjec",
            session=session,
        )
    assert vocab


@pytest.mark.vcr
def test_request_page_pointers():
    with requests.Session() as session:
        pointers = cdm_api.request_page_pointers(
            instance_url="https://cdmdemo.contentdm.oclc.org",
            collection_alias="oclcsample",
            dmrecord="93",
            session=session,
        )
        monograph_pointers = cdm_api.request_page_pointers(
            instance_url="https://cdmdemo.contentdm.oclc.org",
            collection_alias="oclcsample",
            dmrecord="102",
            session=session,
        )
    assert pointers
    assert monograph_pointers


@pytest.mark.parametrize(
    "field_mapping, result",
    [
        ({"label": ["nick"]}, {"nick": "value"}),
        ({"label": ["nick1", "nick2"]}, {"nick1": "value", "nick2": "value"}),
        ({"blank": ["nick"], "label": ["nick"]}, {"nick": "value"}),
        ({"label": ["nick"], "blank": ["nick"]}, {"nick": "value"}),
        ({"blank": ["nick", "nick"]}, {"nick": ""}),
        ({"label": ["nick", "nick"]}, {"nick": "value; value"}),
        ({"label": ["nick"], "label2": ["nick"]}, {"nick": "value; value2"}),
        ({"label2": ["nick"], "label": ["nick"]}, {"nick": "value2; value"}),
    ],
)
def test_apply_mapping(field_mapping, result):
    ftp_fields = {"label": "value", "label2": "value2", "blank": ""}
    mapped = cdm_api.apply_field_mapping(ftp_fields, field_mapping)
    assert mapped == result
