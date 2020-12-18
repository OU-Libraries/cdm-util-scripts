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
        assert cdm_object.repo_url
        assert cdm_object.cdm_source_url
        assert cdm_object.ftp_manifest_url


@ftp_vcr.use_cassette()
def test_get_rendering(session):
    response = session.get('https://fromthepage.com/iiif/48258/manifest')
    ftp_manifest = response.json()
    rendering = ftpmd2catcher.get_rendering(
        ftp_manifest=ftp_manifest,
        label='TEI Export'
    )
    assert rendering['@id'] == 'https://fromthepage.com/export/tei?work_id=48258'

    with pytest.raises(KeyError):
        ftpmd2catcher.get_rendering(
            ftp_manifest=ftp_manifest,
            label='Does Not Exist'
        )


@pytest.mark.skip()
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


@pytest.mark.skip()
@ftp_vcr.use_cassette()
def test_get_object_pages_from_TEI(session):
    cdm_object = ftpmd2catcher.CdmObject(
        ftp_manifest_url='https://fromthepage.com/iiif/45440/manifest'
    )
    ftpmd2catcher.get_object_pages_from_TEI(cdm_object, session)
    assert cdm_object.pages

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


@pytest.mark.parametrize('pages', [
    ([
        {'Label': 'value0'},
        {'Label': 'value1'}
    ]),
])
def test_PagePickers_first_page(pages):
    assert ftpmd2catcher.PagePickers.first_page(pages) is pages[0]


@pytest.mark.parametrize('pages, check_index', [
    ([
        {'Label0': '', 'Label1': ''},
        {'Label0': '', 'Label1': 'value1'},
        {'Label0': '', 'Label1': ''}
    ],
     1),
    ([
        {'Label0': '', 'Label1': ''},
        {'Label0': '', 'Label1': ''},
        {'Label0': '', 'Label1': ''}
    ],
     0),
])
def test_PagePickers_first_filled_page_or_blank(pages, check_index):
    assert ftpmd2catcher.PagePickers.first_filled_page_or_blank(pages) is pages[check_index]


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


def test_map_cdm_object_as_pages(monkeypatch):
    cdm_object = ftpmd2catcher.CdmObject(pages=[
        {'Label': 'value1'},
        {'Label': 'value2'},
        {'Label': 'value3'}
    ])
    field_mapping = {
        'Label': ['nick']
    }

    def mock(*args, **kwargs):
        return ['1', '2', '3']

    monkeypatch.setattr('ftpmd2catcher.ftpmd2catcher.get_cdm_page_pointers', mock)
    page_data = ftpmd2catcher.map_cdm_object_as_pages(
        cdm_object=cdm_object,
        field_mapping=field_mapping,
        session=None
    )
    assert page_data == [
        {'dmrecord': '1', 'nick': 'value1'},
        {'dmrecord': '2', 'nick': 'value2'},
        {'dmrecord': '3', 'nick': 'value3'}
    ]
