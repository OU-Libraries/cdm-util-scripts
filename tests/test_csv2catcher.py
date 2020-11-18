import pytest
import vcr
import requests

import sys
from io import StringIO
from pathlib import Path

sys.path.append(str(Path('.').absolute()))
import csv2catcher


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/csv2catcher',
    record_mode='once'
)


@pytest.fixture(scope='module')
def session():
    with requests.Session() as session:
        yield session


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


@pytest.fixture()
def cdm_collection_row_mapping():
    return {
        'Work Title': 'identi',
        'Respondent name (last, first middle) (text)': 'testfi',
        'Format of folder materials (text)': 'testfa',
        'Additional formats (text)': 'testfa'
    }


@pytest.fixture()
def cdm_row():
    return {
        'Work Title': 'Test title',
        'Page Position': '1',
        'Respondent name (last, first middle) (text)': 'Testname, Testname',
        'Format of folder materials (text)': 'format-1',
        'Additional formats (text)': 'format-2'
    }


@pytest.fixture()
def cdm_row_blanks():
    return {
        'Work Title': 'Test title',
        'Page Position': '1',
        'Respondent name (last, first middle) (text)': 'Testname, Testname',
        'Format of folder materials (text)': '',
        'Additional formats (text)': ''
    }


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


def test_csv_dict_reader_with_join(cdm_collection_rows):
    test_csv = ("h1,h2,h1,h3\n"
                "c1a,c2,c1b,c3\n")
    reader = csv2catcher.csv_dict_reader_with_join(StringIO(test_csv))
    row = next(reader)
    assert row == {'h2': 'c2', 'h3': 'c3', 'h1': 'c1a; c1b'}

    test_csv_blanks = ("h1,h2,h1,h3\n"
                       ",c2,,c3\n")
    reader = csv2catcher.csv_dict_reader_with_join(StringIO(test_csv_blanks))
    row = next(reader)
    assert row == {'h2': 'c2', 'h3': 'c3', 'h1': ''}

    test_csv_mismatch = ("h1,h2,h3\n"
                         "c1,c2,c3,c4\n")
    with pytest.raises(ValueError):
        for row in csv2catcher.csv_dict_reader_with_join(StringIO(test_csv_mismatch)):
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
        csv2catcher.request_collection_page_pointers(cdm_collection=cdm_collection,
                                                     repo_url='https://media.library.ohio.edu',
                                                     alias='p15808coll15',
                                                     session=session)
    for cdm_object in cdm_collection:
        if cdm_object.is_cpd:
            assert cdm_object.page_pointers


def test_cdm_object_from_row(cdm_row, cdm_collection_row_mapping):
    cdm_object = csv2catcher.cdm_object_from_row(row=cdm_row,
                                                 column_mapping=cdm_collection_row_mapping,
                                                 identifier_nick='identi',
                                                 page_position_column_name='Page Position')
    identifier_column_name = [name for name, nick in cdm_collection_row_mapping.items()
                              if nick == 'identi'][0]
    identifier = cdm_row[identifier_column_name]
    assert cdm_object.identifier == identifier
    assert cdm_object.fields['testfa'] == 'format-1; format-2'


def test_cdm_object_from_row_blanks(cdm_row_blanks, cdm_collection_row_mapping):
    cdm_object = csv2catcher.cdm_object_from_row(row=cdm_row_blanks,
                                                 column_mapping=cdm_collection_row_mapping,
                                                 identifier_nick='identi',
                                                 page_position_column_name='Page Position')
    identifier_column_name = [name for name, nick in cdm_collection_row_mapping.items()
                              if nick == 'identi'][0]
    identifier = cdm_row_blanks[identifier_column_name]
    assert cdm_object.identifier == identifier
    assert cdm_object.fields['testfa'] == ''


def test_build_cdm_collection_from_rows(cdm_collection_rows, cdm_collection_row_mapping):
    cdm_collection = csv2catcher.build_cdm_collection_from_rows(rows=cdm_collection_rows,
                                                                column_mapping=cdm_collection_row_mapping,
                                                                identifier_nick='identi',
                                                                page_position_column_name='Page Position')
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
