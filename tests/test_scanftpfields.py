import pytest
import requests

from datetime import datetime

from cdm_util_scripts import scanftpfields
from cdm_util_scripts import ftp_api


@pytest.fixture
def ftp_collection():
    return ftp_api.get_and_load_ftp_collection(
        slug="ohiouniversitylibraries",
        collection_name="Dance Posters Metadata",
        rendering_label="XHTML Export",
        session=requests,
    )

@pytest.mark.default_cassette("ftp_collection.yaml")
@pytest.mark.vcr
def test_count_filled_pages(ftp_collection):
    assert scanftpfields.count_filled_pages(ftp_collection)


@pytest.mark.default_cassette("ftp_collection.yaml")
@pytest.mark.vcr
def test_compile_field_frequencies(ftp_collection):
    assert scanftpfields.compile_field_frequencies(ftp_collection)


@pytest.mark.default_cassette("ftp_collection.yaml")
@pytest.mark.vcr
def test_compile_field_sets(ftp_collection):
    assert scanftpfields.compile_field_sets(ftp_collection)


@pytest.mark.default_cassette("ftp_collection.yaml")
@pytest.mark.vcr
def test_report_to_html(ftp_collection):
    report = scanftpfields.compile_report(ftp_collection)
    report['export_label_used'] = '?'
    report['report_date'] = datetime.now().isoformat()
    assert scanftpfields.report_to_html(report)


@pytest.mark.default_cassette("ftp_collection.yaml")
@pytest.mark.vcr
def test_scanftpfields(tmp_path):
    scanftpfields.scanftpfields(
        ftp_slug="ohiouniversitylibraries",
        ftp_project_name="Dance Posters Metadata",
        rendering_label="XHTML Export",
        report_parent_path=tmp_path,
    )
    assert tmp_path.glob("field-label-report*.html")
