import pytest

import json

from cdm_util_scripts import catchercombineterms


@pytest.mark.default_cassette("test_catchercombineterms.yaml")
@pytest.mark.vcr
@pytest.mark.parametrize(
    "catcher_edits,results,sort_terms",
    [
        (
            [
                {
                    "dmrecord": "71",
                    "subjec": "Information storage and retrieval systems",
                    "rights": "In Copyright",
                }
            ],
            [
                {
                    "dmrecord": "71",
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
                    "subjec": "Information storage and retrieval systems",
                    "rights": "In Copyright",
                }
            ],
            [
                {
                    "dmrecord": "71",
                    "subjec": "Digital images; Information storage and retrieval systems; Searching",
                    "rights": "In Copyright",
                }
            ],
            True,
        ),
    ],
)
def test_catchercombineterms(tmp_path, catcher_edits, results, sort_terms):
    catcher_json_file_path = tmp_path / "catcher-edits.json"
    output_file_path = tmp_path / "combined-edits.json"
    with open(catcher_json_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp)

    catchercombineterms.catchercombineterms(
        cdm_instance_url="https://cdmdemo.contentdm.oclc.org/",
        cdm_collection_alias="oclcsample",
        catcher_json_file_path=catcher_json_file_path,
        output_file_path=output_file_path,
        sort_terms=sort_terms,
    )

    with open(output_file_path, mode="r", encoding="utf-8") as fp:
        read_edits = json.load(fp)

    assert read_edits == results


@pytest.mark.parametrize(
    "terms,results",
    [
        ("", []),
        ("a term", ["a term"]),
        ("term one; term two", ["term one", "term two"]),
        ("term one; term two;", ["term one", "term two"]),
        ("term one; term two; ", ["term one", "term two"]),
    ]
)
def test_split_terms(terms, results):
    splitted = catchercombineterms.split_terms(terms)
    assert splitted == results
