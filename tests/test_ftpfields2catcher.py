import pytest
import requests

import csv
import json

from cdm_util_scripts import ftpfields2catcher
from cdm_util_scripts import ftp_api


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
    mapped = ftpfields2catcher.apply_field_mapping(ftp_fields, field_mapping)
    assert mapped == result


@pytest.mark.parametrize('pages, check_index', [
    ([
        ftp_api.FTPPage(fields={'Label0': '', 'Label1': ''}),
        ftp_api.FTPPage(fields={'Label0': '', 'Label1': 'value1'}),
        ftp_api.FTPPage(fields={'Label0': '', 'Label1': ''}),
    ],
     1),
    ([
        ftp_api.FTPPage(fields=None),
        ftp_api.FTPPage(fields=None),
        ftp_api.FTPPage(fields={'Label0': 'value0', 'Label1': ''}),
    ],
     2),
])
def test_PagePickers_first_filled_page(pages, check_index):
    assert ftpfields2catcher.PagePickers.first_filled_page(pages) is pages[check_index]


@pytest.mark.parametrize('pages', [
    [
        ftp_api.FTPPage(fields=None),
        ftp_api.FTPPage(fields=None),
        ftp_api.FTPPage(fields=None),
    ],
    [],
    [
        ftp_api.FTPPage(fields={'Label0': '', 'Label1': ''}),
        ftp_api.FTPPage(fields={'Label0': '', 'Label1': ''}),
        ftp_api.FTPPage(fields={'Label0': '', 'Label1': ''}),
    ],
])
def test_PagePickers_first_filled_page_is_none(pages):
    assert ftpfields2catcher.PagePickers.first_filled_page(pages) is None


@pytest.mark.parametrize('ftp_work, page_picker, result', [
    (ftp_api.FTPWork(dmrecord='1', pages=[ftp_api.FTPPage(fields={'Label': 'value'})]),
     ftpfields2catcher.PagePickers.first_page,
     {'dmrecord': '1', 'nick': 'value'})
])
def test_map_ftp_work_as_cdm_object(ftp_work, page_picker, result):
    field_mapping = {
        'Label': ['nick']
    }
    page = ftpfields2catcher.map_ftp_work_as_cdm_object(
        ftp_work=ftp_work,
        field_mapping=field_mapping,
        page_picker=page_picker
    )
    assert page == result


@pytest.mark.vcr
def test_get_ftp_work_cdm_item_info():
    ftp_work = ftp_api.FTPWork(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        dmrecord='102'
    )
    item_info = ftpfields2catcher.get_ftp_work_cdm_item_info(ftp_work, session=requests)
    assert item_info['dmrecord'] == ftp_work.dmrecord
    assert item_info['find']


@pytest.mark.default_cassette("test_map_ftp_work_as_cdm_pages.yaml")
@pytest.mark.vcr
@pytest.mark.parametrize('ftp_work, dmrecords', [
    # Compound Object
    (
        ftp_api.FTPWork(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='12',
            pages=[
                ftp_api.FTPPage(fields={'Label': 'value1'}),
                ftp_api.FTPPage(fields={'Label': 'value2'}),
            ]
        ),
        ['10', '11']
    ),

    # Single Item
    (
        ftp_api.FTPWork(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='64',
            pages=[
                ftp_api.FTPPage(fields={'Label': 'value1'}),
            ]
        ),
        ['64']
    )
])
def test_map_ftp_work_as_cdm_pages(ftp_work, dmrecords):
    field_mapping = {
        'Label': ['nick']
    }

    pages_data = ftpfields2catcher.map_ftp_work_as_cdm_pages(
        ftp_work=ftp_work,
        field_mapping=field_mapping,
        session=requests,
    )

    for dmrecord, page, page_data in zip(dmrecords, ftp_work.pages, pages_data):
        assert page_data == {
            'dmrecord': dmrecord,
            **ftpfields2catcher.apply_field_mapping(page.fields, field_mapping)
        }


@pytest.mark.vcr
def test_ftpfields2catcher(tmpdir):
    match_mode = ftpfields2catcher.MatchModes.by_object
    ftp_slug = "ohiouniversitylibraries"
    ftp_project_name = "Dance Posters Metadata"
    field_mapping_csv_path = tmpdir / "field-mapping.csv"
    field_mapping_csv_rows = [
        {"name": "Title", "nick": "title"},
    ]
    with open(field_mapping_csv_path, mode="w", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["name", "nick"])
        writer.writeheader()
        writer.writerows(field_mapping_csv_rows)
    output_file_path = tmpdir / "output.json"

    ftpfields2catcher.ftpfields2catcher(
        match_mode=match_mode,
        ftp_slug=ftp_slug,
        ftp_project_name=ftp_project_name,
        field_mapping_csv_path=field_mapping_csv_path,
        output_file_path=output_file_path,
    )

    with open(output_file_path, mode="r", encoding="utf-8") as fp:
        result = json.load(fp)

    for edit in result:
        assert edit["dmrecord"].isdigit()
        assert "title" in edit
