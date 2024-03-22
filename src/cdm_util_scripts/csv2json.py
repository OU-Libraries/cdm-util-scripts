import csv
import json

from typing import Union, Dict, List


def csv2json(
    input_csv_path: str,
    output_json_path: str,
    csv_dialect: Union[str, csv.Dialect],
    drop_empty_cells: bool = True,
    show_progress: bool = False
) -> None:
    """Transpose a CSV file into a list of JSON objects (cdm-catcher JSON edits)"""
    with open(input_csv_path, mode="r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp, dialect=csv_dialect)
        if not reader.fieldnames:
            raise CSVParsingError("CSV has no fieldnames")
        if len(reader.fieldnames) == 1:
            raise CSVParsingError(f"CSV has only one fieldname {reader.fieldnames[0]!r} (check CSV dialect)")
        rows: List[Dict[str, str]] = []
        for rownum, row in enumerate(reader, start=1):
            if not row.get("dmrecord"):
                raise CSVParsingError(f"CSV row {rownum} is missing dmrecord number")
            if None in row:
                raise CSVParsingError(f"CSV row {rownum} has more fields than fieldnames (check CSV dialect)")
            if drop_empty_cells:
                json_row = {nick: value.strip() for nick, value in row.items() if value and not value.isspace()}
            else:
                json_row = {nick: value.strip() for nick, value in row.items()}
            rows.append(json_row)

    with open(output_json_path, mode="w", encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2)


class CSVParsingError(Exception):
    pass


# The Google Sheets dialects seem to be the same as the Excel ones
class GoogleSheetsCSV(csv.Dialect):
    delimiter = ","
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = "\r\n"
    quoting = csv.QUOTE_MINIMAL


class GoogleSheetsTSV(GoogleSheetsCSV):
    delimiter = "\t"


csv.register_dialect("google-csv", GoogleSheetsCSV)
csv.register_dialect("google-tsv", GoogleSheetsTSV)
