import pytest

import json

from cdm_util_scripts import catchercombine


@pytest.mark.default_cassette("test_catchercombine.yaml")
@pytest.mark.vcr
@pytest.mark.parametrize(
    "catcher_edits,results,prepend",
    [
        (
            [
                {
                    "dmrecord": "71",
                    "title": "(Digital Collection Management)",
                    "subjec": "Information storage and retrieval systems",
                    "rights": "In Copyright",
                }
            ],
            [
                {
                    "dmrecord": "71",
                    "title": "CONTENTdm Brochure (Digital Collection Management)",
                    "subjec": "Digital images; Searching; Information storage and retrieval systems",
                    "rights": "In Copyright",
                }
            ],
            False,
        ),
        (
            [
                {
                    "dmrecord": "71",
                    "title": "Digital Collection Management",
                    "subjec": "Information storage and retrieval systems",
                    "rights": "In Copyright",
                }
            ],
            [
                {
                    "dmrecord": "71",
                    "title": "Digital Collection Management CONTENTdm Brochure",
                    "subjec": "Information storage and retrieval systems; Digital images; Searching",
                    "rights": "In Copyright",
                }
            ],
            True,
        ),
    ],
)
def test_catchercombine(tmp_path, catcher_edits, results, prepend):
    catcher_json_file_path = tmp_path / "catcher-edits.json"
    output_file_path = tmp_path / "combined-edits.json"
    with open(catcher_json_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp)

    catchercombine.catchercombine(
        cdm_instance_url="https://cdmdemo.contentdm.oclc.org/",
        cdm_collection_alias="oclcsample",
        catcher_json_file_path=catcher_json_file_path,
        output_file_path=output_file_path,
        prepend=prepend,
    )

    with open(output_file_path, mode="r", encoding="utf-8") as fp:
        read_edits = json.load(fp)

    assert read_edits == results
