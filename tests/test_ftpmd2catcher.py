import pytest
import vcr
import requests

import ftpmd2catcher

ftp_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/ftpmd2catcher',
    record_mode='new_episodes'
)


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@ftp_vcr.use_cassette()
def test_get_collection_manifest_url(session):
    url = ftpmd2catcher.get_collection_manifest_url(
        slug='ohiouniversitylibraries',
        collection_name='Dance Posters Metadata',
        session=session
    )
    assert url

    with pytest.raises(KeyError):
        ftpmd2catcher.get_collection_manifest_url(
            slug='ohiouniversitylibraries',
            collection_name='Does Not Exist',
            session=session
        )


@ftp_vcr.use_cassette()
def test_get_ftp_collection(session):
    ftp_collection = ftpmd2catcher.get_ftp_collection(
        url='https://fromthepage.com/iiif/collection/1073',
        session=session
    )
    for cdm_object in ftp_collection:
        assert cdm_object.dmrecord.isdigit()
        assert cdm_object.collection_alias
        assert cdm_object.cdm_source_url
        assert cdm_object.ftp_manifest_url


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('url, check_fields',
[
    ('https://fromthepage.com/export/tei?work_id=48254',
     [
         {
             'Title':  'An Evening of Dance, Florida State University poster, February 22-24',
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
     ]
    ),
    ('https://fromthepage.com/export/tei?work_id=46453',
     [
         {
             'Title': 'Box 023, folder 41: Background notes, 1st Parachute Battalion',
             'Respondent formation (examples include divisions and corps)': '6th Airborne Division'
         },
         {
             'Respondent name (last, first middle)': '',
             'Respondent nationality': ''
         }
     ])
])
def test_extract_fields_from_TEI(url, check_fields, session):
    response = session.get(url)
    pages = ftpmd2catcher.extract_fields_from_TEI(tei=response.text)
    for page, check_field in zip(pages, check_fields):
        for key, value in check_field.items():
            assert page[key] == value
