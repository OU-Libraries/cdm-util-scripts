import requests

import argparse

from cdm_util_scripts.printcdminfo import print_as_records
from cdm_util_scripts.ftp_api import get_slug_collections


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print FromThePage project information"
    )
    parser.add_argument("slug", type=str, help="FromThePage user slug")
    args = parser.parse_args()

    with requests.Session() as session:
        collections = get_slug_collections(slug=args.slug, session=session)

    print_as_records(collections["collections"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
