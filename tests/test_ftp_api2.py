import pytest
import requests

from cdm_util_scripts import ftp_api2 as ftp_api


SPECIMEN_FTP_MANIFEST_URL = "https://fromthepage.com/iiif/56198/manifest"


@pytest.fixture
def ftp_manifest():
    with requests.Session() as session:
        response = session.get(SPECIMEN_FTP_MANIFEST_URL)
    response.raise_for_status()
    return ftp_api.FTPManifest.from_json(response.json())


@pytest.mark.default_cassette("dance_posters_metadata.yaml")
@pytest.mark.vcr
def test_FTPInstance_request_collections():
    instance = ftp_api.FTPInstance(base_url="https://fromthepage.com/")
    with requests.Session() as session:
        collections = instance.request_collections(slug="ohiouniversitylibraries", session=session)
    for label, url in collections.collections.items():
        assert label
        assert url.startswith("http")


@pytest.mark.default_cassette("dance_posters_metadata.yaml")
@pytest.mark.vcr
def test_FTPCollectionOfCollections_request_collection():
    instance = ftp_api.FTPInstance(base_url="https://fromthepage.com/")
    with requests.Session() as session:
        collections = instance.request_collections(slug="ohiouniversitylibraries", session=session)
        collection = collections.request_collection(label="Dance Posters Metadata", session=session)
    assert collection.collection_id == "dance-posters-metadata"
    for manifest in collection.manifests:
        assert manifest.url
        assert manifest.label
        assert manifest.cdm_collection_alias == "p15808coll16"
        assert manifest.cdm_object_dmrecord.isdigit()


@pytest.mark.default_cassette("dance_posters_metadata.yaml")
@pytest.mark.vcr
def test_FTPCollection_requests_manifests():
    instance = ftp_api.FTPInstance(base_url="https://fromthepage.com/")
    with requests.Session() as session:
        collections = instance.request_collections(slug="ohiouniversitylibraries", session=session)
        collection = collections.request_collection(label="Dance Posters Metadata", session=session)
        collection.request_manifests(session=session)
    for manifest in collection.manifests:
        assert manifest.metadata
        assert manifest.renderings
        assert manifest.pages
        assert manifest.cdm_collection_alias
        assert manifest.cdm_object_dmrecord


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FTPManifest_request():
    manifest = ftp_api.FTPManifest(url=SPECIMEN_FTP_MANIFEST_URL, label="Test label")
    with requests.Session() as session:
        manifest.request(session=session)
    assert manifest.label == manifest.metadata["Title"]
    assert {rendering.label for rendering in manifest.renderings} == {"Verbatim Plaintext", "Emended Plaintext", "Searchable Plaintext", "XHTML Export", "TEI Export"}
    for page in manifest.pages:
        assert page.id_
        assert page.label
        assert page.renderings
        assert page.cdm_collection_alias
        assert page.cdm_page_dmrecord


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FTPManifest_request_rendering(ftp_manifest):
    with requests.Session() as session:
        plaintext = ftp_manifest.request_rendering(label="Verbatim Plaintext", session=session)
    assert plaintext.startswith("Title: ")


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_FTPManifest_request_xhtml_tei_transcript_fields(ftp_manifest):
    with requests.Session() as session:
        xhtml_fields = ftp_manifest.request_xhtml_transcript_fields(session=session)
        tei_fields = ftp_manifest.request_tei_transcript_fields(session=session)
    assert xhtml_fields == tei_fields
    assert len(xhtml_fields) == 1
    xhtml_page = xhtml_fields[0]
    assert xhtml_page["Title"] == "Nothing else like it in the world poster, Nikolais Dance Theatre"
    assert xhtml_page["Creator (artist)"] == "Warner-Lasser Associates"
    assert xhtml_page["Creator (artist) if other"] == ""


@pytest.mark.vcr
def test_FTPManifest_request_structured_data():
    with requests.Session() as session:
        manifest = ftp_api.FTPManifest(url="https://fromthepage.com/iiif/32024760/manifest", label="Test label")
        manifest.request(session=session)
        structured_data = manifest.request_structured_data(session=session)
    assert structured_data.contributors
    for field_data in structured_data.data:
        assert field_data.label
        assert isinstance(field_data.value, (list, str))
        assert field_data.config.startswith("http")
