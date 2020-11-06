import requests

import json
import csv
import argparse
from dataclasses import dataclass
from collections import defaultdict
from itertools import count

from ftp2catcher import get_cdm_page_pointers

from typing import List, Optional, Dict, Sequence, Any


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


def get_cdm_collection_object_records(repo_url: str,
                                      alias: str,
                                      field_nicks: Sequence[str],
                                      session: requests.Session) -> List[dict]:
    cdm_records = []
    total = 1
    start = 1
    maxrecs = 1024
    while len(cdm_records) < total:
        response = session.get(f"{repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmQuery/{alias}/CISOSEARCHALL/{'!'.join(field_nicks)}/pointer/{maxrecs}/{start}/1/0/0/0/0/1/json")
        response.raise_for_status()
        dmQuery = response.json()
        total = int(dmQuery['pager']['total'])
        start += maxrecs
        cdm_records += dmQuery['records']
    return cdm_records


def build_identifier_to_object_pointer_index(cdm_records: List[dict], identifier_nick: str) -> Dict[str, CdmObject]:
    identifier_index = dict()
    for record in cdm_records:
        identifier = record[identifier_nick]
        if identifier in identifier_index:
            raise KeyError(f"{identifier!r} duplicated")
        identifier_index[identifier] = CdmObject(pointer=record['pointer'],
                                                 identifier=identifier,
                                                 is_cpd=record['find'].endswith('.cpd'))
    return identifier_index


def build_identifier_to_object_and_page_pointer_index(repo_url: str,
                                                      alias: str,
                                                      identifier_to_object_pointer_index: Dict[str, CdmObject],
                                                      session: requests.Session,
                                                      verbose: bool = True) -> Dict[str, CdmObject]:
    if verbose:
        total_cpd = sum(1 if o.is_cpd else 0 for o in identifier_to_object_pointer_index.values())
        request_count = count(1)
    object_and_page_pointer_index = dict()
    for identifier, cdm_object in identifier_to_object_pointer_index.items():
        if cdm_object.is_cpd:
            if verbose:
                n = next(request_count)
                print(f"Requesting page pointers: {n}/{total_cpd} {(n // total_cpd) * 100}%",
                      end='\r',
                      flush=True)
            page_pointers = get_cdm_page_pointers(
                repo_url=repo_url,
                alias=alias,
                dmrecord=cdm_object.pointer,
                session=session
            )
        else:
            page_pointers = None
        verbose and print(end='\n')
        object_and_page_pointer_index[identifier] = cdm_object + CdmObject(page_pointers=page_pointers)
    return object_and_page_pointer_index


def build_cdm_collection_from_rows(rows: Sequence[dict],
                                   column_mapping: dict,
                                   identifier_nick: Optional[str] = None) -> List[CdmObject]:
    return [cdm_object_from_row(row=row,
                                column_mapping=column_mapping,
                                identifier_nick=identifier_nick)
            for row in rows]


def cdm_object_from_row(row: dict,
                        column_mapping: dict,
                        identifier_nick: Optional[str] = None) -> CdmObject:
    fields = {nick: row[name] for name, nick in column_mapping.items()}
    return CdmObject(identifier=fields[identifier_nick] if identifier_nick else None,
                     page_position=int(row['Page Position']),
                     fields=fields)


def build_identifier_to_object_index(cdm_collection: List[CdmObject]) -> Dict[str, List[CdmObject]]:
    cdm_index = defaultdict(list)
    for cdm_object in cdm_collection:
        cdm_index[cdm_object.identifier].append(cdm_object)
    for entry in cdm_index.values():
        entry.sort(key=lambda cdm_object: cdm_object.page_position)
    return cdm_index


def reconcile_indexes_by_object(identifier_to_object_index: Dict[str, List[CdmObject]],
                                identifier_to_object_pointer_index: Dict[str, CdmObject],
                                object_page: int) -> List[CdmObject]:
    reconciled = []
    for identifier, cdm_object_pointer in identifier_to_object_pointer_index.items():
        cdm_object_fields = identifier_to_object_index[identifier][object_page - 1]
        reconciled.append(cdm_object_pointer + cdm_object_fields)
    return reconciled


