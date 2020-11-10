import requests

import json
import csv
import argparse
import sys
from dataclasses import dataclass
from collections import defaultdict
from itertools import count

from ftp2catcher import get_cdm_page_pointers

from typing import List, Optional, Dict, Sequence


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


def request_cdm_collection_object_records(repo_url: str,
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


def build_cdm_collection_from_records(cdm_records: List[dict], identifier_nick: str) -> List[CdmObject]:
    return [CdmObject(pointer=record['pointer'],
                      identifier=record[identifier_nick],
                      is_cpd=record['find'].endswith('.cpd')) for record in cdm_records]


def request_collection_page_pointers(cdm_collection: Sequence[CdmObject],
                                     repo_url: str,
                                     alias: str,
                                     session: requests.Session,
                                     verbose: bool = True) -> None:
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


def cdm_object_from_row(row: dict,
                        column_mapping: dict,
                        identifier_nick: Optional[str]) -> CdmObject:
    fields = {nick: row[name] for name, nick in column_mapping.items()}
    identifier = fields.pop(identifier_nick) if identifier_nick else None
    return CdmObject(identifier=identifier,
                     page_position=int(row['Page Position']),
                     fields=fields)


def build_cdm_collection_from_rows(rows: Sequence[dict],
                                   column_mapping: dict,
                                   identifier_nick: Optional[str]) -> List[CdmObject]:
    return [cdm_object_from_row(row=row,
                                column_mapping=column_mapping,
                                identifier_nick=identifier_nick)
            for row in rows]


def build_identifier_to_object_index(cdm_collection: List[CdmObject]) -> Dict[str, List[CdmObject]]:
    cdm_index = defaultdict(list)
    for cdm_object in cdm_collection:
        cdm_index[cdm_object.identifier].append(cdm_object)
    return dict(cdm_index)


def reconcile_indexes_by_object(objects_index: Dict[str, List[CdmObject]],
                                pages_index: Dict[str, List[CdmObject]],
                                page_position: int) -> List[CdmObject]:
    reconciled = []
    for identifier, pages in pages_index.items():
        position_matches = [page for page in pages if page.page_position == page_position]
        if len(position_matches) == 0:
            raise ValueError(f"missing page at position {page_position} for identifier {identifier!r}")
        if len(position_matches) > 1:
            raise ValueError(f"page position collision on {page_position} for {identifier!r}")
        for cdm_object in objects_index[identifier]:
            reconciled.append(cdm_object + position_matches[0])
    return reconciled


def reconcile_indexes_by_page(objects_index: Dict[str, List[CdmObject]],
                              pages_index: Dict[str, List[CdmObject]]) -> List[dict]:
    reconciled = []
    for identifier, pages in pages_index.items():
        for page in pages:
            for cdm_object in objects_index[identifier]:
                reconciled.append(
                    page + CdmObject(pointer=cdm_object.page_pointers[page.page_position - 1])
                )
    return reconciled


def serialize_cdm_objects(cdm_objects: Sequence[CdmObject]) -> List[dict]:
    series = []
    for cdm_object in cdm_objects:
        fields = cdm_object.fields.copy()
        if cdm_object.pointer:
            fields['dmrecord'] = cdm_object.pointer
        series.append(fields)
    return series


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
        cdm_collection_from_rows = build_cdm_collection_from_rows(
            rows=csv.DictReader(fp),
            column_mapping=column_mapping,
            identifier_nick=args.identifier_nick
        )

    if all(reconciliation_args):
        row_object_index = build_identifier_to_object_index(cdm_collection_from_rows)
        with requests.Session() as session:
            cdm_records = request_cdm_collection_object_records(
                repo_url=args.repository_url,
                alias=args.collection_alias,
                field_nicks=[args.identifier_nick],
                session=session
            )
            cdm_collection_from_records = build_cdm_collection_from_records(
                cdm_records=cdm_records,
                identifier_nick=args.identifier_nick
            )
            cdm_collection_from_records = [cdm_object for cdm_object in cdm_collection_from_records
                                           if cdm_object.identifier in row_object_index]
            if args.object_page:
                request_collection_page_pointers(cdm_collection=cdm_collection_from_records,
                                                 repo_url=args.repo_url,
                                                 alias=args.alias,
                                                 session=session)
        record_object_index = build_identifier_to_object_index(cdm_collection_from_records)
        unreconcilable_identifiers = [identifier for identifier in row_object_index.keys()
                                      if identifier not in record_object_index]
        multiple_identifiers = [identifier for identifier, cdm_objects in record_object_index.items()
                                if len(cdm_objects) > 1]
        if unreconcilable_identifiers or multiple_identifiers:
            for identifier in unreconcilable_identifiers:
                print(f"Couldn't find {identifier!r} in field {args.identifier_nick!r}")
            for identifier in multiple_identifiers:
                print(f"Multiple results for {identifier!r} in field {args.identifier_nick!r}")
            sys.exit()
        elif args.object_page:
            catcher_data = reconcile_indexes_by_object(
                objects_index=record_object_index,
                pages_index=row_object_index,
                page_position=args.object_page
            )
        else:
            catcher_data = reconcile_indexes_by_page(
                objects_index=record_object_index,
                pages_index=row_object_index
            )
    else:
        catcher_data = cdm_collection_from_rows

    with open(args.output_file, mode='w') as fp:
        json.dump(serialize_cdm_objects(catcher_data), fp, indent=2)


if __name__ == '__main__':
    main()
