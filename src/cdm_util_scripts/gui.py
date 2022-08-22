import PySimpleGUI as sg
import requests

import csv
from pprint import pprint

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api
from cdm_util_scripts.catcherdiff import catcherdiff
from cdm_util_scripts.csv2catcher import csv2catcher
from cdm_util_scripts.csv2json import csv2json
from cdm_util_scripts.ftpfields2catcher import ftpfields2catcher, MatchModes
from cdm_util_scripts.ftptr2catcher import ftptr2catcher
from cdm_util_scripts.ftpmdc2catcher import ftpmdc2catcher
from cdm_util_scripts.scanftpvocabs import scanftpvocabs
from cdm_util_scripts.scanftpfields import scanftpfields


catcherdiff_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Generate a HTML report on what CONTENTdm field values will change if a cdm-catcher JSON edit is implemented"
                    )
                ]
            ],
        )
    ],
    [sg.Text("CONTENTdm instance URL")],
    [sg.InputText(key=(catcherdiff, "cdm_instance_url"))],
    [sg.Button("Request collection aliases", key=(catcherdiff, "-LOAD ALIASES-"))],
    [sg.Text("CONTENTdm collection alias")],
    [sg.Combo([], key=(catcherdiff, "cdm_collection_alias"), size=55)],
    [sg.Text("Catcher edits JSON file path")],
    [sg.Input(key=(catcherdiff, "catcher_json_file_path")), sg.FileBrowse()],
    [sg.Text("HTML report output file path")],
    [sg.Input(key=(catcherdiff, "report_file_path")), sg.FileSaveAs()],
    [
        sg.Checkbox(
            "Check terms against CONTENTdm controlled vocabularies",
            key=(catcherdiff, "check_vocabs"),
        )
    ],
    [sg.Button("Run", key=(catcherdiff, "-RUN-"))],
]

csv2catcher_layout = [
    [
        sg.Frame(
            "About",
            [[sg.Text("Reconcile and translate a CSV into cdm-catcher JSON edits")]],
        )
    ],
    [sg.Text("CONTENTdm instance URL")],
    [sg.InputText(key=(csv2catcher, "cdm_instance_url"))],
    [sg.Button("Request collection aliases", key=(csv2catcher, "-LOAD ALIASES-"))],
    [sg.Text("CONTENTdm collection alias")],
    [sg.Combo([], key=(csv2catcher, "cdm_collection_alias"), size=55)],
    [sg.Button("Request collection field nicks", key=(csv2catcher, "-LOAD NICKS-"))],
    [sg.Text("Columns to CONTENTdm field nicks mapping CSV")],
    [
        sg.Input(key=(csv2catcher, "column_mapping_csv_path")),
        sg.FileBrowse(),
    ],
    [sg.Text("CONTENTdm identifier field nick")],
    [sg.Combo([], key=(csv2catcher, "identifier_nick"), size=55)],
    [
        sg.Radio(
            "Match rows to pages",
            group_id="match_mode",
            key=(csv2catcher, "match_mode", "pages"),
        ),
        sg.Radio(
            "Match rows to objects",
            group_id="match_mode",
            key=(csv2catcher, "match_mode", "objects"),
        ),
    ],
    [sg.Text("Field data CSV path")],
    [
        sg.Input(key=(csv2catcher, "field_data_csv_path")),
        sg.FileBrowse(),
    ],
    [sg.Button("Load column names", key=(csv2catcher, "-LOAD COLUMNS-"))],
    [sg.Text("Page position column name")],
    [sg.Combo([], key=(csv2catcher, "page_position_column_name"), size=55)],
    [sg.Text("Catcher JSON output file path")],
    [sg.Input(key=(csv2catcher, "output_file_path")), sg.FileSaveAs()],
    [sg.Button("Run", key=(csv2catcher, "-RUN-"))],
]

ftpfields2catcher_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Get field-based transcription metadata from FromThePage as cdm-catcher JSON edits"
                    )
                ]
            ],
        )
    ],
    [
        sg.Radio(
            "Match fields to objects",
            group_id="match_mode",
            key=(ftpfields2catcher, "match_mode", MatchModes.by_object),
        ),
        sg.Radio(
            "Match fields to pages",
            group_id="match_mode",
            key=(ftpfields2catcher, "match_mode", MatchModes.by_page),
        ),
    ],
    [sg.Text("FromThePage user slug")],
    [sg.InputText(key=(ftpfields2catcher, "ftp_slug"))],
    [
        sg.Button(
            "Request project names", key=(ftpfields2catcher, "-LOAD FTP PROJECTS-")
        )
    ],
    [sg.Text("FromThePage project name")],
    [sg.Combo([], key=(ftpfields2catcher, "ftp_project_name"), size=55)],
    [sg.Text("FromThePage field labels to CONTENTdm field nicks CSV mapping path")],
    [sg.Input(key=(ftpfields2catcher, "field_mapping_csv_path")), sg.FileBrowse()],
    [sg.Text("Catcher JSON output file path")],
    [sg.Input(key=(ftpfields2catcher, "output_file_path")), sg.FileSaveAs()],
    [sg.Button("Run", key=(ftpfields2catcher, "-RUN-"))],
]


