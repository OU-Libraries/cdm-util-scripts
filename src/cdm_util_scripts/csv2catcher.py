import requests

import json
import csv
import argparse
import sys
from dataclasses import dataclass
from collections import defaultdict
from itertools import count
from enum import Enum

from cdm_util_scripts.cdm_api import get_cdm_page_pointers

from typing import List, Optional, Dict, Sequence, Iterator, TextIO


@dataclass
class CdmObject:
    pointer: Optional[str] = None
    identifier: Optional[str] = None
    fields: Optional[dict] = None
    page_position: Optional[int] = None
    is_cpd: Optional[bool] = None
    page_pointers: Optional[List[str]] = None

    def __add__(self, other: object) -> 'CdmObject':
        if not isinstance(other, CdmObject):
            return NotImplemented
        return CdmObject(pointer=self._combine(self.pointer, other.pointer),
                         identifier=self._combine(self.identifier, other.identifier),
                         fields=self._combine(self.fields, other.fields),
                         page_position=self._combine(self.page_position, other.page_position),
                         is_cpd=self._combine(self.is_cpd, other.is_cpd),
                         page_pointers=self._combine(self.page_pointers, other.page_pointers))

    @staticmethod
    def _combine(a: object, b: object) -> object:
        if a == b:
            return a
        if a and b:
            raise ValueError("combination collision: {a!r} and {b!r}")
        return a or b


class MatchMode(Enum):
    PAGE = 'page'
    OBJECT = 'object'


def csv_dict_reader_with_join(fp: TextIO, seperator: str = '; ') -> Iterator[Dict[str, str]]:
    reader = csv.reader(fp)
    try:
        header = [column_name.strip() for column_name in next(reader)]
    except StopIteration:
        raise ValueError("empty CSV")
    for csv_row in reader:
        if len(csv_row) != len(header):
            raise ValueError("CSV header and row length mismatch")
        row = dict()
        for column_name, cell in zip(header, csv_row):
            cell = cell.strip()
            if column_name in row:
                if cell:
                    if row[column_name]:
                        row[column_name] = seperator.join([row[column_name], cell])
                    else:
                        row[column_name] = cell
            else:
                row[column_name] = cell
        yield row


def request_cdm_collection_object_records(repo_url: str,
                                          alias: str,
                                          field_nicks: Sequence[str],
                                          session: requests.Session,
                                          verbose: bool = True) -> List[dict]:
    cdm_records = []
    total = 1
    start = 1
    maxrecs = 1024
    if verbose:
        print("Requesting object pointers...", end='\r')
    while len(cdm_records) < total:
        response = session.get(f"{repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmQuery/{alias}/CISOSEARCHALL/{'!'.join(field_nicks)}/pointer/{maxrecs}/{start}/1/0/0/0/0/1/json")
        response.raise_for_status()
        dmQuery = response.json()
        total = int(dmQuery['pager']['total'])
        start += maxrecs
        cdm_records += dmQuery['records']
        if verbose:
            print(f"Requesting object pointers: {len(cdm_records)}/{total} {(len(cdm_records) / total) * 100:2.0f}%",
                  end='\r',
                  flush=True)
    if verbose:
        print(end='\n')
    return cdm_records


def build_cdm_collection_from_records(cdm_records: List[dict], identifier_nick: str) -> List[CdmObject]:
    return [CdmObject(pointer=str(record['pointer']),
                      identifier=record[identifier_nick],
                      is_cpd=record['find'].endswith('.cpd')) for record in cdm_records]


def request_collection_page_pointers(
        cdm_collection: Sequence[CdmObject],
        repo_url: str,
        alias: str,
        session: requests.Session,
        verbose: bool = True
) -> None:
    if verbose:
        total_cpd = sum(1 if o.is_cpd else 0 for o in cdm_collection)
        request_count = count(1)
    for cdm_object in cdm_collection:
        if cdm_object.is_cpd:
            if verbose:
                n = next(request_count)
                print(f"Requesting page pointers: {n}/{total_cpd} {(n / total_cpd) * 100:2.0f}%",
                      end='\r',
                      flush=True)
            cdm_object.page_pointers = get_cdm_page_pointers(
                repo_url=repo_url,
                alias=alias,
                dmrecord=cdm_object.pointer,
                session=session
            )
    if verbose:
        print(end='\n')


