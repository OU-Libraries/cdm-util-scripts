import argparse
import sys
import csv
import json
from collections import defaultdict

from requests import Session

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api

from typing import Optional, List, Iterable, Dict, Sequence, Callable, Tuple


def get_field_mapping(filename: str) -> Dict[str, List[str]]:
    with open(filename, mode='r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            raise ValueError("column mapping CSV must have 'name' and 'nick' column titles in that order")
        field_mapping = defaultdict(list)
        for row in reader:
            field_mapping[row['name']].append(row['nick'].strip())
    return dict(field_mapping)


def apply_field_mapping(ftp_fields: Dict[str, str], field_mapping: Dict[str, Sequence[str]]) -> Dict[str, str]:
    accumulator = dict()
    for label, nicks in field_mapping.items():
        ftp_field = ftp_fields[label]
        for nick in nicks:
            if nick in accumulator:
                if ftp_field:
                    if accumulator[nick]:
                        accumulator[nick] = '; '.join([
                            accumulator[nick],
                            ftp_field
                        ])
                    else:
                        accumulator[nick] = ftp_field
            else:
                accumulator[nick] = ftp_field
    return accumulator


def map_ftp_work_as_cdm_object(
        ftp_work: ftp_api.FTPWork,
        field_mapping: Dict[str, Sequence[str]],
        page_picker: Callable[[List[ftp_api.FTPPage]], Optional[ftp_api.FTPPage]]
) -> Optional[Dict[str, str]]:
    object_page = page_picker(ftp_work.pages)
    if not object_page:
        return None
    return {
        'dmrecord': ftp_work.dmrecord,
        **apply_field_mapping(object_page.fields,
                              field_mapping)
    }


def map_ftp_works_as_cdm_objects(
        ftp_works: Iterable[ftp_api.FTPWork],
        field_mapping: Dict[str, Sequence[str]],
        page_picker: Callable[[List[Dict[str, str]]], Dict[str, str]],
        verbose: bool = True
) -> Tuple[List[Dict[str, str]], List[ftp_api.FTPWork]]:
    catcher_data = []
    dropped_works = []
    for ftp_work in ftp_works:
        if verbose:
            print(f"Mapping FromThePage data {len(catcher_data)+1}/{len(ftp_works)}...", end='\r')
        cdm_object = map_ftp_work_as_cdm_object(
            ftp_work=ftp_work,
            field_mapping=field_mapping,
            page_picker=page_picker
        )
        if cdm_object:
            catcher_data.append(cdm_object)
        else:
            dropped_works.append(ftp_work)
    if verbose:
        print(end='\n')
    return catcher_data, dropped_works


class PagePickers:

    @staticmethod
    def first_page(pages: List[ftp_api.FTPPage]) -> Optional[ftp_api.FTPPage]:
        if pages:
            return pages[0]
        return None

    @staticmethod
    def first_filled_page(pages: List[ftp_api.FTPPage]) -> Optional[ftp_api.FTPPage]:
        for page in pages:
            if page.fields and any(page.fields.values()):
                return page
        return None


def get_ftp_work_cdm_item_info(ftp_work: ftp_api.FTPWork, session: Session) -> Dict[str, str]:
    return cdm_api.get_cdm_item_info(
        cdm_repo_url=ftp_work.cdm_repo_url,
        cdm_collection_alias=ftp_work.cdm_collection_alias,
        dmrecord=ftp_work.dmrecord,
        session=session
    )


def load_cdm_page_pointers(ftp_work: ftp_api.FTPWork, session: Session) -> None:
    page_pointers = cdm_api.get_cdm_page_pointers(
        repo_url=ftp_work.cdm_repo_url,
        alias=ftp_work.cdm_collection_alias,
        dmrecord=ftp_work.dmrecord,
        session=session
    )
    for page, pointer in zip(ftp_work.pages, page_pointers):
        page.dmrecord = pointer


def map_ftp_work_as_cdm_pages(
        ftp_work: ftp_api.FTPWork,
        field_mapping: Dict[str, Sequence[str]],
        session: Session
) -> List[Dict[str, str]]:
    if not any(page.fields for page in ftp_work.pages):
        return []
    item_info = get_ftp_work_cdm_item_info(ftp_work, session)
    if item_info['find'].endswith('.cpd'):
        load_cdm_page_pointers(ftp_work, session)
    else:
        # It's a simple object, the object is its own page
        ftp_work.pages[0].dmrecord = ftp_work.dmrecord
    page_data = []
    for page in ftp_work.pages:
        if page.fields:
            page_data.append({
                'dmrecord': page.dmrecord,
                **apply_field_mapping(ftp_fields=page.fields,
                                      field_mapping=field_mapping)
            })
    return page_data


def map_ftp_works_as_cdm_pages(
        ftp_works: Sequence[ftp_api.FTPWork],
        field_mapping: Dict[str, Sequence[str]],
        session: Session,
        verbose: bool = True
) -> Tuple[List[Dict[str, str]], List[ftp_api.FTPWork]]:
    catcher_data = []
    dropped_works = []
    for n, ftp_work in enumerate(ftp_works, start=1):
        if verbose:
            print(f"Requesting CONTENTdm page pointers and mapping FromThePage data {n}/{len(ftp_works)}", end='\r')
        pages = map_ftp_work_as_cdm_pages(
            ftp_work=ftp_work,
            field_mapping=field_mapping,
            session=session
        )
        if pages:
            catcher_data.extend(pages)
        else:
            dropped_works.append(ftp_works)
    if verbose:
        print(end='\n')
    return catcher_data, dropped_works


class MatchModes:
    by_object = 'object'
    by_page = 'page'


def main():
    parser = argparse.ArgumentParser(
        description="Get FromThePage metadata and map it into cdm-catcher JSON",
        fromfile_prefix_chars='@'
    )
    parser.add_argument(
        'match_mode',
        type=str,
        choices=[MatchModes.by_object, MatchModes.by_page],
        help="Mode for matching FromThePage metadata to CONTENTdm objects"
    )
    parser.add_argument(
        'slug',
        type=str,
        help="FromThePage user slug"
    )
    parser.add_argument(
        'collection_name',
        type=str,
        help="CONTENTdm collection name used by FromThePage"
    )
    parser.add_argument(
        'field_mapping_csv',
        type=str,
        help="CSV file of FromThePage field labels mapped to CONTENTdm nicknames"
    )
    parser.add_argument(
        'output_file',
        type=str,
        help="File name for cdm-catcher JSON output"
    )
    args = parser.parse_args()

    try:
        field_mapping = get_field_mapping(args.field_mapping_csv)
    except ValueError as err:
        print(f"{args.field_mapping_csv}: {err}")
        sys.exit(1)

    with Session() as session:
        try:
            ftp_collection = ftp_api.get_and_load_ftp_collection(
                slug=args.slug,
                collection_name=args.collection_name,
                rendering_label='XHTML Export',
                session=session
            )
        except KeyError as err:
            print(f"Error: {err}")
            sys.exit(1)

        if args.match_mode == MatchModes.by_object:
            catcher_data, dropped_works = map_ftp_works_as_cdm_objects(
                ftp_works=ftp_collection.works,
                field_mapping=field_mapping,
                page_picker=PagePickers.first_filled_page
            )
            print(f"Collected {len(catcher_data)} CONTENTdm object edits from {len(ftp_collection.works)} FromThePage works.")
        elif args.match_mode == MatchModes.by_page:
            catcher_data, dropped_works = map_ftp_works_as_cdm_pages(
                ftp_works=ftp_collection.works,
                field_mapping=field_mapping,
                session=session
            )
            print(f"Collected {len(catcher_data)} CONTENTdm page edits from {len(ftp_collection.works)} FromThePage works.")
        else:
            raise KeyError(f"invalid match mode {args.match_mode!r}")

    with open(args.output_file, mode='w', encoding='utf-8') as fp:
        json.dump(catcher_data, fp, indent=2)


if __name__ == '__main__':
    main()
