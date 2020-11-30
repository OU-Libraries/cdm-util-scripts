import pytest
import vcr
import requests

import sys
from io import StringIO
from pathlib import Path

import csv2catcher


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/csv2catcher',
    # 'once' will fail with parameterized tests, 'new_episodes' seems to work
    record_mode='none'
)


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@pytest.fixture()
def cdm_collection_rows():
    with open('tests/inputs/fromthepage-tables-export_ryan-test-rows.csv') as fp:
        rows = [row for row in csv2catcher.csv_dict_reader_with_join(fp)]
    return rows


@pytest.fixture()
def cdm_records():
    with cdm_vcr.use_cassette('test_get_cdm_collection_object_records.yml'):
        cdm_records = csv2catcher.request_cdm_collection_object_records(
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            field_nicks=['identi'],
            session=requests
        )
    return cdm_records


def test_CdmObject__combine():
    assert csv2catcher.CdmObject._combine(None, 'b') == 'b'
    assert csv2catcher.CdmObject._combine('a', None) == 'a'
    assert csv2catcher.CdmObject._combine(None, None) is None
    assert csv2catcher.CdmObject._combine('a', 'a') == 'a'
    with pytest.raises(ValueError):
        csv2catcher.CdmObject._combine('a', 'b')


def test_CdmObject___add__():
    a = csv2catcher.CdmObject(pointer='1',
                              identifier='a')
    b = csv2catcher.CdmObject(identifier='a',
                              fields={'a': '1', 'b': '2'},
                              page_position=1,
                              is_cpd=True,
                              page_pointers=['2', '3'])
    c = a + b
    assert c.pointer == a.pointer
    assert c.identifier == a.identifier == b.identifier
    assert c.fields == b.fields
    assert c.page_position == b.page_position
    assert c.is_cpd == b.is_cpd
    assert c.page_pointers == b.page_pointers

    d = csv2catcher.CdmObject(identifier='d')
    with pytest.raises(ValueError):
        a + d


@pytest.mark.parametrize('csv, expected_row', [
    # No join
    (("h1,h2,h3\n"
      "c1,c2,c3\n"),
     {'h1': 'c1', 'h2': 'c2', 'h3': 'c3'}),
    # Join
    (("h1,h2,h1,h3\n"
      "c1a,c2,c1b,c3\n"),
     {'h1': 'c1a; c1b', 'h2': 'c2', 'h3': 'c3'}),
    # Join two blanks
    (("h1,h2,h1,h3\n"
      ",c2,,c3\n"),
     {'h1': '', 'h2': 'c2', 'h3': 'c3'}),
    # Join left blank
    (("h1,h2,h1,h3\n"
      ",c2,c1,c3\n"),
     {'h1': 'c1', 'h2': 'c2', 'h3': 'c3'}),
    # Join right blank
    (("h1,h2,h1,h3\n"
      "c1,c2,,c3\n"),
     {'h1': 'c1', 'h2': 'c2', 'h3': 'c3'}),
    # Strip whitespace
    (("h1,h2,h3\n"
      "c1, c2 ,c3\n"),
     {'h1': 'c1', 'h2': 'c2', 'h3': 'c3'}),
])
def test_csv_dict_reader_with_join(csv, expected_row):
    reader = csv2catcher.csv_dict_reader_with_join(StringIO(csv), seperator='; ')
    row = next(reader)
    assert row == expected_row


def test_csv_dict_reader_with_join_raises():
    test_csv_mismatch = ("h1,h2,h3\n"
                         "c1,c2,c3,c4\n")
    with pytest.raises(ValueError):
        reader = csv2catcher.csv_dict_reader_with_join(StringIO(test_csv_mismatch))
        for row in reader:
            pass


def test_request_cdm_collection_object_records(session):
    field_nicks = ['identi']
    with cdm_vcr.use_cassette('test_get_cdm_collection_object_records.yml'):
        cdm_records = csv2catcher.request_cdm_collection_object_records(
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            field_nicks=field_nicks,
            session=session
        )
    for record in cdm_records:
        for field_nick in field_nicks:
            assert field_nick in record


