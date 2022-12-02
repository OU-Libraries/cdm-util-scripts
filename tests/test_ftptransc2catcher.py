import pytest
import requests

import json

from cdm_util_scripts import ftptransc2catcher
from cdm_util_scripts import ftp_api


SPECIMEN_MANIFEST_URL = "https://fromthepage.com/iiif/25013044/manifest"
STARTS = [
    ("8358", "LST 134"),
    ("8359", "Ackley,"),
    ("8360", "- for Cornelius Ryan 2 -"),
    ("8361", "- for Cornelius Ryan 3 -"),
    ("8362", "402- 2nd Ave"),
    ("8363", "THE READER'S DIGEST"),
]


@pytest.mark.vcr
def test_ftptransc2catcher(tmp_path):
    manifests_listing_path = tmp_path / "manifests.txt"
    manifests_listing_path.write_text(SPECIMEN_MANIFEST_URL + "\n", encoding="utf-8")
    output_path = tmp_path / "output.json"
    transcript_nick = "transc"

    ftptransc2catcher.ftptransc2catcher(
        manifests_listing_path=manifests_listing_path,
        transcript_nick=transcript_nick,
        output_file_path=output_path,
        transcript_type="Verbatim Plaintext",
    )

    with open(output_path, mode="r", encoding="utf-8") as fp:
        output_json = json.load(fp)
    for edit, (dmrecord, start) in zip(output_json, STARTS):
        assert edit["dmrecord"] == dmrecord
        assert edit[transcript_nick].startswith(start)
        assert edit[transcript_nick] == edit[transcript_nick].strip()
        assert set(edit) == {"dmrecord", transcript_nick}
