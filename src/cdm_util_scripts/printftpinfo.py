import requests

import argparse

from cdm_util_scripts import ftp_api


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print FromThePage project information"
    )
    parser.add_argument("slug", type=str, help="FromThePage user slug")
    args = parser.parse_args()

    with requests.Session() as session:
        ftp_instance = ftp_api.FtpInstance(base_url=ftp_api.FTP_HOSTED_BASE_URL)
        ftp_projects = ftp_instance.request_projects(slug=args.slug, session=session)

    for label, url in ftp_projects.projects.items():
        print(repr(label))
        print(url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
