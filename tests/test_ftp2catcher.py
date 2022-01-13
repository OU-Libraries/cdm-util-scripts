import pytest
import vcr
import requests

from cdm_util_scripts import ftp2catcher


cdm_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes/ftp2catcher',
    record_mode='once',
)


@cdm_vcr.use_cassette()
def test_find_cdm_objects(session):
    assert ftp2catcher.find_cdm_objects(
        repo_url='https://media.library.ohio.edu',
        alias='p15808coll15',
        field_nick='identi',
        value='ryan_box058-tlb_f26',
        session=session
    )
