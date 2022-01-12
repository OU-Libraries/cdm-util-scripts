from requests import Session

import argparse

from cdm_util_scripts.printcdminfo import print_as_table


def get_slug_collections(slug: str, session: Session) -> dict:
    response = session.get(f"https://fromthepage.com/iiif/collections/{slug}")
    response.raise_for_status()
    return response.json()


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
