import pytest

import json

from cdm_util_scripts import json2csv
from cdm_util_scripts import csv2json


@pytest.mark.parametrize(
    "input_json",
    [
        [
            {"dmrecord": "1", "subjec": "Electronic spreadsheets"},
            {"dmrecord": "2", "subjec": "Office information systems"},
        ],
    ]
)
def test_json2csv_csv2json(tmp_path, input_json):
    input_json_path = tmp_path / "test.json"
    output_csv_path = tmp_path / "test.csv"
    output_json_path = tmp_path / "result.json"
    with open(input_json_path, mode="w", encoding="utf-8") as fp:
        json.dump(input_json, fp)
    json2csv.json2csv(
        input_json_path=input_json_path,
        output_csv_path=output_csv_path,
    )
    csv2json.csv2json(
        input_csv_path=output_csv_path,
        output_json_path=output_json_path,
    )
    with open(output_json_path, mode="r", encoding="utf-8") as fp:
        result_json = json.load(fp)
    assert input_json == result_json


@pytest.mark.parametrize(
    "input_csv,result,drop_empty_cells",
    [
        (
            "dmrecord,subjec\n1,Electronic spreadsheets\n2,\n3,  \n",
            [
                {"dmrecord": "1", "subjec": "Electronic spreadsheets"},
                {"dmrecord": "2"},
                {"dmrecord": "3"},
            ],
            True,
        ),
        (
            "dmrecord,subjec\n1,Electronic spreadsheets\n2,\n3,  \n",
            [
                {"dmrecord": "1", "subjec": "Electronic spreadsheets"},
                {"dmrecord": "2", "subjec": ""},
                {"dmrecord": "3", "subjec": ""},
            ],
            False,
        ),
    ]
)
def test_csv2json(tmp_path, input_csv, result, drop_empty_cells):
    input_csv_path = tmp_path / "test.csv"
    output_json_path = tmp_path / "test.json"
    with open(input_csv_path, mode="w", encoding="utf-8") as fp:
        fp.write(input_csv)
    csv2json.csv2json(
        input_csv_path=input_csv_path,
        output_json_path=output_json_path,
        drop_empty_cells=drop_empty_cells,
    )
    with open(output_json_path, mode="r", encoding="utf-8") as fp:
        edits = json.load(fp)
    assert edits == result
