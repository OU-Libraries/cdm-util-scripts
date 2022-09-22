import pytest

import json
import collections

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


def test_count_changes():
    deltas = [
        catcherdiff.Delta(
            edit={"dmrecord": "71", "format": "PDF"},
            item_info={"dmrecord": "71", "format": "pdf"},
        ),
        catcherdiff.Delta(
            edit={"dmrecord": "72", "format": "PNG"},
            item_info={"dmrecord": "72", "format": "PNG"},
        ),
        catcherdiff.Delta(
            edit={"dmrecord": "73", "format": "JPG", "date": "2022"},
            item_info={"dmrecord": "73", "format": "JPEG", "date": "2022"},
        )

    ]
    edits_with_changes_count, nicks_with_changes, nicks_with_edits = catcherdiff.count_changes(deltas)
    assert edits_with_changes_count == 2
    assert nicks_with_changes == collections.Counter(["format", "format"])
    assert nicks_with_edits == collections.Counter(["format", "format", "format", "date"])
