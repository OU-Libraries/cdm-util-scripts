import pytest
import requests

import json
import csv
from io import StringIO

from cdm_util_scripts import csv2catcher


@pytest.fixture
def cdm_collection_rows():
    with open('tests/inputs/fromthepage-tables-export_ryan-test-rows.csv') as fp:
        rows = [row for row in csv2catcher.csv_dict_reader_with_join(fp, dialect="unix")]
    return rows


@pytest.fixture
def cdm_records():
    return [
        {'collection': '/p15808coll15',
         'pointer': 5240,
         'filetype': 'cpd',
         'parentobject': -1,
         'identi': 'ryan_box021-tld_f05',
         'find': '5241.cpd'},
        {'collection': '/p15808coll15',
         'pointer': 5223,
         'filetype': 'cpd',
         'parentobject': -1,
         'identi': 'ryan_box023-tld_f41',
         'find': '5224.cpd'},
        {'collection': '/p15808coll15',
         'pointer': 5193,
         'filetype': 'cpd',
         'parentobject': -1,
         'identi': 'ryan_box013-tld_f01',
         'find': '5194.cpd'},
        {'collection': '/p15808coll15',
         'pointer': 5648,
         'filetype': 'cpd',
         'parentobject': -1,
         'identi': 'ryan_box021-tld_f09',
         'find': '5649.cpd'}
    ]


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
    reader = csv2catcher.csv_dict_reader_with_join(StringIO(csv), dialect="unix", join_with='; ')
    row = next(reader)
    assert row == expected_row


def test_csv_dict_reader_with_join_raises():
    test_csv_mismatch = ("h1,h2,h3\n"
                         "c1,c2,c3,c4\n")
    with pytest.raises(ValueError):
        reader = csv2catcher.csv_dict_reader_with_join(StringIO(test_csv_mismatch), dialect="unix")
        for row in reader:
            pass


@pytest.mark.vcr
def test_request_cdm_collection_object_records():
    field_nicks = ['identi']
    cdm_records = csv2catcher.request_cdm_collection_object_records(
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        field_nicks=field_nicks,
        session=requests,
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


@pytest.mark.vcr
def test_request_collection_page_pointers(cdm_records):
    cdm_collection = csv2catcher.build_cdm_collection_from_records(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    csv2catcher.request_collection_page_pointers(
        cdm_collection=cdm_collection[:5],
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        session=requests,
    )
    for cdm_object in cdm_collection:
        if cdm_object.is_cpd:
            assert cdm_object.page_pointers


@pytest.fixture
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
        cdm_records=cdm_records[:5],
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


@pytest.mark.vcr
def test_reconcile_indexes_by_page(cdm_collection_rows, cdm_collection_row_mapping, cdm_records):
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
    csv2catcher.request_collection_page_pointers(
        cdm_collection=record_collection,
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        session=requests,
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


@pytest.mark.default_cassette("test_reconcile_cdm_collection.yaml")
@pytest.mark.vcr
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


@pytest.mark.vcr
def test_csv2catcher(tmpdir):
    reconciliation_config = {
        "repository-url": "https://cdmdemo.contentdm.oclc.org/",
        "collection-alias": "oclcsample",
        "identifier-nick": "title",
        "match-mode": "page",
        "page-position-column-name": "Page Position",
    }
    config_path = tmpdir / "reconciliation_config.json"
    with open(config_path, mode="w", encoding="utf-8") as fp:
        json.dump(reconciliation_config, fp)

    column_mapping_csv = [
        {"name": "Subject", "nick": "subjec"},
        {"name": "Title", "nick": "title"},
    ]
    mapping_csv_path = tmpdir / "column_mapping.csv"
    with open(mapping_csv_path, mode="w", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["name", "nick"], dialect="unix")
        writer.writeheader()
        writer.writerows(column_mapping_csv)

    field_data = [
        {"Page Position": "3", "Title": "Abridged Monograph", "Subject": "Suspension bridges"}
    ]
    field_data_path = tmpdir / "field-data.csv"
    with open(field_data_path, mode="w", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(field_data[0]), dialect="unix")
        writer.writeheader()
        writer.writerows(field_data)

    output_file = tmpdir / "output.json"

    csv2catcher.csv2catcher(
        reconciliation_config_path=config_path,
        column_mapping_csv_path=mapping_csv_path,
        field_data_csv_path=field_data_path,
        output_file_path=output_file,
    )

    assert json.load(output_file) == [
        {"dmrecord": "98", "subjec": "Suspension bridges"}
    ]
