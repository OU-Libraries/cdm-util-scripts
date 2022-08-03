import pytest

from cdm_util_scripts import catcherdiff
from cdm_util_scripts import cdm_api


@pytest.mark.vcr
@pytest.fixture()
def collection_field_info(session):
    return cdm_api.get_collection_field_info(
        repo_url='https://cdmdemo.contentdm.oclc.org',
        collection_alias='oclcsample',
        session=session,
    )


def test_build_vocabs_index(collection_field_info):
    vocabs_index = catcherdiff.build_vocabs_index(collection_field_info)
    assert vocabs_index == {'subjec': {'type': 'vocdb', 'name': 'LCTGM'}}


@pytest.mark.vcr
def test_get_vocabs(collection_field_info, session):
    vocabs_index = catcherdiff.build_vocabs_index(collection_field_info)
    vocabs = catcherdiff.get_vocabs(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        vocabs_index=vocabs_index,
        session=session
    )
    assert len(vocabs_index) == (len(vocabs['vocab']) + len(vocabs['vocdb']))
    for nick, index in vocabs_index.items():
        assert index['name'] in vocabs[index['type']]


@pytest.mark.parametrize('cdm_catcher_edits, cdm_items_info, result', [
    (
        [{'dmrecord': '1', 'nick': 'value1'}],
        [{'dmrecord': '1', 'nick': 'value2', 'extra': 'extra'}],
        [({'dmrecord': '1', 'nick': 'value1'}, {'dmrecord': '1', 'nick': 'value2'})]
    )
])
def test_collate_deltas(cdm_catcher_edits, cdm_items_info, result):
    deltas = catcherdiff.collate_deltas(
        cdm_catcher_edits=cdm_catcher_edits,
        cdm_items_info=cdm_items_info
    )
    assert deltas == result


@pytest.mark.parametrize('cdm_catcher_edits, cdm_items_info', [
    (
        [{'dmrecord': '1', 'nick': 'value1', 'wrong': 'wrong1'}],
        [{'dmrecord': '1', 'nick': 'value2', 'extra': 'extra'}]
    )
])
def test_collate_deltas_raises(cdm_catcher_edits, cdm_items_info):
    with pytest.raises(KeyError):
        catcherdiff.collate_deltas(
            cdm_catcher_edits=cdm_catcher_edits,
            cdm_items_info=cdm_items_info
        )


def test_report_to_html(collection_field_info):
    report_base = {
        'cdm_repo_url': 'https://cdmdemo.contentdm.oclc.org',
        'cdm_collection_alias': 'oclcsample',
        'cdm_fields_info': collection_field_info,
        'vocabs_index': catcherdiff.build_vocabs_index(collection_field_info),
        'catcher_json_file': 'catcher-edits.json',
        'report_file': 'catcherdiff-report.html',
        'report_datetime': '2021-01-01T00:00:00.000000',
        'deltas': [
            (
                {'dmrecord': '1', 'subjec': 'value1'},
                {'dmrecord': '1', 'subjec': 'value2'}
            )
        ],
        'cdm_nick_to_name': {
            field_info['nick']: field_info['name'] for field_info in collection_field_info
        },
    }

    assert catcherdiff.report_to_html({
        **report_base,
        'vocabs': None,
    })

    assert catcherdiff.report_to_html({
        **report_base,
        'vocabs': {
            'vocab': {},
            'vocdb': {
                'LCTGM': ['value1']
            }
        },
    })
