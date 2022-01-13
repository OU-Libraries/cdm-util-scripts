import re

import pytest
import vcr
import requests

from cdm_util_scripts import ftp_api


ftp_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/ftp_api',
    record_mode='once',
)


@pytest.fixture
@ftp_vcr.use_cassette()
def ftp_manifest(session):
    return ftp_api.get_ftp_manifest('https://fromthepage.com/iiif/25000250/manifest', session)


@ftp_vcr.use_cassette()
def test_get_ftp_manifest(session):
    assert ftp_api.get_ftp_manifest('https://fromthepage.com/iiif/25000250/manifest', session)


@ftp_vcr.use_cassette()
def test_get_ftp_transcript(session):
    assert ftp_api.get_ftp_transcript('https://fromthepage.com/iiif/25000250/export/25012395/plaintext/verbatim', session).startswith("29th Divisio")


def test_get_ftp_manifest_transcript_urls(ftp_manifest):
    assert ftp_api.get_ftp_manifest_transcript_urls(
        ftp_manifest,
        label='Verbatim Plaintext'
    )


@ftp_vcr.use_cassette()
def test_get_collection_manifest_url(session):
    url = ftp_api.get_collection_manifest_url(
        slug='ohiouniversitylibraries',
        collection_name='Dance Posters Metadata',
        session=session
    )
    assert url

    with pytest.raises(KeyError):
        ftp_api.get_collection_manifest_url(
            slug='ohiouniversitylibraries',
            collection_name='Does Not Exist',
            session=session
        )


@ftp_vcr.use_cassette()
def test_get_ftp_collection(session):
    ftp_collection = ftp_api.get_ftp_collection(
        manifest_url='https://fromthepage.com/iiif/collection/dance-posters-metadata',
        session=session
    )
    assert ftp_collection.manifest_url
    assert ftp_collection.alias == 'dance-posters-metadata'
    assert ftp_collection.label
    for ftp_work in ftp_collection.works:
        assert ftp_work.dmrecord.isdigit()
        assert ftp_work.cdm_collection_alias
        assert ftp_work.cdm_repo_url
        assert ftp_work.cdm_source_url
        assert ftp_work.ftp_work_label
        assert ftp_work.ftp_manifest_url

    ftp_collection = ftp_api.get_ftp_collection(
        manifest_url='https://fromthepage.com/iiif/collection/ryan-metadata',
        session=session
    )
    assert ftp_collection.manifest_url
    assert ftp_collection.alias == 'ryan-metadata'
    assert ftp_collection.label
    for ftp_work in ftp_collection.works:
        assert ftp_work.ftp_work_label
        assert ftp_work.ftp_manifest_url


@ftp_vcr.use_cassette(record_mode="new_episodes")
@pytest.mark.parametrize('label, match_pattern', [
    ('TEI Export', r'<TEI xmlns="http://www\.tei-c\.org/ns/1.0"'),
    ('XHTML Export', r'<html xmlns="http://www\.w3\.org/1999/xhtml"')
])
def test_get_rendering(label, match_pattern, session):
    response = session.get('https://fromthepage.com/iiif/25000250/manifest')
    ftp_manifest = response.json()
    rendering_text = ftp_api.get_rendering(
        ftp_manifest=ftp_manifest,
        label=label,
        session=session
    )
    assert re.search(match_pattern, rendering_text) is not None


@ftp_vcr.use_cassette()
def test_get_rendering_raises(session):
    response = session.get('https://fromthepage.com/iiif/25000250/manifest')
    ftp_manifest = response.json()
    with pytest.raises(KeyError):
        ftp_api.get_rendering(
            ftp_manifest=ftp_manifest,
            label='Does Not Exist',
            session=None
        )


extraction_test_values = [
    # https://fromthepage.com/iiif/48254/manifest
    ('https://fromthepage.com/iiif/an-evening-of-dance-florida-state-university-poster-february-22-24/export/tei',
     'https://fromthepage.com/iiif/an-evening-of-dance-florida-state-university-poster-february-22-24/export/html',
     [
         {
             'Title':  'An Evening of Dance, Florida State University poster, February 22-24',
             'Creator (artist)': '',
             # Whitespace required at the end of "Davis, ", "Fichter, ", and "Sias and "
             'Transcribed poster text': """
FSU Department of Dance
An Evening of Dance
February 22-24
February 22 & 23 8:00 pm
February 24 2:30 pm
RUBY DIAMOND AUDITORIUM
Works by:
Gwynne Ashton, Lynda Davis, 
Nancy Smith Fichter, 
Richard Sias and 
Alwin Nikolais

FSU Fine Arts,
Union Box Offices
and at the door
Ticket
Reservations:
644-6500 &
644-6277
             """.strip()
         }
     ]),

    # https://fromthepage.com/iiif/46453/manifest
    ('https://fromthepage.com/iiif/ryan-box023-tld-f41-31956cd7-4e66-4f1d-b830-40b33d8dc77d/export/tei',
     'https://fromthepage.com/iiif/ryan-box023-tld-f41-31956cd7-4e66-4f1d-b830-40b33d8dc77d/export/html',
     [
         {
             'Title': 'Box 023, folder 41: Background notes, 1st Parachute Battalion',
             'Respondent unit (examples include battalions, brigades, regiments, and squadrons)': '1st Parachute Battalion',
         },
         {
             'Respondent name (last, first middle)': '',
             'Respondent nationality': '',
         }
     ])
]


@ftp_vcr.use_cassette(record_mode="new_episodes")
@pytest.mark.parametrize('tei_url, html_url, check_pages', extraction_test_values)
def test_extract_fields_from_tei(tei_url, html_url, check_pages, session):
    response = session.get(tei_url)
    pages = ftp_api.extract_fields_from_tei(tei=response.text)
    for page, check_page in zip(pages, check_pages):
        for key, value in check_page.items():
            assert page[key] == value


@ftp_vcr.use_cassette(record_mode="new_episodes")
@pytest.mark.parametrize('tei_url, html_url, check_pages', extraction_test_values)
def test_extract_fields_from_html(tei_url, html_url, check_pages, session):
    response = session.get(html_url)
    pages = ftp_api.extract_fields_from_html(html=response.text)
    for page, check_page in zip(pages, check_pages):
        for key, value in check_page.items():
            assert page[key] == value


@ftp_vcr.use_cassette(record_mode="new_episodes")
@pytest.mark.parametrize('rendering_label', ftp_api.rendering_extractors.keys())
def test_load_ftp_manifest_data(rendering_label, session):
    ftp_work = ftp_api.FTPWork(
        ftp_manifest_url='https://fromthepage.com/iiif/47397/manifest'
    )
    ftp_api.load_ftp_manifest_data(ftp_work, rendering_label, session)
    assert all(isinstance(page, ftp_api.FTPPage) for page in ftp_work.pages)
    assert ftp_work.ftp_work_url
