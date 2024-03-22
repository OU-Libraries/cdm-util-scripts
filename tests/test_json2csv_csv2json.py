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
        csv_dialect="excel",
    )
    csv2json.csv2json(
        input_csv_path=output_csv_path,
        output_json_path=output_json_path,
        csv_dialect="excel",
    )
    with open(output_json_path, mode="r", encoding="utf-8") as fp:
        result_json = json.load(fp)
    assert input_json == result_json


@pytest.mark.parametrize(
    "input_csv, dialect, result, drop_empty_cells",
    [
        (
            "dmrecord,subjec\n1,Electronic spreadsheets\n2,\n3,  \n",
            "excel",
            [
                {"dmrecord": "1", "subjec": "Electronic spreadsheets"},
                {"dmrecord": "2"},
                {"dmrecord": "3"},
            ],
            True,
        ),
        (
            "dmrecord,subjec\n1,Electronic spreadsheets\n2,\n3,  \n",
            "excel",
            [
                {"dmrecord": "1", "subjec": "Electronic spreadsheets"},
                {"dmrecord": "2", "subjec": ""},
                {"dmrecord": "3", "subjec": ""},
            ],
            False,
        ),
        (
            'dmrecord,descri\r\n1,"Lorem ipsum dolor sit amet, ""consectetur"" adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."\r\n2,"Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."\r\n',
            "google-csv",
            [
                {"dmrecord": "1", "descri": 'Lorem ipsum dolor sit amet, "consectetur" adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'},
                {"dmrecord": "2", "descri": 'Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.'},
            ],
            False,
        ),
        (
            'dmrecord\tdescri\r\n1\tLorem ipsum dolor sit amet, "consectetur" adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\r\n2\tUt enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.\r\n',
            "google-tsv",
            [
                {"dmrecord": "1", "descri": 'Lorem ipsum dolor sit amet, "consectetur" adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'},
                {"dmrecord": "2", "descri": 'Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.'},
            ],
            False,
        )
    ]
)
def test_csv2json(tmp_path, input_csv, dialect, result, drop_empty_cells):
    input_csv_path = tmp_path / "test.csv"
    output_json_path = tmp_path / "test.json"
    with open(input_csv_path, mode="w", encoding="utf-8") as fp:
        fp.write(input_csv)
    csv2json.csv2json(
        input_csv_path=input_csv_path,
        output_json_path=output_json_path,
        csv_dialect=dialect,
        drop_empty_cells=drop_empty_cells,
    )
    with open(output_json_path, mode="r", encoding="utf-8") as fp:
        edits = json.load(fp)
    assert edits == result


@pytest.mark.parametrize(
    "input_csv, dialect, message_regex",
    [
        (
            "",
            "excel",
            r"CSV has no fieldnames",
        ),
        (
            'dmrecord,descri\r\n1,"Lorem ipsum dolor sit amet, consectetur adipiscing elit"\r\n',
            "excel-tab",
            r"CSV has only one fieldname 'dmrecord,descri' \(check CSV dialect\)",
        ),
        (
            'descri,subjec\r\n"Lorem ipsum dolor sit amet, consectetur adipiscing elit",Electronic records\r\n',
            "excel",
            r"CSV row 1 is missing dmrecord number",
        ),
        (
            'dmrecord,descri\r\n1,Lorem ipsum dolor sit amet, consectetur adipiscing elit\r\n',
            "excel",
            r"CSV row 1 has more fields than fieldnames \(check CSV dialect\)",
        ),
    ]
)
def test_csv2json_raises(tmp_path, input_csv, dialect, message_regex):
    input_csv_path = tmp_path / "test.csv"
    output_csv_path = tmp_path / "output.json"
    with open(input_csv_path, mode="w", encoding="utf-8", newline="") as fp:
        fp.write(input_csv)
    with pytest.raises(csv2json.CSVParsingError, match=message_regex):
        csv2json.csv2json(
            input_csv_path=input_csv_path,
            output_json_path=output_csv_path,
            csv_dialect=dialect,
        )
    assert not output_csv_path.exists()
