import pytest

import csv
import json

from cdm_util_scripts import ftpmdc2catcher


@pytest.mark.vcr
def test_ftpmdc2catcher(tmpdir):
    ftp_slug = "ohiouniversitylibraries"
    ftp_project_name = "Farfel Leaves Metadata"
    field_mapping_csv_path = tmpdir / "field-mapping.csv"
    with open(field_mapping_csv_path, mode="w", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["name", "nick"])
        writer.writeheader()
        writer.writerows(
            [
                {
                    "name": "Language(s) - Use Google Translate to identify the language of the leaf text: https://translate.google.com/",
                    "nick": "langua",
                },
                {
                    "name": "Document genre(s) - Search online for the leaf author and source title to determine the work's genre",
                    "nick": "docume",
                },
                {
                    "name": "Feature(s) - Identify design features present on the leaf (recto and verso)",
                    "nick": "featur",
                },
            ]
        )
    output_file_path = tmpdir / "output.json"

    ftpmdc2catcher.ftpmdc2catcher(
        ftp_slug=ftp_slug,
        ftp_project_name=ftp_project_name,
        field_mapping_csv_path=field_mapping_csv_path,
        output_file_path=output_file_path,
    )

    with open(output_file_path, mode="r", encoding="utf-8") as fp:
        edits = json.load(fp)
    for edit in edits:
        assert edit["dmrecord"].isdigit()
        assert set(edit).issubset(["langua", "docume", "featur", "dmrecord"])
