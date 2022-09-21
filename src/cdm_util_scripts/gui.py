import PySimpleGUI as sg
import requests

import csv

from typing import Callable, Dict, Any, Hashable

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api
from cdm_util_scripts.catcherdiff import catcherdiff
from cdm_util_scripts.csv2json import csv2json
from cdm_util_scripts.ftptransc2catcher import ftptransc2catcher
from cdm_util_scripts.ftpstruct2catcher import ftpstruct2catcher, Level
from cdm_util_scripts.scanftpfields import scanftpfields


HELP_SIZE = (80, 2)


def gui() -> None:
    catcherdiff_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(catcherdiff.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("CONTENTdm instance URL")],
        [
            sg.InputText(key=(catcherdiff, "cdm_instance_url")),
            sg.Button(
                "Request collection aliases", key=(catcherdiff, "-LOAD ALIASES-")
            ),
        ],
        [sg.Text("CONTENTdm collection alias")],
        [sg.Combo([], key=(catcherdiff, "cdm_collection_alias"), size=55)],
        [sg.Text("Catcher edits JSON file path")],
        [
            sg.Input(key=(catcherdiff, "catcher_json_file_path")),
            sg.FileBrowse(file_types=(("JSON", "*.json"),)),
        ],
        [sg.Text("HTML report output file path")],
        [
            sg.Input(key=(catcherdiff, "report_file_path")),
            sg.FileSaveAs(file_types=(("HTML", "*.html"),), default_extension=".html"),
        ],
        [
            sg.Checkbox(
                "Check terms against CONTENTdm controlled vocabularies",
                key=(catcherdiff, "check_vocabs"),
            )
        ],
        [sg.Button("Run", key=(catcherdiff, "-RUN-"))],
    ]

    ftptransc2catcher_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(ftptransc2catcher.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("FromThePage IIIF manifests file path")],
        [sg.Input(key=(ftptransc2catcher, "manifests_listing_path")), sg.FileBrowse()],
        [sg.Text("CONTENTdm transcript field nick")],
        [sg.InputText(key=(ftptransc2catcher, "transcript_nick"))],
        [sg.Text("Catcher JSON output file path")],
        [
            sg.Input(key=(ftptransc2catcher, "output_file_path")),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".html"),
        ],
        [sg.Text("FromThePage transcript type")],
        [
            sg.Combo(
                ["Verbatim Plaintext"],
                default_value="Verbatim Plaintext",
                key=(ftptransc2catcher, "transcript_type"),
            )
        ],
        [sg.Button("Run", key=(ftptransc2catcher, "-RUN-"))],
    ]

    csv2json_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(csv2json.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("Path to input CSV file")],
        [
            sg.Input(key=(csv2json, "input_csv_path")),
            sg.FileBrowse(file_types=(("CSV", "*.csv"),)),
        ],
        [sg.Text("Path to output JSON file")],
        [
            sg.Input(key=(csv2json, "output_json_path")),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
        ],
        [sg.Button("Run", key=(csv2json, "-RUN-"))],
    ]

    ftpstruct2catcher_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(ftpstruct2catcher.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("FromThePage user slug")],
        [
            sg.InputText(key=(ftpstruct2catcher, "ftp_slug")),
            sg.Button(
                "Request project names", key=(ftpstruct2catcher, "-LOAD FTP PROJECTS-")
            ),
        ],
        [sg.Text("FromThePage project name")],
        [sg.Combo([], key=(ftpstruct2catcher, "ftp_project_name"), size=55)],
        [sg.Text("FromThePage field labels to CONTENTdm field nicks CSV mapping path")],
        [
            sg.Input(key=(ftpstruct2catcher, "field_mapping_csv_path")),
            sg.FileBrowse(file_types=(("CSV", "*.csv"),)),
        ],
        [sg.Text("Level of description to export")],
        [
            sg.Radio(
                "Autodetect",
                group_id="level",
                key=(ftpstruct2catcher, "level", Level.AUTO),
                default=True,
            ),
            sg.Radio(
                "Work", group_id="level", key=(ftpstruct2catcher, "level", Level.WORK)
            ),
            sg.Radio(
                "Page", group_id="level", key=(ftpstruct2catcher, "level", Level.PAGE)
            ),
            sg.Radio(
                "Both", group_id="level", key=(ftpstruct2catcher, "level", Level.BOTH)
            ),
        ],
        [sg.Text("Catcher JSON output file path")],
        [
            sg.Input(key=(ftpstruct2catcher, "output_file_path")),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
        ],
        [sg.Button("Run", key=(ftpstruct2catcher, "-RUN-"))],
    ]

    scanftpfields_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(scanftpfields.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("FromThePage user slug")],
        [
            sg.InputText(key=(scanftpfields, "ftp_slug")),
            sg.Button(
                "Request project names", key=(scanftpfields, "-LOAD FTP PROJECTS-")
            ),
        ],
        [sg.Text("FromThePage project name")],
        [sg.Combo([], key=(scanftpfields, "ftp_project_name"), size=55)],
        [sg.Text("HTML report output file path")],
        [
            sg.Input(key=(scanftpfields, "report_path")),
            sg.FileSaveAs(file_types=(("HTML", "*.html"),), default_extension=".html"),
        ],
        [sg.Button("Run", key=(scanftpfields, "-RUN-"))],
    ]

    cdmschema2csv_layout = [
        [
            sg.Frame(
                "Help",
                [
                    [
                        sg.Text(
                            cdmschema2csv.__doc__,
                            size=HELP_SIZE,
                        )
                    ]
                ],
            )
        ],
        [sg.Text("CONTENTdm instance URL")],
        [
            sg.InputText(key=(cdmschema2csv, "cdm_instance_url")),
            sg.Button(
                "Request collection aliases", key=(cdmschema2csv, "-LOAD ALIASES-")
            ),
        ],
        [sg.Text("CONTENTdm collection alias")],
        [sg.Combo([], key=(cdmschema2csv, "cdm_collection_alias"), size=55)],
        [sg.Text("CSV output file path")],
        [
            sg.Input(key=(cdmschema2csv, "csv_file_path")),
            sg.FileSaveAs(file_types=(("CSV", "*.csv"),), default_extension=".csv"),
        ],
        [sg.Button("Run", key=(cdmschema2csv, "-RUN-"))],
    ]

    layout = [
        [
            sg.TabGroup(
                [
                    [
                        sg.Tab("catcherdiff", catcherdiff_layout),
                        sg.Tab("scanftpfields", scanftpfields_layout),
                        sg.Tab("ftptransc2catcher", ftptransc2catcher_layout),
                        sg.Tab("ftpstruct2catcher", ftpstruct2catcher_layout),
                        sg.Tab("cdmschema2csv", cdmschema2csv_layout),
                        sg.Tab("csv2json", csv2json_layout),
                    ]
                ]
            )
        ],
        [sg.Text("Command Log")],
        [
            sg.Multiline(
                auto_refresh=True,
                autoscroll=True,
                reroute_stdout=True,
                write_only=True,
                font="Courier 10",
                size=(72, 10),
                key="-OUTPUT-",
            )
        ],
        [sg.Push(), sg.Quit()],
    ]

    window = sg.Window("cdm-util-scripts", layout, location=(25, 50))

    try:
        while True:
            event, values = window.read()

            if event == sg.WIN_CLOSED or event == "Quit":
                break

            if isinstance(event, tuple):
                event_function, event_value, *event_rest = event

                tab_values = get_tab_values(event_function, values)

                if event_value == "-LOAD ALIASES-":
                    print("Requesting CONTENTdm collection aliases... ")
                    try:
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
                    except Exception as e:
                        print("Request failed with error: ", e)

                elif event_value == "-LOAD FTP PROJECTS-":
                    print("Requesting FromThePage project names... ")
                    try:
                        with requests.Session() as session:
                            ftp_instance = ftp_api.FtpInstance(
                                url=ftp_api.FTP_HOSTED_URL
                            )
                            ftp_project_collection = ftp_instance.request_projects(
                                slug=tab_values["ftp_slug"], session=session
                            )
                        window[(event_function, "ftp_project_name")].update(
                            values=[
                                project.label
                                for project in ftp_project_collection.projects
                            ]
                        )
                        print("Done")
                    except Exception as e:
                        print("Request failed with error:", e)

                elif event_value == "-RUN-":
                    missing_values_keys = [
                        key
                        for key, value in tab_values.items()
                        if isinstance(value, str) and not value.strip()
                    ]
                    if missing_values_keys:
                        sg.popup(
                            "Missing required input values:",
                            *missing_values_keys,
                            title="Missing input(s)",
                        )
                        continue

                    print(f"Running {event_function.__name__}(")
                    for key, value in tab_values.items():
                        print(f" {key}={value!r},")
                    print(")")

                    try:
                        event_function(**tab_values, show_progress=False)
                        print("Done")
                    except Exception as e:
                        print("Run failed with error:", e)
                        sg.popup("Run failed with error:", e, title="Run failed")

                else:
                    raise KeyError(repr(event_value))

        window.close()
    except Exception as e:
        sg.popup(e, title="Fatal Error")


