import PySimpleGUI as sg
import requests

import csv
import json

from typing import Callable, Dict, Any, Hashable, Set, List, Iterable, Tuple

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api
from cdm_util_scripts.catcherdiff import catcherdiff
from cdm_util_scripts.catchercombineterms import catchercombineterms
from cdm_util_scripts.catchertidy import catchertidy as run_catchertidy
from cdm_util_scripts.csv2json import csv2json
from cdm_util_scripts.json2csv import json2csv
from cdm_util_scripts.ftptransc2catcher import ftptransc2catcher
from cdm_util_scripts.ftpstruct2catcher import ftpstruct2catcher, Level
from cdm_util_scripts.scanftpschema import scanftpschema


HELP_SIZE = (90, 2)
COMMAND_LOG_SIZE = (85, 12)
COMBO_SIZE = 70
INPUT_SIZE = 70


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
            sg.InputText(key=(catcherdiff, "cdm_instance_url"), size=INPUT_SIZE),
            sg.Button(
                "Request collection aliases", key=(catcherdiff, "-LOAD ALIASES-")
            ),
        ],
        [sg.Text("CONTENTdm collection alias")],
        [sg.Combo([], key=(catcherdiff, "cdm_collection_alias"), size=COMBO_SIZE)],
        [sg.Text("Catcher edits JSON file path")],
        [
            sg.Input(key=(catcherdiff, "catcher_json_file_path"), size=INPUT_SIZE),
            sg.FileBrowse(file_types=(("JSON", "*.json"),)),
        ],
        [sg.Text("HTML report output file path")],
        [
            sg.Input(key=(catcherdiff, "report_file_path"), size=INPUT_SIZE),
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

    catchercombineterms_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(catchercombineterms.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("CONTENTdm instance URL")],
        [
            sg.InputText(key=(catchercombineterms, "cdm_instance_url"), size=INPUT_SIZE),
            sg.Button(
                "Request collection aliases", key=(catchercombineterms, "-LOAD ALIASES-")
            ),
        ],
        [sg.Text("CONTENTdm collection alias")],
        [sg.Combo([], key=(catchercombineterms, "cdm_collection_alias"), size=COMBO_SIZE)],
        [sg.Text("Catcher edits JSON file path")],
        [
            sg.Input(key=(catchercombineterms, "catcher_json_file_path"), size=INPUT_SIZE),
            sg.FileBrowse(file_types=(("JSON", "*.json"),)),
        ],
        [sg.Text("Catcher JSON output file path")],
        [
            sg.Input(key=(catchercombineterms, "output_file_path"), size=INPUT_SIZE),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
        ],
        [
            sg.Checkbox(
                "Sort terms",
                default=True,
                key=(catchercombineterms, "sort_terms"),
            )
        ],
        [sg.Button("Run", key=(catchercombineterms, "-RUN-"))],
    ]

    catchertidy_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(run_catchertidy.__doc__, size=HELP_SIZE)]],
            )
        ],
        [
            sg.Column(
                layout=[
                    [sg.Text("CONTENTdm instance URL")],
                    [
                        sg.InputText(key=(catchertidy, "cdm_instance_url"), size=INPUT_SIZE),
                        sg.Button(
                            "Request collection aliases", key=(catchertidy, "-LOAD ALIASES-")
                        ),
                    ],
                    [sg.Text("CONTENTdm collection alias")],
                    [
                        sg.Combo([], key=(catchertidy, "cdm_collection_alias"), size=COMBO_SIZE),
                    ],

                    [sg.Text("Catcher edits JSON file path")],
                    [
                        sg.Input(key=(catchertidy, "catcher_json_file_path"), size=INPUT_SIZE),
                        sg.FileBrowse(file_types=(("JSON", "*.json"),)),
                    ],
                    [sg.Text("Configure tidy operations")],
                    [sg.Button("Configure...", key=(catchertidy, "-CONFIG TIDY-"))],
                    [sg.Text("Catcher JSON output file path")],
                    [
                        sg.Input(key=(catchertidy, "output_file_path"), size=INPUT_SIZE),
                        sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
                    ],
                    [sg.Button("Run", key=(catchertidy, "-RUN-"))],
                ]
            ),
            sg.Column(
                layout=[
                    [sg.Frame("Tidy Operations", size=(450, 600), layout=[], key=(catchertidy, "-TIDY OPS FRAME-"))],
                ],
                scrollable=True,
                vertical_alignment="top",
                key=(catchertidy, "-TIDY OPS COLUMN-"),
            ),
        ],
    ]

    ftptransc2catcher_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(ftptransc2catcher.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("FromThePage IIIF manifests file path")],
        [sg.Input(key=(ftptransc2catcher, "manifests_listing_path"), size=INPUT_SIZE), sg.FileBrowse()],
        [sg.Text("CONTENTdm transcript field nick")],
        [sg.InputText(key=(ftptransc2catcher, "transcript_nick"), size=INPUT_SIZE)],
        [sg.Text("Catcher JSON output file path")],
        [
            sg.Input(key=(ftptransc2catcher, "output_file_path"), size=INPUT_SIZE),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
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
            sg.Input(key=(csv2json, "input_csv_path"), size=INPUT_SIZE),
            sg.FileBrowse(file_types=(("CSV", "*.csv"),)),
        ],
        [sg.Text("Path to output JSON file")],
        [
            sg.Input(key=(csv2json, "output_json_path"), size=INPUT_SIZE),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
        ],
        [
            sg.Checkbox(
                "Drop empty CSV cells",
                default=True,
                key=(csv2json, "drop_empty_cells"),
            )
        ],
        [sg.Button("Run", key=(csv2json, "-RUN-"))],
    ]

    json2csv_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(json2csv.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("Path to input JSON file")],
        [
            sg.Input(key=(json2csv, "input_json_path"), size=INPUT_SIZE),
            sg.FileBrowse(file_types=(("JSON", "*.json"),)),
        ],
        [sg.Text("Path to output CSV file")],
        [
            sg.Input(key=(json2csv, "output_csv_path"), size=INPUT_SIZE),
            sg.FileSaveAs(file_types=(("CSV", "*.csv"),), default_extension=".csv"),
        ],
        [sg.Text("CSV dialect")],
        [
            sg.Combo(csv.list_dialects(), default_value="excel-tab", key=(json2csv, "csv_dialect")),
        ],
        [sg.Button("Run", key=(json2csv, "-RUN-"))],
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
            sg.InputText(key=(ftpstruct2catcher, "ftp_slug"), size=INPUT_SIZE),
            sg.Button(
                "Request project names", key=(ftpstruct2catcher, "-LOAD FTP PROJECTS-")
            ),
        ],
        [sg.Text("FromThePage project name")],
        [sg.Combo([], key=(ftpstruct2catcher, "ftp_project_name"), size=COMBO_SIZE)],
        [sg.Text("FromThePage field labels to CONTENTdm field nicks CSV mapping path")],
        [
            sg.Input(key=(ftpstruct2catcher, "field_mapping_csv_path"), size=INPUT_SIZE),
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
            sg.Input(key=(ftpstruct2catcher, "output_file_path"), size=INPUT_SIZE),
            sg.FileSaveAs(file_types=(("JSON", "*.json"),), default_extension=".json"),
        ],
        [sg.Button("Run", key=(ftpstruct2catcher, "-RUN-"))],
    ]

    scanftpschema_layout = [
        [
            sg.Frame(
                "Help",
                [[sg.Text(scanftpschema.__doc__, size=HELP_SIZE)]],
            )
        ],
        [sg.Text("FromThePage user slug")],
        [
            sg.InputText(key=(scanftpschema, "ftp_slug"), size=INPUT_SIZE),
            sg.Button(
                "Request project names", key=(scanftpschema, "-LOAD FTP PROJECTS-")
            ),
        ],
        [sg.Text("FromThePage project name")],
        [sg.Combo([], key=(scanftpschema, "ftp_project_name"), size=COMBO_SIZE)],
        [sg.Text("HTML report output file path")],
        [
            sg.Input(key=(scanftpschema, "report_path"), size=INPUT_SIZE),
            sg.FileSaveAs(file_types=(("HTML", "*.html"),), default_extension=".html"),
        ],
        [sg.Button("Run", key=(scanftpschema, "-RUN-"))],
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
            sg.InputText(key=(cdmschema2csv, "cdm_instance_url"), size=INPUT_SIZE),
            sg.Button(
                "Request collection aliases", key=(cdmschema2csv, "-LOAD ALIASES-")
            ),
        ],
        [sg.Text("CONTENTdm collection alias")],
        [sg.Combo([], key=(cdmschema2csv, "cdm_collection_alias"), size=COMBO_SIZE)],
        [sg.Text("CSV output file path")],
        [
            sg.Input(key=(cdmschema2csv, "csv_file_path"), size=INPUT_SIZE),
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
                        sg.Tab("catchercombineterms", catchercombineterms_layout),
                        sg.Tab("catchertidy", catchertidy_layout),
                        sg.Tab("scanftpschema", scanftpschema_layout),
                        sg.Tab("ftptransc2catcher", ftptransc2catcher_layout),
                        sg.Tab("ftpstruct2catcher", ftpstruct2catcher_layout),
                        sg.Tab("cdmschema2csv", cdmschema2csv_layout),
                        sg.Tab("csv2json", csv2json_layout),
                        sg.Tab("json2csv", json2csv_layout),
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
                size=COMMAND_LOG_SIZE,
                key="-OUTPUT-",
            )
        ],
        [sg.Quit()],
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

                elif event_value == "-CONFIG TIDY-":
                    cdm_instance_url = tab_values["cdm_instance_url"]
                    cdm_collection_alias = tab_values["cdm_collection_alias"]
                    if cdm_instance_url and cdm_collection_alias:
                        print("Requesting collection field info...")
                        try:
                            with requests.Session() as session:
                                field_infos = cdm_api.request_field_infos(
                                    instance_url=cdm_instance_url,
                                    collection_alias=cdm_collection_alias,
                                    session=session,
                                )
                        except Exception as e:
                            print("Request failed with error: ", e)
                            continue
                    catcher_json_file_path = tab_values["catcher_json_file_path"]
                    if not catcher_json_file_path:
                        print("Configuration requires Catcher edits JSON file path")
                        continue
                    print("Scanning Catcher edits for nicks...")
                    nicks = get_nicks_from_edit(catcher_json_file_path)
                    window.extend_layout(
                        window[(event_function, "-TIDY OPS FRAME-")],
                        [
                            [
                                sg.Checkbox("whitespace", default=True, key=(catchertidy, "normalize_whitespace", fi.nick)),
                                sg.Checkbox("quotes", default=True, key=(catchertidy, "replace_smart_chars", fi.nick)),
                                sg.Checkbox("lcsh", default=False, key=(catchertidy, "normalize_lcsh", fi.nick)),
                                sg.Checkbox("sort", default=bool(fi.vocab), key=(catchertidy, "sort_terms", fi.nick)),
                                sg.Text(fi.name),
                            ] for fi in field_infos if fi.nick in nicks
                        ],
                    )
                    window[(event_function, "-TIDY OPS COLUMN-")].contents_changed()
                    window[(event_function, "-CONFIG TIDY-")].update(
                        disabled=True,
                    )

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
    tab_values: Dict[str, Any] = {}
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

                # Handle catchertidy operations
                if tab_key in [
                        "normalize_whitespace",
                        "replace_smart_chars",
                        "normalize_lcsh",
                        "sort_terms"
                ]:
                    tab_value = tab_values.get(tab_key, [])
                    if values_value:
                        tab_value.append(tab_rest[0])

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


def catchertidy(*args, **kwargs) -> None:
    arguments = {
        k: v for k, v in kwargs.items()
        if k not in ["cdm_instance_url", "cdm_collection_alias"]
    }
    run_catchertidy(
        *args,
        **arguments,
    )


def get_nicks_from_edit(path: str) -> List[str]:
    nicks: Set[str] = set()
    with open(path, mode="r", encoding="utf-8") as fp:
        catcher_edits = json.load(fp)
    for edit in catcher_edits:
        nicks.update(edit)
    nicks.discard("dmrecord")
    return sorted(nicks)
