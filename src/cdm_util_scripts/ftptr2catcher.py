import re
import json
import argparse
from typing import Dict, Any, Iterator, Tuple, Iterable, List, Optional

import requests
from rich.progress import track

from cdm_util_scripts import ftp_api


def parse_canvas_id(url: str) -> Tuple[str, str]:
    match = re.search(r"/iiif/([A-Za-z0-9\-]+)[:/](\d+)/canvas/c\d+$", url)
    if match:
        return match.groups()
    raise ValueError(f"Couldn't parse URL {url!r}")


def iter_manifest_sequence(
    manifest: Dict[str, Any], transcript_type: str
) -> Iterator[Tuple[str, str]]:
    for canvas in manifest["sequences"][0]["canvases"]:
        _, dmrecord = parse_canvas_id(canvas["@id"])
        url = [
            seeAlso["@id"]
            for seeAlso in canvas["seeAlso"]
            if seeAlso["label"] == transcript_type
        ]
        if not url:
            raise ValueError(f"transcript type {transcript_type!r} not found")
        yield dmrecord, url[0]


def get_manifest_catcher_edits(
    manifest: Dict[str, Any],
    transcript_nick: str,
    transcript_type: str,
    session: requests.Session,
) -> List[Dict[str, str]]:
    catcher_edits = []
    for dmrecord, url in track(
        list(iter_manifest_sequence(manifest=manifest, transcript_type=transcript_type)),
        description=f"Requesting {transcript_type!r} transcripts...",
    ):
        transcript_text = ftp_api.get_ftp_transcript(url=url, session=session)
        catcher_edits.append(
            {
                "dmrecord": dmrecord,
                transcript_nick: transcript_text.strip(),
            }
        )
    return catcher_edits


def get_manifests_catcher_edits(
    manifest_urls: Iterable[str],
    transcript_nick: str,
    transcript_type: str,
    session: requests.Session,
) -> List[Dict[str, str]]:
    catcher_edits = []
    for manifest_url in manifest_urls:
        print(f"Requesting {manifest_url!r}...")
        manifest = ftp_api.get_ftp_manifest(manifest_url, session)
        catcher_edits.extend(
            get_manifest_catcher_edits(
                manifest=manifest,
                transcript_nick=transcript_nick,
                transcript_type=transcript_type,
                session=session,
            )
        )
    return catcher_edits


def main(test_args: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Get transcripts from a list of FromThePage manuscripts in cdm-catcher JSON format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        default="Verbatim Plaintext",
        help="FromThePage transcript type",
    )
    args = parser.parse_args(test_args)

    with open(args.manifests_listing_path, mode="r", encoding="utf-8") as fp:
        manifest_urls = [line.strip() for line in fp.readlines()]

    with requests.Session() as session:
        catcher_edits = get_manifests_catcher_edits(
            manifest_urls=manifest_urls,
            transcript_nick=args.transcript_nick,
            transcript_type=args.transcript_type,
            session=session,
        )

    print("Writing JSON file...")
    with open(args.output_file, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp, indent=2)
    print("Done.")


if __name__ == "__main__":
    main()
