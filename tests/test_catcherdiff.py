import pytest

import json

from cdm_util_scripts import catcherdiff


@pytest.mark.vcr
def test_catcherdiff(tmp_path):
    catcher_edits = [{"dmrecord": "71", "format": "PDF"}]
    catcher_json_file_path = tmp_path / "catcher-edits.json"
    report_file_path = tmp_path / "report.html"
    with open(catcher_json_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp)

    catcherdiff.catcherdiff(
        cdm_instance_url="https://cdmdemo.contentdm.oclc.org/",
        cdm_collection_alias="oclcsample",
        catcher_json_file_path=catcher_json_file_path,
        report_file_path=report_file_path,
        check_vocabs=True,
    )

    assert report_file_path.exists()
