import pytest

from cdm_util_scripts import scanftpfields
from cdm_util_scripts import ftp_api2 as ftp_api


@pytest.fixture
def field_transcriptions():
    return iter(
        [
            [
                {"A": "a"},
                None,
                {"B": "b"},
            ],
            [
                {"A": "a"},
                None,
                None,
            ],
        ]
    )


def test_count_filled_pages(field_transcriptions):
    assert scanftpfields.count_filled_pages(field_transcriptions) == 3


def test_compile_field_frequencies(field_transcriptions):
    assert scanftpfields.compile_field_frequencies(field_transcriptions) == {
        "A": 2,
        "B": 1,
    }


def test_collate_ftp_fields_by_schema(field_transcriptions):
    test_works = [
        ftp_api.FtpWork(
            "0",
            pages=[ftp_api.FtpPage("0"), ftp_api.FtpPage("1"), ftp_api.FtpPage("2")],
        ),
        ftp_api.FtpWork(
            "1",
            pages=[ftp_api.FtpPage("0"), ftp_api.FtpPage("1"), ftp_api.FtpPage("2")],
        ),
    ]
    assert scanftpfields.collate_ftp_pages_by_schema(zip(test_works, field_transcriptions)) == {
        frozenset(["A"]): [
            (test_works[0].pages[0], test_works[0]),
            (test_works[1].pages[0], test_works[1]),
        ],
        frozenset(["B"]): [(test_works[0].pages[2], test_works[0])],
        None: [
            (test_works[0].pages[1], test_works[0]),
            (test_works[1].pages[1], test_works[1]),
            (test_works[1].pages[2], test_works[1]),
        ],
    }


@pytest.mark.vcr
def test_scanftpfields(tmp_path):
    scanftpfields.scanftpfields(
        ftp_slug="ohiouniversitylibraries",
        ftp_project_name="Dance Posters Metadata",
        report_parent_path=tmp_path,
    )
    assert tmp_path.glob("field-label-report*.html")
