import pytest
import vcr
import requests

from datetime import datetime

import scanftpfields

ftp_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/scanftpfields',
    record_mode='none'
)


ftp_collection_number = '1073'
ftp_collection_url = f'https://fromthepage.com/iiif/collection/{ftp_collection_number}'


@pytest.fixture(scope='session')
def session():
    with requests.Session() as module_session:
        yield module_session


@pytest.fixture()
@ftp_vcr.use_cassette()
def filled_pages():
    with requests.Session() as session:
        ftp_collection = scanftpfields.request_collection(
            collection_url=ftp_collection_url,
            label='TEI Export',
            session=session
        )
    return scanftpfields.collection_as_filled_pages(ftp_collection)


def test_compile_field_frequencies(filled_pages):
    assert scanftpfields.compile_field_frequencies(filled_pages)


def test_compile_field_sets(filled_pages):
    assert scanftpfields.compile_field_sets(filled_pages)


def test_report_to_html(filled_pages):
    assert scanftpfields.report_to_html({
        'collection_number': ftp_collection_number,
        'collection_manifest': ftp_collection_url,
        'report_date': datetime.now().isoformat(),
        'export_label_used': 'TEI Export',
        'works_count': '?',
        'filled_pages_count': len(filled_pages),
        'field_label_frequencies': dict(scanftpfields.compile_field_frequencies(filled_pages)),
        'works_with_field_sets': scanftpfields.compile_field_sets(filled_pages),
    })
