import requests

import json
import csv
import argparse
from dataclasses import dataclass
from itertools import count

from typing import List, Optional


@dataclass
class CdmObject:
    pointer: str
    identifier: str
    is_cpd: bool
    page_pointers: Optional[List[str]] = None


def get_cdm_collection(repo_url: str,
                       alias: str,
                       id_field_nick: str,
                       session: requests.Session,
                       page_data: bool = True) -> List[CdmObject]:
    cdm_collection = []
    total = 1
    while len(cdm_collection) < total:
        response = session.get(f"{repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmQuery/{alias}/CISOSEARCHALL/dmrecord!{id_field_nick}/dmrecord/1024/0/1/0/0/0/0/1/json")
        response.raise_for_status()
        dmQuery = response.json()
        total = int(dmQuery['pager']['total'])
        cdm_collection += [CdmObject(pointer=record['dmrecord'],
                                     identifier=record[id_field_nick],
                                     is_cpd=record['find'].endswith('.cpd'))
                           for record in dmQuery['records']]
    cpd_total = sum([1 if o.is_cpd else 0 for o in cdm_collection])
    print(f"Found {total} records in {alias}, {cpd_total} objects")
    cpd_count = count(1)
    if page_data:
        for cdm_object in cdm_collection:
            if cdm_object.is_cpd:
                n = next(cpd_count)
                print(f"Fetching compound object structures: {n}/{cpd_total} {(n // cpd_total) * 100}%", end='\r', flush=True)
                cdm_object.page_pointers = get_cdm_page_pointers(repo_url=repo_url,
                                                                 alias=alias,
                                                                 dmrecord=cdm_object.pointer,
                                                                 session=session)
    return cdm_collection


def get_cdm_page_pointers(repo_url: str, alias: str, dmrecord: str, session: requests.Session) -> List[str]:
    response = session.get(f"{repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmGetCompoundObjectInfo/{alias}/{dmrecord}/json")
    response.raise_for_status()
    dmGetCompoundObjectInfo = response.json()
    if 'code' in dmGetCompoundObjectInfo:
        raise ValueError(f"CONTENTdm error {dmGetCompoundObjectInfo['message']!r}")
    # print(f"Found {len(dmGetCompoundObjectInfo)} pages in {dmrecord!r} of type {dmGetCompoundObjectInfo['type']}", flush=True)
    return [page['pageptr'] for page in dmGetCompoundObjectInfo['page']]


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
    parser.add_argument('--key_nick',
                        type=str,
                        action='store',
                        help="Column name to use as a search field to get dmrecord numbers")
    parser.add_argument('--object_page',
                        type=int,
                        action='store',
                        help="Page number to be used as object metadata (e.g. 1)")
    args = parser.parse_args()

    reconciliation_args = (args.key_nick, args.repository_url, args.collection_alias)
    if any(reconciliation_args) and not all(reconciliation_args):
        raise ValueError("All of repository_url, collection_alias and key_nick must be specified for reconciliation")

    with open(args.column_mapping_file, mode='r') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            raise ValueError("Column mapping file must have 'name' and 'nick' column titles in that order")
        name_nick_map = {row['name']: row['nick'] for row in reader}

    with open(args.ftp_all_table_data, mode='r') as fp:
        catcher_records = [{nick: row[name] for name, nick in name_nick_map.items()}
                           for row in csv.DictReader(fp)]

    if all(reconciliation_args):
        with requests.Session() as session:
            cdm_collection = get_cdm_collection(
                repo_url=args.repository_url,
                alias=args.collection_alias,
                id_field_nick=args.key_nick,
                session=session,
                page_data=False if args.object_page else True
            )
            cdm_index = dict()
            for cdm_object in cdm_collection:
                if cdm_object.identifier in cdm_index:
                    raise ValueError(f"{cdm_object.identifier} not unique in collection")
                cdm_index[cdm_object.identifier] = cdm_object
            if args.object_page:
                cdm_catcher_json = [{'dmrecord': cdm_index[record[args.key_nick]].pointer, **record}
                                    for record in catcher_records
                                    if int(record['Page Position']) == args.object_page]
            else:
                cdm_catcher_json = []
                for record in catcher_records:
                    cdm_object = cdm_index[record[args.key_nick]]
                    cdm_catcher_json.append({
                        'dmrecord': (cdm_object.page_pointers[int(record['Page Position']) - 1]
                                     if cdm_object.is_cpd else cdm_object.pointer),
                        **record
                    })

    with open(args.output_file, mode='w') as fp:
        json.dump(cdm_catcher_json, fp, indent=2)


if __name__ == '__main__':
    main()