ftptr2catcher_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Get transcripts from a list of FromThePage manifests as cdm-catcher JSON edits"
                    )
                ]
            ],
        )
    ],
    [sg.Text("FromThePage IIIF manifests file path")],
    [sg.Input(key=(ftptr2catcher, "manifests_listing_path")), sg.FileBrowse()],
    [sg.Text("CONTENTdm transcript field nick")],
    [sg.InputText(key=(ftptr2catcher, "transcript_nick"))],
    [sg.Text("Catcher JSON output file path")],
    [sg.Input(key=(ftptr2catcher, "output_file_path")), sg.FileSaveAs()],
    [sg.Text("FromThePage transcript type")],
    [
        sg.Combo(
            ["Verbatim Plaintext"],
            default_value="Verbatim Plaintext",
            key=(ftptr2catcher, "transcript_type"),
        )
    ],
    [sg.Button("Run", key=(ftptr2catcher, "-RUN-"))],
]

csv2json_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Transpose CSV files into lists of JSON objects (cdm-catcher JSON edits)"
                    )
                ]
            ],
        )
    ],
    [sg.Text("Path to input CSV file")],
    [sg.Input(key=(csv2json, "input_csv_path")), sg.FileBrowse()],
    [sg.Text("Path to output JSON file")],
    [sg.Input(key=(csv2json, "output_json_path")), sg.FileSaveAs()],
    [sg.Button("Run", key=(csv2json, "-RUN-"))],
]

ftpmdc2catcher_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Get FromThePage Metadata Creation project data as cdm-catcher JSON edits"
                    )
                ]
            ],
        )
    ],
    [sg.Text("FromThePage user slug")],
    [sg.InputText(key=(ftpmdc2catcher, "ftp_slug"))],
    [sg.Button("Request project names", key=(ftpmdc2catcher, "-LOAD FTP PROJECTS-"))],
    [sg.Text("FromThePage project name")],
    [sg.Combo([], key=(ftpmdc2catcher, "ftp_project_name"), size=55)],
    [sg.Text("FromThePage field labels to CONTENTdm field nicks CSV mapping path")],
    [sg.Input(key=(ftpmdc2catcher, "field_mapping_csv_path")), sg.FileBrowse()],
    [sg.Text("Catcher JSON output file path")],
    [sg.Input(key=(ftpmdc2catcher, "output_file_path")), sg.FileSaveAs()],
    [sg.Button("Run", key=(ftpmdc2catcher, "-RUN-"))],
]

scanftpvocabs_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Cross check a FromThePage collection against CONTENTdm controlled vocabs"
                    )
                ]
            ],
        )
    ],
    [sg.Text("FromThePage user slug")],
    [sg.InputText(key=(scanftpvocabs, "ftp_slug"))],
    [sg.Button("Request project names", key=(scanftpvocabs, "-LOAD FTP PROJECTS-"))],
    [sg.Text("FromThePage project name")],
    [sg.Combo([], key=(scanftpvocabs, "ftp_project_name"), size=55)],
    [sg.Text("CONTENTdm instance URL")],
    [sg.InputText(key=(scanftpvocabs, "cdm_instance_url"))],
    [sg.Button("Request collection aliases", key=(scanftpvocabs, "-LOAD ALIASES-"))],
    [sg.Text("CONTENTdm collection alias")],
    [sg.Combo([], key=(scanftpvocabs, "cdm_collection_alias"), size=55)],
    [sg.Text("FromThePage field labels to CONTENTdm field nicks CSV mapping path")],
    [sg.Input(key=(scanftpvocabs, "field_mapping_csv_path")), sg.FileBrowse()],
    [sg.Text("HTML report output file path")],
    [sg.Input(key=(scanftpvocabs, "report_file_path")), sg.FileSaveAs()],
    [sg.Button("Run", key=(scanftpvocabs, "-RUN-"))],
]

