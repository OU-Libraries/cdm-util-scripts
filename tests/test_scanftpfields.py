import pytest

from cdm_util_scripts import scanftpfields
from cdm_util_scripts.ftp_api import (
    FtpWork,
    FtpPage,
    FtpStructuredData,
    FtpStructuredDataField,
)


@pytest.mark.parametrize(
    "ftp_objects",
    [
        [
            scanftpfields.WorkAndFields(
                FtpWork(url="0"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpfields.WorkAndFields(
                FtpWork(url="1"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpfields.WorkAndFields(
                FtpWork(url="2"),
                FtpStructuredData(
                    data=[FtpStructuredDataField(label="B", value="", config="b")]
                ),
            ),
        ],
        [
            scanftpfields.PageAndFields(
                FtpPage(id_="0"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpfields.WorkAndFields(
                FtpPage(id_="1"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpfields.WorkAndFields(
                FtpPage(id_="2"),
                FtpStructuredData(
                    data=[FtpStructuredDataField(label="B", value="", config="b")]
                ),
            ),
        ],
    ],
)
def test_collate_field_sets(ftp_objects):
    collation = scanftpfields.collate_field_sets(ftp_objects)
    assert len(collation[frozenset(["a"])]) == 2
    assert len(collation[frozenset(["b"])]) == 1


@pytest.mark.vcr
def test_scanftpfields(tmp_path):
    report_path = tmp_path / "report.html"
    scanftpfields.scanftpfields(
        ftp_slug="ohiouniversitylibraries",
        ftp_project_name="Dance Posters Metadata",
        report_path=report_path,
    )
    assert report_path.exists()
