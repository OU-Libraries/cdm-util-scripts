import pytest
import requests

import json

from cdm_util_scripts import catcherdiff
from cdm_util_scripts import cdm_api


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


@pytest.mark.vcr
def test_report_to_html():
    repo_url = 'https://cdmdemo.contentdm.oclc.org'
    collection_alias = 'oclcsample'
    with requests.Session() as session:
        collection_field_info = cdm_api.get_collection_field_info(
            repo_url=repo_url,
            collection_alias=collection_alias,
            session=session,
        )
    report_base = {
        'cdm_repo_url': repo_url,
        'cdm_collection_alias': collection_alias,
        'cdm_fields_info': collection_field_info,
        'vocabs_index': cdm_api.build_vocabs_index(collection_field_info),
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


@pytest.mark.vcr
def test_catcherdiff(tmpdir):
    catcher_edits = [
        {"dmrecord": "71", "format": "PDF"}
    ]
    catcher_json_file_path = tmpdir / "catcher-edits.json"
    report_file_path = tmpdir / "report.html"
    with open(catcher_json_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp)

    catcherdiff.catcherdiff(
        cdm_repo_url="https://cdmdemo.contentdm.oclc.org/",
        cdm_collection_alias="oclcsample",
        catcher_json_file_path=catcher_json_file_path,
        report_file_path=report_file_path,
        check_vocabs=True,
    )

    assert report_file_path.exists()
