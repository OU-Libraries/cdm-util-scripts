import pytest

import collections
import xml.etree.ElementTree as ET
import html

from cdm_util_scripts import scanftpschema
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
            scanftpschema.WorkAndFields(
                FtpWork(url="0"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpschema.WorkAndFields(
                FtpWork(url="1"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpschema.WorkAndFields(
                FtpWork(url="2"),
                FtpStructuredData(
                    data=[FtpStructuredDataField(label="B", value="", config="b")]
                ),
            ),
        ],
        [
            scanftpschema.PageAndFields(
                FtpPage(id_="0"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpschema.WorkAndFields(
                FtpPage(id_="1"),
                FtpStructuredData(
                    data=[
                        FtpStructuredDataField(label="A", value="", config="a"),
                    ]
                ),
            ),
            scanftpschema.WorkAndFields(
                FtpPage(id_="2"),
                FtpStructuredData(
                    data=[FtpStructuredDataField(label="B", value="", config="b")]
                ),
            ),
        ],
    ],
)
def test_collate_field_sets(ftp_objects):
    collation = scanftpschema.collate_field_sets(ftp_objects)
    assert len(collation[frozenset(["a"])]) == 2
    assert len(collation[frozenset(["b"])]) == 1


@pytest.mark.vcr
def test_scanftpschema(tmp_path):
    report_path = tmp_path / "report.html"
    scanftpschema.scanftpschema(
        ftp_slug="ohiouniversitylibraries",
        ftp_project_name="Farfel Leaves Metadata",
        report_path=report_path,
    )

    report = ET.parse(report_path)
    work_config = report.find(".//table[@class='work-config']")
    field_counts = {
        html.unescape(tr[0].find("span").text): int(tr[3].text) for tr in work_config.findall("./tbody/tr")
    }
    field_sets = report.findall(".//div[@class='field-set']")
    field_set_counts = collections.Counter()
    for field_set in field_sets:
        occurences = int(field_set.find("h3").text.partition(" ")[0])
        field_set_count = {}
        for li in field_set.findall("./ol/li"):
            included, label = li.findall("span")
            if included.text == "+":
                field_set_count[html.unescape(label.text)] = occurences
        field_set_counts.update(field_set_count)
    assert dict(field_set_counts) == field_counts == {
        "Document genre(s) - Search online for the leaf author and source title to determine the work's genre": 59,
        "Language(s) - Use Google Translate to identify the language of the leaf text: https://translate.google.com/": 59,
        "Feature(s) - Identify design features present on the leaf (recto and verso)": 55,
    }
