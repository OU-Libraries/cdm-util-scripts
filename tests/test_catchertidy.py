import json

import pytest

from cdm_util_scripts import catchertidy


def test_catchertidy(tmp_path):
    edits = [
        {
            "dmrecord": "1",
            "nicka": "The  quick \n brown fox  jumps\tover the “lazy” dog.",
            "nickb": "World War, 1939-1945--Journalists;\tFrancis Pope, 1936---Biography; ",
        },
    ]
    edits_path = tmp_path / "edits.json"
    output_path = tmp_path / "output.json"
    edits_path.write_text(json.dumps(edits))
    catchertidy.catchertidy(
        catcher_json_file_path=edits_path,
        output_file_path=output_path,
        normalize_whitespace=["nicka", "nickb"],
        replace_smart_chars=["nicka", "nickb"],
        normalize_lcsh=["nickb"],
        sort_terms=["nickb"],
    )
    json.load(output_path.open()) == [
        {
            "dmrecord": "1",
            "nicka": 'The quick brown fox jumps over the "lazy" dog.',
            "nickb": "Francis Pope, 1936- -- Biography; World War, 1939-1945 -- Journalists",
        }
    ]


@pytest.mark.parametrize(
    "before,after",
    [
        ("", ""),
        ("No change.", "No change."),
        ("“double quotes”", '"double quotes"'),
        ("‘single quotes’", "'single quotes'"),
        ("em—dash", "em--dash"),
        ("en–dash", "en-dash"),
    ],
)
def test_replace_smart_chars_(before, after):
    assert catchertidy.replace_smart_chars_(before) == after


@pytest.mark.parametrize(
    "before,after",
    [
        ("World War, 1939-1945--Journalists", "World War, 1939-1945 -- Journalists"),
        (
            "Soldiers--United States--20th century",
            "Soldiers -- United States -- 20th century",
        ),
        ("Francis Pope, 1936---Biography", "Francis Pope, 1936- -- Biography"),
        (
            "World War, 1939-1945--Journalists; Soldiers -- United States -- 20th century",
            "World War, 1939-1945 -- Journalists; Soldiers -- United States -- 20th century",
        ),
    ],
)
def test_normalize_lcsh_(before, after):
    assert catchertidy.normalize_lcsh_(before) == after


@pytest.mark.parametrize(
    "before,after",
    [
        ("single term", ["single term"]),
        ("term one; term two", ["term one", "term two"]),
        ("term one;term two", ["term one", "term two"]),
        ("term one;   term two", ["term one", "term two"]),
        ("term one;\tterm two", ["term one", "term two"]),
    ],
)
def test_split_controlled_vocab(before, after):
    assert catchertidy.split_controlled_vocab(before) == after
