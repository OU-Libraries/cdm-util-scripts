import json
import argparse
from typing import Dict, Any, Iterator, Tuple, Iterable, List

import requests

from ftp2catcher import get_ftp_manifest, get_ftp_transcript


def iter_manifest_sequence(manifest: Dict[str, Any], transcript_type: str) -> Iterator[Tuple[str, str]]:
    for canvas in manifest["sequences"][0]["canvases"]:
        dmrecord = canvas["@id"].split("/")[-3]
        url = [seeAlso["@id"] for seeAlso in canvas["seeAlso"] if seeAlso["label"] == transcript_type][0]
        yield dmrecord, url


def get_manifest_catcher_edits(manifest: Dict[str, Any], transcript_nick: str, transcript_type: str, session: requests.Session) -> List[Dict[str, str]]:
    catcher_edits = []
    for dmrecord, url in iter_manifest_sequence(
            manifest=manifest,
            transcript_type=transcript_type
    ):
        print(f"Requesting {url!r}...")
        transcript_text = get_ftp_transcript(url=url, session=session)
        catcher_edits.append({
            "dmrecord": dmrecord,
            transcript_nick: transcript_text.strip(),
        })
    return catcher_edits


def get_manifests_catcher_edits(manifest_urls: Iterable[str], transcript_nick: str, transcript_type: str, session: requests.Session) -> List[Dict[str, str]]:
    catcher_edits = []
    for manifest_url in manifest_urls:
        print(f"Requesting {manifest_url!r}...")
        manifest = get_ftp_manifest(manifest_url, session)
        catcher_edits.extend(
            get_manifest_catcher_edits(
                manifest=manifest,
                transcript_nick=transcript_nick,
                transcript_type=transcript_type,
                session=session
            )
        )
    return catcher_edits


def main():
    parser = argparse.ArgumentParser(
        description="",
    )
    parser.add_argument(
        "manifests_listing_path",
        type=str,
        help="Path to file listing FromThePage manifest links",
    )
    parser.add_argument(
        "transcript_nick",
        type=str,
        help="CONTENTdm field nickname for the transcript field",
    )
    parser.add_argument(
        "output_file",
        type=str,
        help="Path to write cdm-catcher JSON file",
    )
    parser.add_argument(
        "--transcript_type",
        type=str,
        default="Verbatium Plaintext",
        help="FromThePage transcript type",
    )
    args = parser.parse_args()

    with open(args.manifests_listing_path, mode="r", encoding="utf-8") as fp:
        manifest_urls = [line.strip() for line in fp.readlines()]

    with requests.Session() as session:
        catcher_edits = get_manifests_catcher_edits(
            manifest_urls=manifest_urls,
            transcript_nick=args.transcript_nick,
            transcript_type=args.transcript_type,
            session=session
        )

    print("Writing JSON file...")
    with open(args.output_file, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp, indent=2)


if __name__ == "__main__":
    main()
