import pytest
import vcr
import requests

from datetime import datetime

from cdm_util_scripts import scanftpfields
from cdm_util_scripts import ftpfields2catcher


ftp_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/scanftpfields',
    record_mode='none'
)


@pytest.fixture(params=[
    {'slug': 'ohiouniversitylibraries', 'collection_name': 'Dance Posters Metadata', 'rendering_label': 'XHTML Export'},
    {'slug': 'ohiouniversitylibraries', 'collection_name': 'Ryan collection metadata', 'rendering_label': 'XHTML Export'},
])
@ftp_vcr.use_cassette()
def ftp_collection(request):
    with requests.Session() as session:
        ftp_collection = ftpfields2catcher.get_and_load_ftp_collection(
            **request.param,
            session=session
        )
    return ftp_collection


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
