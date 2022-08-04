import pytest
import requests

import json

from cdm_util_scripts import ftp2catcher


@pytest.mark.vcr
def test_find_cdm_objects():
    assert ftp2catcher.find_cdm_objects(
        repo_url="https://media.library.ohio.edu",
        alias="p15808coll15",
        field_nick="identi",
        value="ryan_box058-tlb_f26",
        session=requests,
    )


@pytest.mark.skip(
    reason="Can't find any live dc:source manifest examples in FromThePage"
)
@pytest.mark.vcr
def test_main(tmp_path, session):
    manifests_file_path = tmp_path / "manifests.txt"
    manifests_file_path.write_text(
        """
https://fromthepage.com/iiif/45434/manifest
https://fromthepage.com/iiif/36866/manifest
    """.strip(),
        encoding="utf-8",
    )
    transcript_nick = "descri"
    output_file_path = tmp_path / "output.json"
    ftp2catcher.main(
        [
            "https://media.library.ohio.edu",
            "p15808coll15",
            "identi",
            transcript_nick,
            str(manifests_file_path),
            str(output_file_path),
        ]
    )
    output = json.load(output_file_path.read_text(encoding="utf-8"))
    for edit in output:
        assert "dmrecord" in edit
        assert int(edit["dmrecord"])
        assert transcript_nick in edit
