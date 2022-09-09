import pytest

from cdm_util_scripts import scanftpvocabs
from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api


def test_scan_vocabs():
    cdm_field_mapping = {
        "FtP TGM label": ["subjec"],
        "FtP vocab label": ["subjed"],
    }
    cdm_field_infos = [
        cdm_api.CdmFieldInfo(
            name="Subject-LCTGM",
            nick="subjec",
            type="TEXT",
            size=0,
            find="a5",
            req=0,
            search=1,
            hide=0,
            vocdb="LCTGM",
            vocab=1,
            dc="subjec",
            admin=0,
            readonly=0,
        ),
        cdm_api.CdmFieldInfo(
            name="Subject-custom",
            nick="subjed",
            type="TEXT",
            size=0,
            find="a6",
            req=0,
            search=1,
            hide=0,
            vocdb="",
            vocab=1,
            dc="subjec",
            admin=0,
            readonly=0,
        ),
    ]
    cdm_vocabs = {
        cdm_api.CdmVocabInfo(cdm_api.CdmVocabType.builtin, "LCTGM"): frozenset(
            ["Paddleboats"]
        ),
        cdm_api.CdmVocabInfo(cdm_api.CdmVocabType.custom, "subjed"): frozenset(
            ["controlled-term"]
        ),
    }
    ftp_project = ftp_api.FtpProject(
        url="test-url",
        label="Test label",
        works=[ftp_api.FtpWork(url="test-url", pages=[ftp_api.FtpPage(id_="test-id")])],
    )
    ftp_transcriptions = [
        [
            {
                "FtP TGM label": "Paddleboats; NotInTGM",
                "FtP vocab label": "controlled-term; uncontrolled-term",
            }
        ],
    ]
    uncontrolled_terms_by_field_nick, _, _, _ = scanftpvocabs.scan_vocabs(
        cdm_field_mapping=cdm_field_mapping,
        cdm_field_infos=cdm_field_infos,
        cdm_vocabs=cdm_vocabs,
        ftp_project=ftp_project,
        ftp_transcriptions=ftp_transcriptions,
    )
    assert uncontrolled_terms_by_field_nick == {
        "subjec": {"NotInTGM": [ftp_project.works[0].pages[0]]},
        "subjed": {"uncontrolled-term": [ftp_project.works[0].pages[0]]},
    }


@pytest.mark.vcr
def test_scanftpvocabs(tmp_path):
    ftp_slug = "ohiouniversitylibraries"
    ftp_project_name = "Dance Posters Metadata"
    cdm_instance_url = "https://media.library.ohio.edu/"
    cdm_collection_alias = "p15808coll16"
    field_mapping_csv_path = tmp_path / "field-mapping.csv"
    field_mapping_csv_path.write_text(
        data="""name,nick
Creator (choreographer),creata
""",
        encoding="utf-8",
    )
    report_path = tmp_path / "report.html"
    scanftpvocabs.scanftpvocabs(
        ftp_slug=ftp_slug,
        ftp_project_name=ftp_project_name,
        cdm_instance_url=cdm_instance_url,
        cdm_collection_alias=cdm_collection_alias,
        field_mapping_csv_path=field_mapping_csv_path,
        report_path=report_path,
    )
    assert report_path.exists()
