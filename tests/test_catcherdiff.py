import requests
import pytest
import vcr

import catcherdiff
from printcdminfo import DmError


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/catcherdiff',
    record_mode='none'
)


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@cdm_vcr.use_cassette('cdmdemo')
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

    with pytest.raises(DmError):
        catcherdiff.get_cdm_item_info(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='999',
            session=session
        )


@cdm_vcr.use_cassette('cdmdemo')
def test_get_cdm_collection_field_vocab(session):
    vocab = catcherdiff.get_cdm_collection_field_vocab(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        cdm_field_nick='subjec',
        session=session
    )
    assert vocab


@cdm_vcr.use_cassette('cdmdemo')
def test_get_cdm_collection_vocabs(session):
    vocabs = catcherdiff.get_cdm_collection_vocabs(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        session=session
    )
    assert 'subjec' in vocabs


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


def test_report_to_html():
    report_html = catcherdiff.report_to_html({
        'cdm_repo_url': 'https://cdmdemo.contentdm.oclc.org',
        'cdm_collection_alias': 'oclcsample',
        'cdm_fields_info': [{
            'name': 'Field',
            'nick': 'nick',
            'admin': 0
        }],
        'catcher_json_file': 'catcher-edits.json',
        'report_file': 'catcherdiff-report.html',
        'report_datetime': '2021-01-01T00:00:00.000000',
        'deltas': [
            (
                {'dmrecord': '1', 'nick': 'value1'},
                {'dmrecord': '1', 'nick': 'value2'}
            )
        ],
    })
    assert report_html
