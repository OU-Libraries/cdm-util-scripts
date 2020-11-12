import requests

import json
import csv
import argparse
import sys
from dataclasses import dataclass
from collections import defaultdict
from itertools import count

from ftp2catcher import get_cdm_page_pointers

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


def csv_dict_reader_with_join(fp: TextIO, seperator: str = '; ') -> Iterator[Dict[str, str]]:
    reader = csv.reader(fp)
    header = next(reader)
    for csv_row in reader:
        row = dict()
        for column_name, cell in zip(header, csv_row):
            row[column_name] = seperator.join([row[column_name], cell]) if column_name in row else cell
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
        print("Requesting object pointers: ", end='')
    while len(cdm_records) < total:
        response = session.get(f"{repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmQuery/{alias}/CISOSEARCHALL/{'!'.join(field_nicks)}/pointer/{maxrecs}/{start}/1/0/0/0/0/1/json")
        response.raise_for_status()
        dmQuery = response.json()
        total = int(dmQuery['pager']['total'])
        start += maxrecs
        cdm_records += dmQuery['records']
        if verbose:
            print(f"{len(cdm_records)}/{total}... ",
                  end='',
                  flush=True)
    print("Done")
    return cdm_records


def build_cdm_collection_from_records(cdm_records: List[dict], identifier_nick: str) -> List[CdmObject]:
    return [CdmObject(pointer=str(record['pointer']),
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
                print(f"Requesting page pointers: {n}/{total_cpd} {(n / total_cpd) * 100:2.0f}%... ",
                      end='\r',
                      flush=True)
            cdm_object.page_pointers = get_cdm_page_pointers(
                repo_url=repo_url,
                alias=alias,
                dmrecord=cdm_object.pointer,
                session=session
            )
    if verbose:
        print("Done")


def cdm_object_from_row(row: dict,
                        column_mapping: dict,
                        identifier_nick: Optional[str]) -> CdmObject:
    fields = dict()
    for name, nick in column_mapping.items():
        fields[nick] = '; '.join([fields[nick], row[name]]) if nick in fields else row[name]
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


def main():
    parser = argparse.ArgumentParser(description="Render a FromThePage All Table Data as cdm-catcher JSON",
                                     fromfile_prefix_chars='@')
    parser.add_argument('column_mapping_csv',
                        type=str,
                        help="Path to CSV with columns 'name' and 'nick' mapping column names to CONTENTdm field nicknames")
    parser.add_argument('ftp_all_table_csv',
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
    parser.add_argument('--match_mode',
                        type=str,
                        action='store',
                        default='page',
                        help="Match CSV rows to 'page' level metadata or 'object' level metadata, default 'page'")
    args = parser.parse_args()

    reconciliation_args = (args.identifier_nick, args.repository_url, args.collection_alias)
    if any(reconciliation_args) and not all(reconciliation_args):
        print("All of --repository_url, --collection_alias and --identifier_nick must be specified for reconciliation")
        sys.exit()

    if args.match_mode not in ('page', 'object'):
        print(f"Unknown --match_mode value {args.match_mode!r}")
        sys.exit()

    with open(args.column_mapping_csv, mode='r') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            print("Column mapping CSV must have 'name' and 'nick' column titles in that order")
            sys.exit()
        column_mapping = {row['name']: row['nick'] for row in reader}

    with open(args.ftp_all_table_csv, mode='r') as fp:
        cdm_collection_from_rows = build_cdm_collection_from_rows(
            rows=csv_dict_reader_with_join(fp),
            column_mapping=column_mapping,
            identifier_nick=args.identifier_nick
        )

    if not all(reconciliation_args):
        # If no reconciliation args, transpose the CSV to Catcher JSON without dmrecord pointers
        catcher_data = cdm_collection_from_rows
    else:
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

            # Drop unneeded record objects to keep page pointer requests to the minimum
            cdm_collection_from_records = [cdm_object for cdm_object in cdm_collection_from_records
                                           if cdm_object.identifier in row_object_index]
            if args.match_mode == 'page':
                request_collection_page_pointers(
                    cdm_collection=cdm_collection_from_records,
                    repo_url=args.repository_url,
                    alias=args.collection_alias,
                    session=session
                )
        record_object_index = build_identifier_to_object_index(cdm_collection_from_records)

        # Are there rows in the FtP CSV for which CONTENTdm objects could not be found?
        unreconcilable_row_identifiers = [identifier for identifier in row_object_index.keys()
                                          if identifier not in record_object_index]

        # Are there multiple CONTENTdm objects with the same identifier?
        confused_cdm_identifiers = [identifier for identifier, cdm_objects in record_object_index.items()
                                    if len(cdm_objects) > 1]

        if unreconcilable_row_identifiers or confused_cdm_identifiers:
            for identifier in unreconcilable_row_identifiers:
                print(f"Couldn't find {identifier!r} in field {args.identifier_nick!r}")
            for identifier in confused_cdm_identifiers:
                print(f"Multiple results for {identifier!r} in field {args.identifier_nick!r}")
            sys.exit()
        elif args.match_mode == 'object':
            catcher_data = reconcile_indexes_by_object(
                records_index=record_object_index,
                rows_index=row_object_index
            )
        elif args.match_mode == 'page':
            catcher_data = reconcile_indexes_by_page(
                records_index=record_object_index,
                rows_index=row_object_index
            )
        else:
            print(f"Unknown --match_mode {args.match_mode!r}")
            sys.exit()

    with open(args.output_file, mode='w') as fp:
        json.dump(serialize_cdm_objects(catcher_data), fp, indent=2)


if __name__ == '__main__':
    main()