def cdm_object_from_row(
        row: Dict[str, str],
        column_mapping: Dict[str, List[str]],
        identifier_nick: Optional[str],
        page_position_column_name: Optional[str]
) -> CdmObject:
    fields = dict()
    for name, nicks in column_mapping.items():
        field = row[name]
        for nick in nicks:
            if nick in fields:
                if field:
                    if fields[nick]:
                        fields[nick] = '; '.join([fields[nick], field])
                    else:
                        fields[nick] = field
            else:
                fields[nick] = field
    identifier = fields.pop(identifier_nick) if identifier_nick else None
    page_position = int(row[page_position_column_name]) if page_position_column_name else None
    return CdmObject(identifier=identifier,
                     page_position=page_position,
                     fields=fields)


def build_cdm_collection_from_rows(
        rows: Sequence[Dict[str, str]],
        column_mapping: Dict[str, List[str]],
        identifier_nick: Optional[str],
        page_position_column_name: Optional[str]
) -> List[CdmObject]:
    return [cdm_object_from_row(
        row=row,
        column_mapping=column_mapping,
        identifier_nick=identifier_nick,
        page_position_column_name=page_position_column_name
    )
            for row in rows]


def build_identifier_to_object_index(cdm_collection: List[CdmObject]) -> Dict[str, List[CdmObject]]:
    cdm_index = defaultdict(list)
    for cdm_object in cdm_collection:
        cdm_index[cdm_object.identifier].append(cdm_object)
    return dict(cdm_index)


def reconcile_indexes_by_object(records_index: Dict[str, List[CdmObject]],
                                rows_index: Dict[str, List[CdmObject]]) -> List[CdmObject]:
    reconciled = []
    for identifier, row_objects in rows_index.items():
        if len(row_objects) > 1:
            raise ValueError(f"row collision on {identifier!r}")
        for cdm_object in records_index[identifier]:
            reconciled.append(cdm_object + row_objects[0])
    return reconciled


def reconcile_indexes_by_page(records_index: Dict[str, List[CdmObject]],
                              rows_index: Dict[str, List[CdmObject]]) -> List[dict]:
    reconciled = []
    for identifier, row_objects in rows_index.items():
        for row_object in row_objects:
            for record_object in records_index[identifier]:
                reconciled.append(
                    row_object + CdmObject(pointer=record_object.page_pointers[row_object.page_position - 1])
                )
    return reconciled


def serialize_cdm_objects(cdm_objects: Sequence[CdmObject]) -> List[dict]:
    series = []
    for cdm_object in cdm_objects:
        fields = dict()
        if cdm_object.pointer:
            fields['dmrecord'] = cdm_object.pointer
        fields.update(cdm_object.fields)
        series.append(fields)
    return series


def reconcile_cdm_collection(
        cdm_collection: Sequence[CdmObject],
        repository_url: str,
        collection_alias: str,
        identifier_nick: str,
        match_mode: MatchMode,
        verbose: bool = True
) -> List[CdmObject]:
    row_object_index = build_identifier_to_object_index(cdm_collection)
    with requests.Session() as session:
        cdm_records = request_cdm_collection_object_records(
            repo_url=repository_url,
            alias=collection_alias,
            field_nicks=[identifier_nick],
            session=session
        )
        cdm_collection_from_records = build_cdm_collection_from_records(
            cdm_records=cdm_records,
            identifier_nick=identifier_nick
        )

        # Drop unneeded record objects to keep page pointer requests to the minimum
        cdm_collection_from_records = [cdm_object for cdm_object in cdm_collection_from_records
                                       if cdm_object.identifier in row_object_index]
        if match_mode is MatchMode.PAGE:
            request_collection_page_pointers(
                cdm_collection=cdm_collection_from_records,
                repo_url=repository_url,
                alias=collection_alias,
                session=session
            )
    record_object_index = build_identifier_to_object_index(cdm_collection_from_records)

    # Are there rows in the field data CSV for which CONTENTdm objects could not be found?
    unreconcilable_row_identifiers = [identifier for identifier in row_object_index.keys()
                                      if identifier not in record_object_index]

    # Are there multiple CONTENTdm objects with the same identifier?
    confused_cdm_identifiers = [identifier for identifier, cdm_objects in record_object_index.items()
                                if len(cdm_objects) > 1]

    if unreconcilable_row_identifiers or confused_cdm_identifiers:
        if verbose:
            for identifier in unreconcilable_row_identifiers:
                print(f"Couldn't find {identifier!r} in field {identifier_nick!r}")
            for identifier in confused_cdm_identifiers:
                print(f"Multiple results for {identifier!r} in field {identifier_nick!r}")
        raise KeyError("identifier mismatch(es)")
    elif match_mode is MatchMode.OBJECT:
        catcher_data = reconcile_indexes_by_object(
            records_index=record_object_index,
            rows_index=row_object_index
        )
    elif match_mode is MatchMode.PAGE:
        catcher_data = reconcile_indexes_by_page(
            records_index=record_object_index,
            rows_index=row_object_index
        )
    else:
        raise ValueError(f"invalid match-mode {match_mode!r}")

    return catcher_data


