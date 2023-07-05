import json
import re

from typing import Optional, List, Dict


def catchertidy(
    catcher_json_file_path: str,
    output_file_path: str,
    normalize_whitespace: List[str],
    replace_smart_chars: List[str],
    normalize_lcsh: List[str],
    sort_terms: List[str],
    show_progress: bool,
) -> None:
    """Tidy up a cdm-catcher JSON edit."""
    with open(catcher_json_file_path, mode="r", encoding="utf-8") as fp:
        catcher_edits: List[Dict[str, str]] = json.load(fp)

    tidy_edits: List[Dict[str, str]] = []
    for edit in catcher_edits:
        tidy_edit: Dict[str, str] = {"dmrecord": edit["dmrecord"]}
        for nick, edit_value in edit.items():
            if nick == "dmrecord":
                continue

            if nick in normalize_whitespace:
                edit_value = normalize_whitespace_(edit_value)

            if nick in replace_smart_chars:
                edit_value = replace_smart_chars_(edit_value)

            if nick in normalize_lcsh:
                edit_value = normalize_lcsh_(edit_value)

            if nick in sort_terms:
                edit_value = sort_terms_(edit_value)

            tidy_edit[nick] = edit_value
        tidy_edits.append(tidy_edit)

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(tidy_edits, fp, indent=2)


def normalize_whitespace_(value: str) -> str:
    return " ".join(value.split())


def replace_smart_chars_(value: str) -> str:
    return value.translate(
        {
            0x201C: '"',
            0x201D: '"',
            0x2018: "'",
            0x2019: "'",
            0x2013: "-",
            0x2014: "--",
        }
    )


def normalize_lcsh_(terms: str) -> str:
    normalized_terms: List[str] = []
    for term in split_controlled_vocab(terms):
        term = replace_smart_chars_(normalize_whitespace_(term))
        parts = [part.strip() for part in term.rsplit("--")]
        normalized_terms.append(" -- ".join(parts))
    return "; ".join(normalized_terms)


def sort_terms_(terms: str) -> str:
    return "; ".join(sorted(split_controlled_vocab(terms)))


VOCAB_SPLIT_PAT = re.compile(r";\s*")


def split_controlled_vocab(values: str) -> List[str]:
    return [term for term in VOCAB_SPLIT_PAT.split(values) if term]
