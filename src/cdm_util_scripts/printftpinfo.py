import argparse

from requests import Session

from cdm_util_scripts.printcdminfo import print_as_table
from cdm_util_scripts.ftp_api import get_slug_collections


def main():
    parser = argparse.ArgumentParser(description="Print FromThePage project information")
    parser.add_argument(
        'slug',
        type=str,
        help="FromThePage user slug"
    )
    args = parser.parse_args()
    with Session() as session:
        collections = get_slug_collections(slug=args.slug, session=session)
    print_as_table(collections['collections'])
