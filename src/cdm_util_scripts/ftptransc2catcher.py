import requests
import tqdm

import json

from cdm_util_scripts import ftp_api


def ftptransc2catcher(
    manifests_listing_path: str,
    transcript_nick: str,
    output_file_path: str,
    transcript_type: str,
    show_progress: bool = True,
) -> None:
    """Get transcripts from a list of FromThePage manifests as cdm-catcher JSON edits"""
    progress_bar = tqdm.tqdm if show_progress else (lambda obj: obj)
    with open(manifests_listing_path, mode="r", encoding="utf-8") as fp:
        manifest_urls = [line.strip() for line in fp.readlines()]

    with requests.Session() as session:
        catcher_edits = []
        for manifest_url in progress_bar(manifest_urls):
            ftp_work = ftp_api.FtpWork.from_url(manifest_url, session=session)
            for ftp_page in ftp_work.pages:
                catcher_edits.append(
                    {
                        "dmrecord": ftp_page.cdm_page_dmrecord,
                        transcript_nick: ftp_page.request_transcript(
                            label=transcript_type,
                            session=session,
                        ),
                    }
                )

    print("Writing JSON file...")
    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_edits, fp, indent=2)
