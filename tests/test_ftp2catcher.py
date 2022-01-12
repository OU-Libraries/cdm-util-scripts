import pytest
import vcr
import requests

from cdm_util_scripts import ftp2catcher


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/ftp2catcher',
    record_mode='none'
)


@pytest.fixture(scope='module')
def session():
    with requests.Session() as session:
        yield session


@pytest.fixture
def ftp_manifest(session):
    with cdm_vcr.use_cassette('ftp_manifest.yml'):
        return ftp2catcher.get_ftp_manifest('https://fromthepage.com/iiif/36875/manifest', session)


def test_find_cdm_objects(session):
    with cdm_vcr.use_cassette('test_find_cdm_objects.yml'):
        assert ftp2catcher.find_cdm_objects(
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            field_nick='identi',
            value='ryan_box058-tlb_f26',
            session=session
        )


def test_get_ftp_manifest(session):
    with cdm_vcr.use_cassette('test_get_ftp_manifest.yml'):
        assert ftp2catcher.get_ftp_manifest('https://fromthepage.com/iiif/36875/manifest', session)


def test_get_ftp_manifest_transcript_urls(ftp_manifest):
    assert ftp2catcher.get_ftp_manifest_transcript_urls(ftp_manifest,
                                                        label='Verbatim Plaintext')


def test_get_ftp_transcript(session):
    with cdm_vcr.use_cassette('test_get_ftp_transcript.yml'):
        assert ftp2catcher.get_ftp_transcript('https://fromthepage.com/iiif/36875/export/1229042/plaintext/verbatim', session)
