import requests
import vcr
import pytest

from cdm_util_scripts import ftptr2catcher


ftp_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes/ftptr2catcher",
    record_mode="none",
)


@pytest.fixture(scope='module')
def session():
    with requests.Session() as session:
        yield session


@pytest.fixture
def ftp_manifest(session):
    with ftp_vcr.use_cassette('ftp_manifest.yml'):
        return ftptr2catcher.get_ftp_manifest("https://fromthepage.com/iiif/45345/manifest", session)


def test_iter_manifest_sequence(ftp_manifest):
    for dmrecord, url in ftptr2catcher.iter_manifest_sequence(ftp_manifest, transcript_type="Verbatim Plaintext"):
        assert int(dmrecord)
        assert url.startswith("https://")


def test_get_manifest_catcher_edits(ftp_manifest, session):
    transcript_nick = "transc"
    with ftp_vcr.use_cassette("test_get_manifest_catcher_edits.yml"):
        catcher_edits = ftptr2catcher.get_manifest_catcher_edits(ftp_manifest, transcript_nick=transcript_nick, transcript_type="Verbatim Plaintext", session=session)
        for edit in catcher_edits:
            assert set(edit) == {"dmrecord", transcript_nick}
            assert int(edit["dmrecord"])


def test_get_manifests_catcher_edits(session):
    transcript_nick = "transc"
    transcript_type = "Verbatim Plaintext"
    with ftp_vcr.use_cassette("test_get_manifests_catcher_edits.yml"):
        catcher_edits = ftptr2catcher.get_manifests_catcher_edits(
            [
                "https://fromthepage.com/iiif/45345/manifest",
                "https://fromthepage.com/iiif/45346/manifest",
            ],
            transcript_type=transcript_type,
            transcript_nick=transcript_nick,
            session=session
        )
        for edit in catcher_edits:
            assert set(edit) == {"dmrecord", transcript_nick}
            assert int(edit["dmrecord"])
