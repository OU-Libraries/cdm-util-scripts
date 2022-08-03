import pytest

from datetime import datetime

from cdm_util_scripts import scanftpfields
from cdm_util_scripts import ftp_api


@pytest.mark.vcr
@pytest.fixture()
def ftp_collection(session):
    return ftp_api.get_and_load_ftp_collection(
        slug="ohiouniversitylibraries",
        collection_name="Dance Posters Metadata",
        rendering_label="XHTML Export",
        session=session,
    )


def test_count_filled_pages(ftp_collection):
    assert scanftpfields.count_filled_pages(ftp_collection)


def test_compile_field_frequencies(ftp_collection):
    assert scanftpfields.compile_field_frequencies(ftp_collection)


def test_compile_field_sets(ftp_collection):
    assert scanftpfields.compile_field_sets(ftp_collection)


def test_report_to_html(ftp_collection):
    report = scanftpfields.compile_report(ftp_collection)
    report['export_label_used'] = '?'
    report['report_date'] = datetime.now().isoformat()
    assert scanftpfields.report_to_html(report)
