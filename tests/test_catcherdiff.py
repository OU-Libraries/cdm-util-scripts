import pytest

import json
import collections
import xml.etree.ElementTree as ET
import html

from cdm_util_scripts import catcherdiff


DeltaRow = collections.namedtuple("DeltaRow", "dmrecord controlled nick curr_val change edit_val")


@pytest.mark.vcr
def test_catcherdiff(tmp_path):
    catcher_edits = [
        {
            "dmrecord": "71",
            "subjec": "Information storage and retrieval systems",
            "creato": "",
            "format": "PDF",
            "date": "2010   ",
            "rights": "Test\ntest\ttest."
        },
    ]
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

    delta_rows = scrape_report(report_file_path)

    assert delta_rows == [
        DeltaRow("71", True, "subjec", "Digital images; Searching", "Replace", "Information storage and retrieval systems"),
        DeltaRow("71", False, "creato", "OCLC", "Delete", ""),
        DeltaRow("71", False, "format", "pdf", "Replace", "PDF"),
        DeltaRow("71", False, "date", "2010", "None", "2010"),
        DeltaRow("71", False, "rights", "", "New", "TestLFtestTABtest."),
    ]


def scrape_report(path):
    diff = ET.parse(path)
    h3s = diff.findall(".//h3")
    tbodys = diff.findall(".//table[@class='delta-table']/tbody")
    rows = []
    for h3, tbody in zip(h3s, tbodys):
        dmrecord = h3.text.partition(" ")[2]
        for tr in tbody.findall("tr"):
            ctrl_col, nick_col, curr_col, change_col, edit_col = tr.findall("td")
            rows.append(
                DeltaRow(
                    dmrecord=dmrecord,
                    controlled=is_controlled(ctrl_col),
                    nick=nick_col.find("./span[@class='cdm-nick']").text,
                    curr_val=html.unescape("".join(curr_col.find('span').itertext())),
                    change=change_col.text,
                    edit_val=html.unescape("".join(edit_col.find('span').itertext())),
                )
            )
    return rows


def is_controlled(ctrl_col):
    content = "".join(ctrl_col.itertext())
    if not content:
        return False
    if content == "\N{LOCK}":
        return True
    raise ValueError(repr(content))


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

