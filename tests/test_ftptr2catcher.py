import pytest
import requests

import json

from cdm_util_scripts import ftptr2catcher
from cdm_util_scripts import ftp_api


SPECIMEN_MANIFEST_URL = "https://fromthepage.com/iiif/25013044/manifest"


@pytest.fixture
def ftp_manifest():
    return ftp_api.get_ftp_manifest(
        SPECIMEN_MANIFEST_URL, session=requests
    )


@pytest.mark.parametrize("url,alias,dmrecord", [
    ("https://cdm15808.contentdm.oclc.org/iiif/mss:188/canvas/c1", "mss", "188"),
    ("https://cdm15808.contentdm.oclc.org/digital/iiif/p15808coll19/1959/canvas/c0", "p15808coll19", "1959"),
])
def test_parse_canvas_id(url, alias, dmrecord):
    assert ftptr2catcher.parse_canvas_id(url) == (alias, dmrecord)


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_iter_manifest_sequence(ftp_manifest):
    for dmrecord, url in ftptr2catcher.iter_manifest_sequence(
        ftp_manifest, transcript_type="Verbatim Plaintext"
    ):
        assert int(dmrecord)
        assert url.startswith("https://")


@pytest.mark.default_cassette("ftp_manifest.yaml")
@pytest.mark.vcr
def test_get_manifest_catcher_edits(ftp_manifest):
    transcript_nick = "transc"
    catcher_edits = ftptr2catcher.get_manifest_catcher_edits(
        ftp_manifest,
        transcript_nick=transcript_nick,
        transcript_type="Verbatim Plaintext",
        session=requests,
    )
    for edit in catcher_edits:
        assert int(edit["dmrecord"])
        assert set(edit) == {"dmrecord", transcript_nick}


@pytest.mark.vcr
def test_get_manifests_catcher_edits():
    transcript_nick = "transc"
    transcript_type = "Verbatim Plaintext"
    catcher_edits = ftptr2catcher.get_manifests_catcher_edits(
        [
            SPECIMEN_MANIFEST_URL,
        ],
        transcript_type=transcript_type,
        transcript_nick=transcript_nick,
        session=requests,
    )
    for edit in catcher_edits:
        assert set(edit) == {"dmrecord", transcript_nick}
        assert int(edit["dmrecord"])


@pytest.mark.vcr
def test_main(tmp_path):
    manifests_listing_path = tmp_path / "manifests.txt"
    manifests_listing_path.write_text(
        SPECIMEN_MANIFEST_URL + "\n", encoding="utf-8"
    )
    output_path = tmp_path / "output.json"
    transcript_nick = "transc"
    ftptr2catcher.main([str(manifests_listing_path), transcript_nick, str(output_path)])
    with open(output_path, mode="r", encoding="utf-8") as fp:
        output_json = json.load(fp)
    for edit in output_json:
        assert set(edit) == {"dmrecord", transcript_nick}
        assert int(edit["dmrecord"])
