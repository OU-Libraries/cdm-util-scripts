import pytest
import vcr
import requests
import re

import ftpfields2catcher

ftp_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/ftpfields2catcher',
    record_mode='none'
)


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@ftp_vcr.use_cassette()
def test_get_collection_manifest_url(session):
    url = ftpfields2catcher.get_collection_manifest_url(
        slug='ohiouniversitylibraries',
        collection_name='Dance Posters Metadata',
        session=session
    )
    assert url

    with pytest.raises(KeyError):
        ftpfields2catcher.get_collection_manifest_url(
            slug='ohiouniversitylibraries',
            collection_name='Does Not Exist',
            session=session
        )


@ftp_vcr.use_cassette()
def test_get_ftp_collection(session):
    ftp_collection = ftpfields2catcher.get_ftp_collection(
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

    ftp_collection = ftpfields2catcher.get_ftp_collection(
        manifest_url='https://fromthepage.com/iiif/collection/ryan-metadata',
        session=session
    )
    assert ftp_collection.manifest_url
    assert ftp_collection.alias == 'ryan-metadata'
    assert ftp_collection.label
    for ftp_work in ftp_collection.works:
        assert ftp_work.ftp_work_label
        assert ftp_work.ftp_manifest_url


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('label, match_pattern', [
    ('TEI Export', r'<TEI xmlns="http://www\.tei-c\.org/ns/1.0"'),
    ('XHTML Export', r'<html xmlns="http://www\.w3\.org/1999/xhtml"')
])
def test_get_rendering(label, match_pattern, session):
    response = session.get('https://fromthepage.com/iiif/48258/manifest')
    ftp_manifest = response.json()
    rendering_text = ftpfields2catcher.get_rendering(
        ftp_manifest=ftp_manifest,
        label=label,
        session=session
    )
    assert re.search(match_pattern, rendering_text) is not None


@ftp_vcr.use_cassette()
def test_get_rendering_raises(session):
    response = session.get('https://fromthepage.com/iiif/48258/manifest')
    ftp_manifest = response.json()
    with pytest.raises(KeyError):
        ftpfields2catcher.get_rendering(
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


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('tei_url, html_url, check_pages', extraction_test_values)
def test_extract_fields_from_tei(tei_url, html_url, check_pages, session):
    response = session.get(tei_url)
    pages = ftpfields2catcher.extract_fields_from_tei(tei=response.text)
    for page, check_page in zip(pages, check_pages):
        for key, value in check_page.items():
            assert page[key] == value


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('tei_url, html_url, check_pages', extraction_test_values)
def test_extract_fields_from_html(tei_url, html_url, check_pages, session):
    response = session.get(html_url)
    pages = ftpfields2catcher.extract_fields_from_html(html=response.text)
    for page, check_page in zip(pages, check_pages):
        for key, value in check_page.items():
            assert page[key] == value


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('rendering_label', ftpfields2catcher.rendering_extractors.keys())
def test_load_ftp_manifest_data(rendering_label, session):
    ftp_work = ftpfields2catcher.FTPWork(
        ftp_manifest_url='https://fromthepage.com/iiif/47397/manifest'
    )
    ftpfields2catcher.load_ftp_manifest_data(ftp_work, rendering_label, session)
    assert all(isinstance(page, ftpfields2catcher.FTPPage) for page in ftp_work.pages)
    assert ftp_work.ftp_work_url


@pytest.mark.parametrize('field_mapping, result', [
    ({'label': ['nick']}, {'nick': 'value'}),
    ({'label': ['nick1', 'nick2']}, {'nick1': 'value', 'nick2': 'value'}),
    ({'blank': ['nick'], 'label': ['nick']}, {'nick': 'value'}),
    ({'label': ['nick'], 'blank': ['nick']}, {'nick': 'value'}),
    ({'blank': ['nick', 'nick']}, {'nick': ''}),
    ({'label': ['nick', 'nick']}, {'nick': 'value; value'}),
    ({'label': ['nick'], 'label2': ['nick']}, {'nick': 'value; value2'}),
    ({'label2': ['nick'], 'label': ['nick']}, {'nick': 'value2; value'}),
])
def test_apply_mapping(field_mapping, result):
    ftp_fields = {
        'label': 'value',
        'label2': 'value2',
        'blank': ''
    }
    mapped = ftpfields2catcher.apply_field_mapping(ftp_fields, field_mapping)
    assert mapped == result


@pytest.mark.parametrize('pages, check_index', [
    ([
        ftpfields2catcher.FTPPage(fields={'Label0': '', 'Label1': ''}),
        ftpfields2catcher.FTPPage(fields={'Label0': '', 'Label1': 'value1'}),
        ftpfields2catcher.FTPPage(fields={'Label0': '', 'Label1': ''}),
    ],
     1),
    ([
        ftpfields2catcher.FTPPage(fields=None),
        ftpfields2catcher.FTPPage(fields=None),
        ftpfields2catcher.FTPPage(fields={'Label0': 'value0', 'Label1': ''}),
    ],
     2),
])
def test_PagePickers_first_filled_page(pages, check_index):
    assert ftpfields2catcher.PagePickers.first_filled_page(pages) is pages[check_index]


@pytest.mark.parametrize('pages', [
    [
        ftpfields2catcher.FTPPage(fields=None),
        ftpfields2catcher.FTPPage(fields=None),
        ftpfields2catcher.FTPPage(fields=None),
    ],
    [],
    [
        ftpfields2catcher.FTPPage(fields={'Label0': '', 'Label1': ''}),
        ftpfields2catcher.FTPPage(fields={'Label0': '', 'Label1': ''}),
        ftpfields2catcher.FTPPage(fields={'Label0': '', 'Label1': ''}),
    ],
])
def test_PagePickers_first_filled_page_is_none(pages):
    assert ftpfields2catcher.PagePickers.first_filled_page(pages) is None


@pytest.mark.parametrize('ftp_work, page_picker, result', [
    (ftpfields2catcher.FTPWork(dmrecord='1', pages=[ftpfields2catcher.FTPPage(fields={'Label': 'value'})]),
     ftpfields2catcher.PagePickers.first_page,
     {'dmrecord': '1', 'nick': 'value'})
])
def test_map_ftp_work_as_cdm_object(ftp_work, page_picker, result):
    field_mapping = {
        'Label': ['nick']
    }
    page = ftpfields2catcher.map_ftp_work_as_cdm_object(
        ftp_work=ftp_work,
        field_mapping=field_mapping,
        page_picker=page_picker
    )
    assert page == result


@ftp_vcr.use_cassette()
def test_get_cdm_item_info(session):
    ftp_work = ftpfields2catcher.FTPWork(
        cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
        cdm_collection_alias='oclcsample',
        dmrecord='102'
    )
    item_info = ftpfields2catcher.get_cdm_item_info(ftp_work, session)
    assert item_info['dmrecord'] == ftp_work.dmrecord
    assert item_info['find']


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('ftp_work, dmrecords', [
    # Compound Object
    (
        ftpfields2catcher.FTPWork(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='12',
            pages=[
                ftpfields2catcher.FTPPage(fields={'Label': 'value1'}),
                ftpfields2catcher.FTPPage(fields={'Label': 'value2'}),
            ]
        ),
        ['10', '11']
    ),

    # Single Item
    (
        ftpfields2catcher.FTPWork(
            cdm_repo_url='https://cdmdemo.contentdm.oclc.org',
            cdm_collection_alias='oclcsample',
            dmrecord='64',
            pages=[
                ftpfields2catcher.FTPPage(fields={'Label': 'value1'}),
            ]
        ),
        ['64']
    )
])
def test_map_ftp_work_as_cdm_pages(ftp_work, dmrecords, session):
    field_mapping = {
        'Label': ['nick']
    }

    pages_data = ftpfields2catcher.map_ftp_work_as_cdm_pages(
        ftp_work=ftp_work,
        field_mapping=field_mapping,
        session=session
    )

    for dmrecord, page, page_data in zip(dmrecords, ftp_work.pages, pages_data):
        assert page_data == {
            'dmrecord': dmrecord,
            **ftpfields2catcher.apply_field_mapping(page.fields, field_mapping)
        }
