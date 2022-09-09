import pytest
import requests

import json

from cdm_util_scripts import ftpmdc2catcher
from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api


@pytest.fixture
def farfel_field_mapping(tmp_path):
    field_mapping_csv_path = tmp_path / "farfel-field-mapping.csv"
    cdm_api.write_csv_field_mapping(
        field_mapping_csv_path,
        {
            "Language(s) - Use Google Translate to identify the language of the leaf text: https://translate.google.com/": [
                "langua"
            ],
            "Document genre(s) - Search online for the leaf author and source title to determine the work's genre": [
                "docume"
            ],
            "Feature(s) - Identify design features present on the leaf (recto and verso)": [
                "featur"
            ],
        },
    )
    return field_mapping_csv_path


@pytest.fixture
def dance_posters_field_mapping(tmp_path):
    field_mapping_csv_path = tmp_path / "dance-posters-field-mapping.csv"
    cdm_api.write_csv_field_mapping(
        field_mapping_csv_path,
        {
            "Title": ["title"],
            "Creator (artist)": ["creatb"],
            "Creator (artist) if other": ["creatb"],
            "Creator (choreographer)": ["creata"],
            "Creator (choreographer) if other": ["creata"],
            "Creator (photographer)": ["creato"],
            "Creator (photographer) if other": ["creato"],
            "Dance company": ["dancea"],
            "Dance company if other": ["dancea"],
            "Dance title": ["dance"],
            "Dance title if other": ["dance"],
            "Language": ["langua"],
            "Date created (YYYY)": ["datea"],
            "Rights information": ["rightsc"],
            "Transcribed poster text": ["transc"],
            "Description": ["descri"],
        },
    )
    return field_mapping_csv_path


@pytest.mark.vcr
def test_umapped_fields(dance_posters_field_mapping):
    config = ftp_api.FtpStructuredDataConfig.from_json(
        requests.get("https://fromthepage.com/iiif/1073/structured/config/page").json()
    )
    field_mapping = cdm_api.read_csv_field_mapping(dance_posters_field_mapping)
    unmapped_configs = list(
        ftpmdc2catcher.unmapped_fields(config=config, field_mapping=field_mapping)
    )
    assert unmapped_configs[0].label.startswith("Title format:")
    assert unmapped_configs[1].label.startswith("Description format:")


@pytest.mark.default_cassette("farfel-leaves-metadata.yaml")
@pytest.mark.vcr
@pytest.mark.parametrize(
    "level",
    [
        ftpmdc2catcher.Level.AUTO,
        ftpmdc2catcher.Level.WORK,
    ],
)
def test_ftpmdc2catcher_farfel(tmp_path, farfel_field_mapping, level):
    ftp_slug = "ohiouniversitylibraries"
    ftp_project_name = "Farfel Leaves Metadata"
    output_file_path = tmp_path / "output.json"

    ftpmdc2catcher.ftpmdc2catcher(
        ftp_slug=ftp_slug,
        ftp_project_name=ftp_project_name,
        field_mapping_csv_path=farfel_field_mapping,
        level=level,
        output_file_path=output_file_path,
    )

    with open(output_file_path, mode="r", encoding="utf-8") as fp:
        edits = json.load(fp)
    for edit in edits:
        assert edit["dmrecord"].isdigit()
        assert set(edit).issubset({"langua", "docume", "featur", "dmrecord"})


@pytest.mark.default_cassette("dance-posters-metadata.yaml")
@pytest.mark.vcr
@pytest.mark.parametrize(
    "level",
    [
        ftpmdc2catcher.Level.AUTO,
        ftpmdc2catcher.Level.PAGE,
    ],
)
def test_ftpmdc2catcher_dance(tmp_path, dance_posters_field_mapping, level):
    ftp_slug = "ohiouniversitylibraries"
    ftp_project_name = "Dance Posters Metadata"
    output_file_path = tmp_path / "output.json"

    ftpmdc2catcher.ftpmdc2catcher(
        ftp_slug=ftp_slug,
        ftp_project_name=ftp_project_name,
        field_mapping_csv_path=dance_posters_field_mapping,
        level=ftpmdc2catcher.Level.PAGE,
        output_file_path=output_file_path,
    )

    with open(output_file_path, mode="r", encoding="utf-8") as fp:
        edits = json.load(fp)
    for edit in edits:
        assert edit["dmrecord"].isdigit()
        assert set(edit).issubset(
            {
                "dmrecord",
                "creata",
                "creatb",
                "creato",
                "dance",
                "dancea",
                "datea",
                "descri",
                "langua",
                "rightsc",
                "title",
                "transc",
            }
        )
