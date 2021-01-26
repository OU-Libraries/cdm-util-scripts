import pytest
import vcr
import requests
import re

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
        assert cdm_object.repo_url
        assert cdm_object.cdm_source_url
        assert cdm_object.ftp_manifest_url


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('label, match_pattern', [
    ('TEI Export', r'https://fromthepage\.com/iiif/[^/]*/export/tei'),
    ('XHTML Export', r'https://fromthepage\.com/iiif/[^/]*/export/html')
])
def test_get_rendering(label, match_pattern, session):
    response = session.get('https://fromthepage.com/iiif/48258/manifest')
    ftp_manifest = response.json()
    rendering = ftpmd2catcher.get_rendering(
        ftp_manifest=ftp_manifest,
        label=label
    )
    assert re.fullmatch(match_pattern, rendering['@id']) is not None


@ftp_vcr.use_cassette()
def test_get_rendering_raises(session):
    response = session.get('https://fromthepage.com/iiif/48258/manifest')
    ftp_manifest = response.json()
    with pytest.raises(KeyError):
        ftpmd2catcher.get_rendering(
            ftp_manifest=ftp_manifest,
            label='Does Not Exist'
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
             'Respondent formation (examples include divisions and corps)': '6th Airborne Division'
         },
         {
             'Respondent name (last, first middle)': '',
             'Respondent nationality': ''
         }
     ])
]


@pytest.mark.skip(reason="TEI endpoint returning status 500")
@ftp_vcr.use_cassette()
@pytest.mark.parametrize('tei_url, html_url, check_pages', extraction_test_values)
def test_extract_fields_from_tei(tei_url, html_url, check_pages, session):
    response = session.get(tei_url)
    pages = ftpmd2catcher.extract_fields_from_tei(tei=response.text)
    for page, check_page in zip(pages, check_pages):
        for key, value in check_page.items():
            assert page[key] == value


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('tei_url, html_url, check_pages', extraction_test_values)
def test_extract_fields_from_html(tei_url, html_url, check_pages, session):
    response = session.get(html_url)
    pages = ftpmd2catcher.extract_fields_from_html(html=response.text)
    for page, check_page in zip(pages, check_pages):
        for key, value in check_page.items():
            assert page[key] == value


@pytest.mark.skip(reason="TEI endpoint returning status 500")
@ftp_vcr.use_cassette()
@pytest.mark.parametrize('rendering_label', ftpmd2catcher.rendering_extractors.keys())
def test_load_ftp_manifest_data(rendering_label, session):
    cdm_object = ftpmd2catcher.CdmObject(
        ftp_manifest_url='https://fromthepage.com/iiif/47397/manifest'
    )
    ftpmd2catcher.load_ftp_manifest_data(cdm_object, rendering_label, session)
    assert cdm_object.pages
    assert cdm_object.ftp_work_url


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
    mapped = ftpmd2catcher.apply_field_mapping(ftp_fields, field_mapping)
    assert mapped == result


@pytest.mark.parametrize('pages, check_index', [
    ([
        {'Label0': '', 'Label1': ''},
        {'Label0': '', 'Label1': 'value1'},
        {'Label0': '', 'Label1': ''}
    ],
     1),
    ([
        None,
        None,
        {'Label0': 'value0', 'Label1': ''}
    ],
     2),
])
def test_PagePickers_first_filled_page(pages, check_index):
    assert ftpmd2catcher.PagePickers.first_filled_page(pages) is pages[check_index]


@pytest.mark.parametrize('pages', [
    [
        None,
        None,
        None,
    ],
    [],
    [
        {'Label0': '', 'Label1': ''},
        {'Label0': '', 'Label1': ''},
        {'Label0': '', 'Label1': ''},
    ],
])
def test_PagePickers_first_filled_page_raises(pages):
    with pytest.raises(LookupError):
        ftpmd2catcher.PagePickers.first_filled_page(pages)


@pytest.mark.parametrize('cdm_object, page_picker, result', [
    (ftpmd2catcher.CdmObject(dmrecord='1', pages=[{'Label': 'value'}]),
     ftpmd2catcher.PagePickers.first_page,
     {'dmrecord': '1', 'nick': 'value'})
])
def test_map_cdm_object_as_object(cdm_object, page_picker, result):
    field_mapping = {
        'Label': ['nick']
    }
    page = ftpmd2catcher.map_cdm_object_as_object(
        cdm_object=cdm_object,
        field_mapping=field_mapping,
        page_picker=page_picker
    )
    assert page == result


@ftp_vcr.use_cassette()
def test_get_cdm_item_info(session):
    cdm_object = ftpmd2catcher.CdmObject(
        repo_url='https://cdmdemo.contentdm.oclc.org',
        collection_alias='oclcsample',
        dmrecord='102'
    )
    item_info = ftpmd2catcher.get_cdm_item_info(cdm_object, session)
    assert item_info['dmrecord'] == cdm_object.dmrecord
    assert item_info['find']


@ftp_vcr.use_cassette()
@pytest.mark.parametrize('cdm_object, dmrecords', [
    # Compound Object
    (
        ftpmd2catcher.CdmObject(
            repo_url='https://cdmdemo.contentdm.oclc.org',
            collection_alias='oclcsample',
            dmrecord='12',
            pages=[
                {'Label': 'value1'},
                {'Label': 'value2'},
            ]
        ),
        ['10', '11']
    ),

    # Single Item
    (
        ftpmd2catcher.CdmObject(
            repo_url='https://cdmdemo.contentdm.oclc.org',
            collection_alias='oclcsample',
            dmrecord='64',
            pages=[
                {'Label': 'value1'}
            ]
        ),
        ['64']
    )
])
def test_map_cdm_object_as_pages(cdm_object, dmrecords, session):
    field_mapping = {
        'Label': ['nick']
    }

    pages_data = ftpmd2catcher.map_cdm_object_as_pages(
        cdm_object=cdm_object,
        field_mapping=field_mapping,
        session=session
    )

    for dmrecord, page, page_data  in zip(dmrecords, cdm_object.pages, pages_data):
        assert page_data == {
            'dmrecord': dmrecord,
            **ftpmd2catcher.apply_field_mapping(page, field_mapping)
        }