def reconcile_indexes_by_page(identifier_to_object_index: Dict[str, List[CdmObject]],
                              identifier_to_object_and_page_pointer_index: Dict[str, CdmObject]) -> List[dict]:
    reconciled = []
    for identifier, cdm_object_pointer in identifier_to_object_and_page_pointer_index.items():
        for pointer, cdm_object in zip(cdm_object_pointer.page_pointers, identifier_to_object_index[identifier]):
            reconciled.append(cdm_object + CdmObject(pointer=pointer))


def serialize_cdm_objects(cdm_objects: Sequence[CdmObject]) -> List[dict]:
    return [{'dmrecord': cdm_object.pointer, **cdm_object.fields} for cdm_object in cdm_objects]


def main():
    parser = argparse.ArgumentParser(description="Render a FromThePage All Table Data as cdm-catcher JSON",
                                     fromfile_prefix_chars='@')
    parser.add_argument('column_mapping_file',
                        type=str,
                        help="Path to CSV with columns 'name' and 'nick' mapping column names to CONTENTdm field nicknames")
    parser.add_argument('ftp_all_table_data',
                        type=str,
                        help="Path to FromThePage All Table Data CSV")
    parser.add_argument('output_file',
                        type=str,
                        help="Path to output cdm-catcher JSON")
    parser.add_argument('--repository_url',
                        type=str,
                        action='store',
                        help="CONTENTdm repository URL")
    parser.add_argument('--collection_alias',
                        type=str,
                        action='store',
                        help="CONTENTdm collection alias")
    parser.add_argument('--identifier_nick',
                        type=str,
                        action='store',
                        help="Column name to use as a search field to get dmrecord numbers")
    parser.add_argument('--object_page',
                        type=int,
                        action='store',
                        help="Page number to be used as object metadata (e.g. 1)")
    args = parser.parse_args()

    reconciliation_args = (args.identifier_nick, args.repository_url, args.collection_alias)
    if any(reconciliation_args) and not all(reconciliation_args):
        raise ValueError("All of repository_url, collection_alias and key_nick must be specified for reconciliation")

    with open(args.column_mapping_file, mode='r') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            raise ValueError("Column mapping file must have 'name' and 'nick' column titles in that order")
        column_mapping = {row['name']: row['nick'] for row in reader}

    with open(args.ftp_all_table_data, mode='r') as fp:
        cdm_collection = build_cdm_collection_from_rows(
            rows=csv.DictReader(fp),
            column_mapping=column_mapping,
            identifier_nick=args.identifier_nick
        )

    if all(reconciliation_args):
        identifier_to_object_index = build_identifier_to_object_index(cdm_collection)
        with requests.Session() as session:
            cdm_records = get_cdm_collection_object_records(
                repo_url=args.repository_url,
                alias=args.collection_alias,
                session=session
            )
            identifier_to_object_pointer_index = build_identifier_to_object_pointer_index(
                records=cdm_records,
                identifier_nick=args.identifier_nick
            )
            if args.object_page:
                reduced_identifier_to_object_pointer_index = {identifier: identifier_to_object_pointer_index[identifier]
                                                              for identifier in identifier_to_object_index.keys()}
                identifier_to_object_and_page_pointer_index = build_identifier_to_object_and_page_pointer_index(
                    repo_url=args.repository_url,
                    alias=args.collection_alias,
                    identifier_to_object_pointer_index=reduced_identifier_to_object_pointer_index,
                    session=session
                )
        if args.object_page:
            catcher_data = reconcile_indexes_by_object(
                identifier_to_object_index=identifier_to_object_index,
                identifier_to_object_pointer_index=identifier_to_object_pointer_index,
                object_page=args.object_page
            )
        else:
            catcher_data = reconcile_indexes_by_page(
                identifier_to_object_index=identifier_to_object_index,
                identifier_to_object_and_page_pointer_index=identifier_to_object_and_page_pointer_index
            )

    with open(args.output_file, mode='w') as fp:
        json.dump(serialize_cdm_objects(catcher_data), fp, indent=2)


if __name__ == '__main__':
    main()
