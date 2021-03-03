import pytest

from datetime import datetime

from ftpfields2catcher import FTPCollection, FTPWork, FTPPage
import scanftpvocabs


def test_scan_vocabs():
    ftp_collection = FTPCollection(
        works=[FTPWork(pages=[FTPPage(fields={
            'FtP vocab label': 'controlled-term; uncontrolled-term',
            'FtP TGM label': 'Paddleboats; NotInTGM',
        })])]
    )
    field_mapping = {
        'FtP vocab label': ['nickv'],
        'FtP TGM label': ['nickdb']
    }
    vocabs_index = {
        'nickv': {'type': 'vocab', 'name': 'nickv'},
        'nickdb': {'type': 'vocdb', 'name': 'LCTGM'}
    }
    vocabs = {
        'vocab': {'nickv': ['controlled-term']},
        'vocdb': {'LCTGM': ['Paddleboats']}
    }
    field_scans = scanftpvocabs.scan_vocabs(
        ftp_collection=ftp_collection,
        field_mapping=field_mapping,
        vocabs_index=vocabs_index,
        vocabs=vocabs
    )
    assert 'uncontrolled-term' in field_scans['nickv']
    assert 'NotInTGM' in field_scans['nickdb']


def test_report_to_html():
    report = scanftpvocabs.report_to_html({
        'ftp_slug': 'slug',
        'ftp_project_name': 'project name',
        'cdm_repo_url': 'repo url',
        'cdm_collection_alias': 'collection alias',
        'field_mapping_csv': 'field_mapping_csv.csv',
        'output': 'html',
        'label': 'XHTML Export',
        'report_date': datetime.now().isoformat(),
        'cdm_fields_info': [{'name': 'Name', 'nick': 'nick', 'vocab': 1}],
        'field_mapping': {
            'FtP vocab label': ['nickv'],
            'FtP TGM label': ['nickdb']
        },
        'field_scans': {'nick': {'uncontrolled-term': [FTPPage(display_url='', label='', transcription_url='')]}},
        'vocabs_index': {'nick': {'type': 'vocab', 'name': 'nick'}},
        'vocabs': {'vocab': {'nick': ['controlled_term']}, 'vocdb': {}},
        'cdm_nick_to_name': {'nick': 'Name'},
    })
    assert report
