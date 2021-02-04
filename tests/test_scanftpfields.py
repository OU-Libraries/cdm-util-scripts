import pytest
import vcr
import requests

from datetime import datetime

import scanftpfields
import ftpmd2catcher

ftp_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/scanftpfields',
    record_mode='none'
)


slug = 'ohiouniversitylibraries'
collection_name = 'Dance Posters Metadata'
rendering_label = 'XHTML Export'


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@pytest.fixture()
@ftp_vcr.use_cassette()
def ftp_collection():
    with requests.Session() as session:
        ftp_collection = ftpmd2catcher.get_and_load_ftp_collection(
            slug=slug,
            collection_name=collection_name,
            rendering_label=rendering_label,
            session=session
        )
    return ftp_collection


def test_compile_field_frequencies(ftp_collection):
    filled_pages = scanftpfields.collection_as_filled_pages(ftp_collection)
    assert scanftpfields.compile_field_frequencies(filled_pages)


def test_compile_field_sets(ftp_collection):
    filled_pages = scanftpfields.collection_as_filled_pages(ftp_collection)
    assert scanftpfields.compile_field_sets(filled_pages)


def test_report_to_html(ftp_collection):
    report = scanftpfields.compile_report(ftp_collection)
    report['export_label_used'] = rendering_label
    report['report_date'] = datetime.now().isoformat()
    assert scanftpfields.report_to_html(report)