def get_tab_values(event_function: Callable[..., None], values: Dict[Hashable, Any]):
    tab_values: Dict[str, Any] = dict()
    for values_key, values_value in values.items():
        if isinstance(values_key, tuple):
            tab_function, tab_key, *tab_rest = values_key
            if tab_function is event_function:

                # Handle radio buttons, which have a 3rd tuple value
                if tab_rest and isinstance(values_value, bool):
                    if values_value is True:
                        tab_value = tab_rest[0]
                else:
                    tab_value = values_value

                # Handle "<alias>=<fieldname>" values
                if tab_key in {"cdm_collection_alias"}:
                    tab_value = tab_value.partition("=")[0]

                if isinstance(tab_value, str):
                    tab_value = tab_value.strip()

                tab_values[tab_key] = tab_value

    return tab_values


def cdmschema2csv(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    csv_file_path: str,
    show_progress: bool = False,
) -> None:
    """Jump start a CONTENTdm field mapping by writing a CONTENTdm collection's editable names and nicks to CSV"""
    with requests.Session() as session:
        field_infos = cdm_api.request_field_infos(
            instance_url=cdm_instance_url,
            collection_alias=cdm_collection_alias,
            session=session,
        )
    with open(csv_file_path, mode="w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["name", "nick"], dialect="excel")
        writer.writeheader()
        for field_info in field_infos:
            if not field_info.readonly:
                writer.writerow(
                    {
                        "name": field_info.name,
                        "nick": field_info.nick,
                    }
                )