def main():
    parser = argparse.ArgumentParser(description="Transform and reconcile CSVs into cdm-catcher JSON",
                                     fromfile_prefix_chars='@')
    parser.add_argument('reconciliation_config',
                        type=str,
                        help="Path to a collection reconciliation JSON configuration file")
    parser.add_argument('column_mapping_csv',
                        type=str,
                        help="Path to CSV with columns 'name' and 'nick' mapping column names to CONTENTdm field nicknames")
    parser.add_argument('field_data_csv',
                        type=str,
                        help="Path to field data CSV")
    parser.add_argument('output_file',
                        type=str,
                        help="Path to output cdm-catcher JSON")
    args = parser.parse_args()

    # Read reconciliation_config
    with open(args.reconciliation_config, mode='r', encoding="utf-8") as fp:
        reconciliation_config = json.load(fp)

    repository_url = reconciliation_config.get('repository-url', None)
    collection_alias = reconciliation_config.get('collection-alias', None)
    identifier_nick = reconciliation_config.get('identifier-nick', None)
    match_mode_value = reconciliation_config.get('match-mode', None)
    page_position_column_name = reconciliation_config.get('page-position-column-name', None)

    # Validate reconciliation_config settings
    reconciliation_args = (repository_url, collection_alias, identifier_nick)
    if any(reconciliation_args) and not all(reconciliation_args):
        print(f"{args.reconciliation_config!r}: all of repository-url, collection-alias, identifier-nick and match-mode must be specified for reconciliation")
        sys.exit(1)

    if not match_mode_value:
        print(f"{args.reconciliation_config!r}: match-mode must be specified")
        sys.exit(1)

    match_mode_index = {mode.value: mode for mode in iter(MatchMode)}
    if match_mode_value not in match_mode_index:
        print(f"{args.reconciliation_config!r}: invalid match-mode value {match_mode_value!r}")
        sys.exit(1)
    else:
        match_mode = match_mode_index[match_mode_value]

    if match_mode == MatchMode.PAGE and not page_position_column_name:
        print(f"{args.reconciliation_config!r}: match-mode page requires page-position-column-name")
        sys.exit(1)

    # Read column_mapping_csv
    with open(args.column_mapping_csv, mode='r', encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            print(f"{args.column_mapping_csv!r}: column mapping CSV must have 'name' and 'nick' column titles in that order")
            sys.exit(1)
        column_mapping = defaultdict(list)
        for row in reader:
            column_mapping[row['name']].append(row['nick'])
        column_mapping = dict(column_mapping)

    # Read field_data_csv
    with open(args.field_data_csv, mode='r', encoding="utf-8") as fp:
        cdm_collection_from_rows = build_cdm_collection_from_rows(
            rows=csv_dict_reader_with_join(fp),
            column_mapping=column_mapping,
            identifier_nick=identifier_nick,
            page_position_column_name=page_position_column_name
        )

    if not all(reconciliation_args):
        # If no reconciliation args, just transpose the CSV to Catcher JSON
        catcher_data = cdm_collection_from_rows
    else:
        try:
            catcher_data = reconcile_cdm_collection(
                cdm_collection=cdm_collection_from_rows,
                repository_url=repository_url,
                collection_alias=collection_alias,
                identifier_nick=identifier_nick,
                match_mode=match_mode
            )
        except (ValueError, KeyError) as err:
            print(f"Reconciliation failure: {err}")
            sys.exit(1)

    with open(args.output_file, mode='w', encoding="utf-8") as fp:
        json.dump(serialize_cdm_objects(catcher_data), fp, indent=2)


if __name__ == '__main__':
    main()