scanftpfields_layout = [
    [
        sg.Frame(
            "About",
            [
                [
                    sg.Text(
                        "Scan and report on a FromThePage collection's field-based transcription labels"
                    )
                ]
            ],
        )
    ],
    [sg.Text("FromThePage user slug")],
    [sg.InputText(key=(scanftpfields, "ftp_slug"))],
    [sg.Button("Request project names", key=(scanftpfields, "-LOAD FTP PROJECTS-"))],
    [sg.Text("FromThePage project name")],
    [sg.Combo([], key=(scanftpfields, "ftp_project_name"), size=55)],
    [sg.Text("HTML report output file path")],
    [sg.Input(key=(scanftpfields, "report_file_path")), sg.FileSaveAs()],
    [sg.Button("Run", key=(scanftpfields, "-RUN-"))],
]

layout = [
    [
        sg.TabGroup(
            [
                [
                    sg.Tab("catcherdiff", catcherdiff_layout),
                    sg.Tab("scanftpvocabs", scanftpvocabs_layout),
                    sg.Tab("scanftpfields", scanftpfields_layout),
                    sg.Tab("ftpfields2catcher", ftpfields2catcher_layout),
                    sg.Tab("ftptr2catcher", ftptr2catcher_layout),
                    sg.Tab("ftpmdc2catcher", ftpmdc2catcher_layout),
                    sg.Tab("csv2catcher", csv2catcher_layout),
                    sg.Tab("csv2json", csv2json_layout),
                ]
            ]
        )
    ],
    [sg.Text("Command Log")],
    [sg.Output(size=(80, 10), key="-OUTPUT-")],
    [sg.Push(), sg.Quit()],
]

window = sg.Window("cdm-util-scripts", layout, location=(25, 50))

while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED or event == "Quit":
        break

    if isinstance(event, tuple):
        event_function, event_value, *event_rest = event
        tab_values = dict()
        for values_key, values_value in values.items():
            if isinstance(values_key, tuple):
                tab_function, tab_key, *tab_rest = values_key
                if tab_function is event_function:
                    # Handle radio buttons
                    if tab_rest and isinstance(values_value, bool):
                        if values_value is True:
                            tab_values[tab_key] = tab_rest[0]
                    else:
                        tab_values[tab_key] = values_value

        if "cdm_collection_alias" in tab_values:
            tab_values["cdm_collection_alias"] = tab_values[
                "cdm_collection_alias"
            ].partition("=")[0]
        if "identifier_nick" in tab_values:
            tab_values["identifier_nick"] = tab_values["identifier_nick"].partition(
                "="
            )[0]

        if event_value == "-LOAD ALIASES-":
            print("Requesting CONTENTdm collection aliases... ", end="")
            with requests.Session() as session:
                cdm_collection_list = cdm_api.request_collection_list(
                    instance_url=tab_values["cdm_instance_url"],
                    session=session,
                )
            window[(event_function, "cdm_collection_alias")].update(
                values=[
                    f"{info.alias.lstrip('/')}={info.name}"
                    for info in cdm_collection_list
                ]
            )
            print("Done")

        elif event_value == "-LOAD NICKS-":
            print("Requesting CONTENTdm field nicks... ", end="")
            with requests.Session() as session:
                cdm_field_infos = cdm_api.request_field_infos(
                    instance_url=tab_values["cdm_instance_url"],
                    collection_alias=tab_values["cdm_collection_alias"],
                    session=session,
                )
            window[(event_function, "identifier_nick")].update(
                values=[f"{info.nick}={info.name}" for info in cdm_field_infos]
            )
            print("Done")

        elif event_value == "-LOAD COLUMNS-":
            print("Loading CSV column names... ", end="")
            with open(
                tab_values["field_data_csv_path"],
                mode="r",
                encoding="utf-8",
                newline="",
            ) as fp:
                reader = csv.DictReader(fp, dialect=cdm_api.sniff_csv_dialect(fp))
                fieldnames = reader.fieldnames
            window[(event_function, "page_position_column_name")].update(
                values=fieldnames
            )
            print("Done")

        elif event_value == "-LOAD FTP PROJECTS-":
            print("Requesting FromThePage project names... ", end="")
            with requests.Session() as session:
                ftp_instance = ftp_api.FtpInstance(base_url=ftp_api.FTP_HOSTED_BASE_URL)
                ftp_project_collection = ftp_instance.request_projects(
                    slug=tab_values["ftp_slug"], session=session
                )
            window[(event_function, "ftp_project_name")].update(
                values=list(ftp_project_collection.projects)
            )
            print("Done")

        elif event_value == "-RUN-":
            missing_values_keys = [
                key for key, value in tab_values.items() if value == ""
            ]
            if missing_values_keys:
                sg.popup("Missing required input values")
                continue
            print(f"Running {event_function.__name__}(**{tab_values!r})")

        else:
            print("Unhandled event")

window.close()
