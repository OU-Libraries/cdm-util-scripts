import pytest
import requests

from cdm_util_scripts import ftp_api2 as ftp_api


SPECIMEN_FTP_MANIFEST_URL = "https://fromthepage.com/iiif/56198/manifest"


@pytest.fixture
def ftp_work():
    with requests.Session() as session:
        response = session.get(SPECIMEN_FTP_MANIFEST_URL)
    response.raise_for_status()
    return ftp_api.FtpWork.from_json(response.json())


@pytest.mark.default_cassette("dance_posters_metadata.yaml")
@pytest.mark.vcr
def test_FtpInstance_request_projects():
    instance = ftp_api.FtpInstance(base_url="https://fromthepage.com/")
    with requests.Session() as session:
        projects = instance.request_projects(slug="ohiouniversitylibraries", session=session)
    for label, url in projects.projects.items():
        assert label
        assert url.startswith("http")


@pytest.mark.default_cassette("dance_posters_metadata.yaml")
@pytest.mark.vcr
def test_FtpProjectCollection_request_project():
    instance = ftp_api.FtpInstance(base_url="https://fromthepage.com/")
    with requests.Session() as session:
        projects = instance.request_projects(slug="ohiouniversitylibraries", session=session)
        project = projects.request_project(label="Dance Posters Metadata", session=session)
    assert project.project_id == "dance-posters-metadata"
    for work in project.works:
        assert work.url
        assert work.label
        assert work.cdm_collection_alias == "p15808coll16"
        assert work.cdm_object_dmrecord.isdigit()


@pytest.mark.default_cassette("dance_posters_metadata.yaml")
@pytest.mark.vcr
def test_FtpProject_requests_works():
    instance = ftp_api.FtpInstance(base_url="https://fromthepage.com/")
    with requests.Session() as session:
        projects = instance.request_projects(slug="ohiouniversitylibraries", session=session)
        project = projects.request_project(label="Dance Posters Metadata", session=session)
        project.request_works(session=session)
    for work in project.works:
        assert work.metadata
        assert work.renderings
        assert work.pages
        assert work.cdm_instance_base_url
        assert work.cdm_collection_alias
        assert work.cdm_object_dmrecord


@pytest.mark.vcr
def test_FtpProject_request_structured_data_configs():
    project = ftp_api.FtpProject(
        url="https://fromthepage.com/iiif/collection/dance-posters-metadata",
        label="Dance Posters Metadata",
    )
    with requests.Session() as session:
        work_config = project.request_work_structured_data_config(session=session)
        page_config = project.request_page_structured_data_config(session=session)
    assert work_config
    assert page_config


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FtpWork_request():
    work = ftp_api.FtpWork(url=SPECIMEN_FTP_MANIFEST_URL, label="Test label")
    with requests.Session() as session:
        work.request(session=session)
    assert work.label == work.metadata["Title"]
    assert {rendering.label for rendering in work.renderings} == {"Verbatim Plaintext", "Emended Plaintext", "Searchable Plaintext", "XHTML Export", "TEI Export"}
    for page in work.pages:
        assert page.id_
        assert page.label
        assert page.renderings
        assert page.cdm_instance_base_url
        assert page.cdm_collection_alias
        assert page.cdm_page_dmrecord


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FtpWork_request_rendering(ftp_work):
    with requests.Session() as session:
        plaintext = ftp_work.request_rendering(label="Verbatim Plaintext", session=session)
    assert plaintext.startswith("Title: ")


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FtpWork_request_xhtml_tei_transcript_fields(ftp_work):
    with requests.Session() as session:
        xhtml_fields = ftp_work.request_xhtml_transcript_fields(session=session)
        tei_fields = ftp_work.request_tei_transcript_fields(session=session)
    assert xhtml_fields == tei_fields
    assert len(xhtml_fields) == 1
    xhtml_page = xhtml_fields[0]
    assert xhtml_page["Title"] == "Nothing else like it in the world poster, Nikolais Dance Theatre"
    assert xhtml_page["Creator (artist)"] == "Warner-Lasser Associates"
    assert xhtml_page["Creator (artist) if other"] == ""


@pytest.mark.vcr
def test_FtpWork_request_structured_data():
    with requests.Session() as session:
        work = ftp_api.FtpWork(url="https://fromthepage.com/iiif/32024760/manifest", label="Test label")
        work.request(session=session)
        structured_data = work.request_structured_data(session=session)
    assert structured_data.contributors
    for field_data in structured_data.data:
        assert field_data.label
        assert isinstance(field_data.value, (list, str))
        assert field_data.config.startswith("http")


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FtpPage_request_transcript(ftp_work):
    with requests.Session() as session:
        transcript = ftp_work.pages[0].request_transcript(label="Verbatim Plaintext", session=session)
    assert transcript.startswith("Title: ")


@pytest.mark.parametrize("url,base_url,alias,dmrecord", [
    ("https://cdm15808.contentdm.oclc.org/iiif/mss:188/canvas/c1", "https://cdm15808.contentdm.oclc.org", "mss", "188"),
    ("https://cdm15808.contentdm.oclc.org/digital/iiif/p15808coll19/1959/canvas/c0", "https://cdm15808.contentdm.oclc.org", "p15808coll19", "1959"),
])
def test_parse_ftp_canvas_id(url, base_url, alias, dmrecord):
    assert ftp_api.parse_ftp_canvas_id(url) == (base_url, alias, dmrecord)