def test_build_cdm_collection_from_records(cdm_records):
    cdm_collection = csv2catcher.build_cdm_collection_from_records(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    assert len(cdm_records) == len(cdm_collection)
    for cdm_object in cdm_collection:
        assert isinstance(cdm_object.identifier, str)
        assert cdm_object.pointer
        assert isinstance(cdm_object.is_cpd, bool)


def test_request_collection_page_pointers(cdm_records, session):
    cdm_collection = csv2catcher.build_cdm_collection_from_records(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    with cdm_vcr.use_cassette('test_request_collection_page_pointers.yml'):
        csv2catcher.request_collection_page_pointers(
            cdm_collection=cdm_collection,
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            session=session
        )
    for cdm_object in cdm_collection:
        if cdm_object.is_cpd:
            assert cdm_object.page_pointers


@pytest.fixture()
def cdm_collection_row_mapping():
    return {
        'Work Title': ['identi', 'debug'],
        'Respondent name (last, first middle) (text)': ['testfi'],
        'Format of folder materials (text)': ['testfa'],
        'Additional formats (text)': ['testfa']
    }


@pytest.mark.parametrize('row, expected_fields', [
    # Two filled formats
    ({
        'Work Title': 'Test title',
        'Page Position': '1',
        'Respondent name (last, first middle) (text)': 'Testname, Testname',
        'Format of folder materials (text)': 'format-1',
        'Additional formats (text)': 'format-2'
    },
     {
         'debug': 'Test title',
         'testfi': 'Testname, Testname',
         'testfa': 'format-1; format-2',
     }),

    # Right blank format
    ({
        'Work Title': 'Test title',
        'Page Position': '1',
        'Respondent name (last, first middle) (text)': 'Testname, Testname',
        'Format of folder materials (text)': '',
        'Additional formats (text)': 'format-2'
    },
     {
         'debug': 'Test title',
         'testfi': 'Testname, Testname',
         'testfa': 'format-2',
     }),

    # Left blank format
    ({
        'Work Title': 'Test title',
        'Page Position': '1',
        'Respondent name (last, first middle) (text)': 'Testname, Testname',
        'Format of folder materials (text)': 'format-1',
        'Additional formats (text)': ''
    },
     {
         'debug': 'Test title',
         'testfi': 'Testname, Testname',
         'testfa': 'format-1',
     }),

    # Two blank formats
    ({
        'Work Title': 'Test title',
        'Page Position': '1',
        'Respondent name (last, first middle) (text)': 'Testname, Testname',
        'Format of folder materials (text)': '',
        'Additional formats (text)': ''
    },
     {
         'debug': 'Test title',
         'testfi': 'Testname, Testname',
         'testfa': '',
     })
])
def test_cdm_object_from_row(cdm_collection_row_mapping, row, expected_fields):
    page_position_column_name = 'Page Position'
    cdm_object = csv2catcher.cdm_object_from_row(
        row=row,
        column_mapping=cdm_collection_row_mapping,
        identifier_nick='identi',
        page_position_column_name=page_position_column_name
    )
    identifier_column_name = [name for name, nicks in cdm_collection_row_mapping.items()
                              if 'identi' in nicks][0]
    identifier = row[identifier_column_name]
    assert cdm_object.identifier == identifier
    assert cdm_object.page_position == int(row[page_position_column_name])
    assert cdm_object.fields == expected_fields


def test_build_cdm_collection_from_rows(cdm_collection_rows, cdm_collection_row_mapping):
    cdm_collection = csv2catcher.build_cdm_collection_from_rows(
        rows=cdm_collection_rows,
        column_mapping=cdm_collection_row_mapping,
        identifier_nick='identi',
        page_position_column_name='Page Position'
    )
    assert len(cdm_collection) == len(cdm_collection_rows)
    for cdm_object in cdm_collection:
        assert cdm_object.identifier


def test_build_identifier_to_object_index(cdm_records):
    cdm_collection = csv2catcher.build_cdm_collection_from_records(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    index = csv2catcher.build_identifier_to_object_index(cdm_collection=cdm_collection)
    assert len(cdm_collection) == sum(len(cdm_objects) for cdm_objects in index.values())
    for identifier, cdm_objects in index.items():
        for cdm_object in cdm_objects:
            assert cdm_object.identifier == identifier


def test_reconcile_indexes_by_object(cdm_collection_rows, cdm_collection_row_mapping, cdm_records):
    row_collection = csv2catcher.build_cdm_collection_from_rows(
        rows=cdm_collection_rows,
        column_mapping=cdm_collection_row_mapping,
        identifier_nick='identi',
        page_position_column_name='Page Position'
    )
    index_from_rows = csv2catcher.build_identifier_to_object_index(row_collection)
    record_collection = csv2catcher.build_cdm_collection_from_records(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    index_from_records = csv2catcher.build_identifier_to_object_index(
        cdm_collection=record_collection
    )
    reconciled = csv2catcher.reconcile_indexes_by_object(
        records_index=index_from_records,
        rows_index=index_from_rows
    )
    assert len(reconciled) == len(index_from_rows)
    for cdm_object in reconciled:
        assert cdm_object.pointer
        assert cdm_object.fields


def test_reconcile_indexes_by_page(cdm_collection_rows, cdm_collection_row_mapping, cdm_records, session):
    row_collection = csv2catcher.build_cdm_collection_from_rows(
        rows=cdm_collection_rows,
        column_mapping=cdm_collection_row_mapping,
        identifier_nick='identi',
        page_position_column_name='Page Position'
    )
    index_from_rows = csv2catcher.build_identifier_to_object_index(row_collection)
    record_collection = csv2catcher.build_cdm_collection_from_records(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    with cdm_vcr.use_cassette('test_request_collection_page_pointers.yml'):
        csv2catcher.request_collection_page_pointers(
            cdm_collection=record_collection,
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            session=session
        )
    index_from_records = csv2catcher.build_identifier_to_object_index(
        cdm_collection=record_collection
    )
    reconciled = csv2catcher.reconcile_indexes_by_page(
        records_index=index_from_records,
        rows_index=index_from_rows
    )
    assert len(reconciled) == len(row_collection)
    for cdm_object in reconciled:
        assert cdm_object.pointer
        assert cdm_object.fields


@pytest.mark.parametrize('match_mode, right_answers',
                         [
                             (csv2catcher.MatchMode.OBJECT,
                              {
                                  "ryan_box013-tld_f01": "5193",
                                  "ryan_box023-tld_f41": "5223",
                                  "ryan_box021-tld_f09": "5648",
                                  "ryan_box021-tld_f05": "5240"
                              }),
                             (csv2catcher.MatchMode.PAGE,
                              {
                                  "ryan_box013-tld_f01": "5173",
                                  "ryan_box023-tld_f41": "5221",
                                  "ryan_box021-tld_f09": "5642",
                                  "ryan_box021-tld_f05": "5227"
                              })
                         ])
def test_reconcile_cdm_collection(cdm_collection_rows,
                                  cdm_collection_row_mapping,
                                  match_mode,
                                  right_answers):
    row_collection = csv2catcher.build_cdm_collection_from_rows(
        rows=cdm_collection_rows,
        column_mapping=cdm_collection_row_mapping,
        identifier_nick='identi',
        page_position_column_name='Page Position'
    )
    with cdm_vcr.use_cassette('test_reconcile_cdm_collection.yml'):
        catcher_data = csv2catcher.reconcile_cdm_collection(
            cdm_collection=row_collection,
            repository_url='https://media.library.ohio.edu',
            collection_alias='p15808coll15',
            identifier_nick='identi',
            match_mode=match_mode
        )
    assert len(cdm_collection_rows) == len(catcher_data)
    row_index = csv2catcher.build_identifier_to_object_index(row_collection)
    rec_index = csv2catcher.build_identifier_to_object_index(catcher_data)
    for identifier, cdm_objects in row_index.items():
        rec_objects = rec_index[identifier]
        assert len(cdm_objects) == 1 and len(rec_objects) == 1
        dmrecord = right_answers[cdm_objects[0].identifier]
        assert rec_objects[0].pointer == dmrecord
        assert rec_objects[0].fields == cdm_objects[0].fields
