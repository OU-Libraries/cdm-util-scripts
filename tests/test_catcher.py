import os
import xml.etree.ElementTree as ET
from unittest import mock

import pytest

from cdm_util_scripts import catcher


@pytest.mark.parametrize(
    "obj, order",
    [
        ({}, []),
        (
            {"nick": "value"},
            ["nick"],
        ),
        (
            {"nick": "value", "dmrecord": "1"},
            ["dmrecord", "nick"],
        ),
        (
            {"title": "Test", "nick": "value"},
            ["title", "nick"],
        ),
        (
            {"nick": "value", "dmrecord": "1", "title": "Test"},
            ["dmrecord", "title", "nick"],
        ),
        (
            {"nick": "value", "title": "Test", "dmrecord": "1"},
            ["dmrecord", "title", "nick"],
        ),
        (
            {"title": "Test", "dmrecord": "1", "nick": "value"},
            ["dmrecord", "title", "nick"],
        ),
    ]
)
def test_sorted_metadata_json_object(obj, order):
    assert list(catcher.sorted_metadata_json_object(obj)) == order


MOCK_ENIVRON = {
    "CATCHER_URL": "http://serverXXXXX.contentdm.oclc.org:XXXX",
    "CATCHER_USERNAME": "username",
    "CATCHER_PASSWORD": "password",
    "CATCHER_LICENSE": "XXXXX-XXXXX-XXXXX-XXXXX",
}


@pytest.fixture(autouse=True)
def mock_catcher_environ():
    with mock.patch.dict(
        os.environ,
        MOCK_ENIVRON,
    ):
        yield


def test_credentials_from_environ():

    def check_environment_variables(*args, **kwargs):
        assert kwargs["cdm_instance_url"] == MOCK_ENIVRON["CATCHER_URL"]
        assert kwargs["username"] == MOCK_ENIVRON["CATCHER_USERNAME"]
        assert kwargs["password"] == MOCK_ENIVRON["CATCHER_PASSWORD"]
        assert kwargs["license"] == MOCK_ENIVRON["CATCHER_LICENSE"]

    catcher.credentials_from_environ(check_environment_variables)()


def test_print_result(capsys):
    catcher.print_result(lambda: "Test")()
    captured = capsys.readouterr()
    assert captured.out == "Test\n"


def test_print_catalog_as_tsv(capsys):
    catalog_str = """\
<?xml version="1.0" encoding="utf-8" ?>
<collinfo>
  <num_collections>1</num_collections>
  <collection>
    <collection_alias>/alias</collection_alias>
    <collection_name>CONTENTdm archival collection</collection_name>
    <collection_fullres>
      <fullres_enabled>no</fullres_enabled>
    </collection_fullres>
  </collection>
</collinfo>"""
    catcher.print_catalog_as_tsv(lambda: catalog_str)()
    captured = capsys.readouterr()
    assert captured.out == (
        "alias\tname\tfullres_enabled\r\n"
        "/alias\tCONTENTdm archival collection\tFalse\r\n"
    )


def test_print_collection_config_as_tsv(capsys):
    collection_config_str = """\
<?xml version="1.0" encoding="utf-8" ?>
<fields>
  <code>0</code>
  <field>
    <admin>0</admin>
    <nickname>title</nickname>
    <name>Title</name>
    <type>TEXT</type>
    <size>0</size>
    <search>1</search>
    <hidden>0</hidden>
    <vocab>0</vocab>
    <vocdb></vocdb>
    <dcmap>title</dcmap>
    <req>1</req>
    <readonly>0</readonly>
    <tag></tag>
  </field>
</fields>"""
    catcher.print_collection_config_as_tsv(lambda: collection_config_str)()
    captured = capsys.readouterr()
    assert captured.out == (
        "admin\tnickname\tname\ttype\tsize\tsearch\thidden\tvocab\tvocdb\tdcmap\treq\treadonly\ttag\r\n"
        "False\ttitle\tTitle\tTEXT\tFalse\tTrue\tFalse\tFalse\t\ttitle\tTrue\tFalse\t\r\n"
    )


def test_print_terms_as_text(capsys):
    terms_str = """\
<?xml version="1.0" encoding="utf-8"?>
<terms>
  <term><![CDATA[Collection]]></term>
</terms>"""
    catcher.print_terms_as_text(lambda: terms_str)()
    captured = capsys.readouterr()
    assert captured.out == "Collection\n"


def test_get_elem_text_or_none():
    with pytest.raises(ValueError):
        catcher.get_elem_text_or_none(ET.Element("test"))
    root = ET.fromstring(
        "<root><record><one>One</one><two><nested>Two</nested></two></record></root>"
    )
    record = root.find("record")
    assert record is not None
    assert catcher.get_elem_text_or_none(record, "one") == "One"
    assert catcher.get_elem_text_or_none(record, "two", "nested") == "Two"
    assert catcher.get_elem_text_or_none(record, "three") is None
