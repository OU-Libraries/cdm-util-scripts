import pytest
import vcr
import requests

import sys
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
def cdm_collection():
    return [
        csv2catcher.CdmObject(pointer='1', identifier='test01', is_cpd=False),
        csv2catcher.CdmObject(pointer='2', identifier='test02', is_cpd=False),
        csv2catcher.CdmObject(pointer='457',
                              identifier='ryan_box09-tld_f11',
                              is_cpd=True,
                              page_pointers=['452', '453', '454', '455', '456'])
    ]


@pytest.fixture()
def catcher_records():
    return [
        {'identi': 'test01', 'feildnicka': 'a1', 'fieldnickb': 'b1', 'fieldnickc': 'c1'},
        {'identi': 'test02', 'feildnicka': 'a2', 'fieldnickb': 'b2', 'fieldnickc': 'c2'},
        {'identi': 'ryan_box09-tld_f11', 'feildnicka': 'a3', 'fieldnickb': 'b3', 'fieldnickc': 'c3'},
    ]


@pytest.fixture()
def cdm_records():
    return [{'collection': '/p15808coll15',
             'pointer': 314,
             'filetype': 'cpd',
             'parentobject': -1,
             'identi': 'ryan_box50-tlb_f05',
             'find': '315.cpd'},
            {'collection': '/p15808coll15',
             'pointer': 329,
             'filetype': 'cpd',
             'parentobject': -1,
             'identi': 'ryan_box50-tlb_f10',
             'find': '330.cpd'},
            {'collection': '/p15808coll15',
             'pointer': 254,
             'filetype': 'cpd',
             'parentobject': -1,
             'identi': 'ryan_box50-tlb_f24',
             'find': '255.cpd'},
            {'collection': '/p15808coll15',
             'pointer': 300,
             'filetype': 'cpd',
             'parentobject': -1,
             'identi': 'ryan_box50-tlb_f27',
             'find': '301.cpd'}]


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


def test_get_cdm_collection_object_records(session):
    with cdm_vcr.use_cassette('test_get_cdm_collection_object_records.yml'):
        cdm_records = csv2catcher.get_cdm_collection_object_records(
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            field_nicks=['identi'],
            session=session
        )
    assert cdm_records


def test_build_identifier_to_object_pointer_index(cdm_records):
    index = csv2catcher.build_identifier_to_object_pointer_index(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    assert len(index) == len(cdm_records)


def test_build_identifier_to_object_pointer_index_unique(cdm_records):
    cdm_records[3]['identi'] = cdm_records[0]['identi']
    with pytest.raises(KeyError):
        csv2catcher.build_identifier_to_object_pointer_index(
            cdm_records=cdm_records,
            identifier_nick='identi'
        )


@pytest.mark.skip(reason="Duplicate identifiers in Ryan")
def test_build_identifier_to_object_and_page_pointer_index(session):
    with cdm_vcr.use_cassette('test_get_cdm_collection_object_records.yml'):
        cdm_records = csv2catcher.get_cdm_collection_object_records(
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            field_nicks=['identi'],
            session=session
        )
    identifier_to_object_pointer_index = csv2catcher.build_identifier_to_object_pointer_index(
        cdm_records=cdm_records,
        identifier_nick='identi'
    )
    with cdm_vcr.use_cassette('test_build_identifier_to_object_and_page_pointer_index.yml'):
        identifier_to_object_and_page_pointer_index = csv2catcher.build_identifier_to_object_and_page_pointer_index(
            repo_url='https://media.library.ohio.edu',
            alias='p15808coll15',
            identifier_to_object_pointer_index=identifier_to_object_pointer_index,
            session=session)
    assert identifier_to_object_and_page_pointer_index
