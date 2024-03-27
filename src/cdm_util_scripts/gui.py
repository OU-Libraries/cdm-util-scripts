import csv
import json
import sys
import textwrap
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import scrolledtext

import requests

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api
from cdm_util_scripts.catcherdiff import catcherdiff
from cdm_util_scripts.catchercombineterms import catchercombineterms
from cdm_util_scripts.catchertidy import catchertidy
from cdm_util_scripts.ftptransc2catcher import ftptransc2catcher
from cdm_util_scripts.ftpstruct2catcher import ftpstruct2catcher, Level
from cdm_util_scripts.scanftpschema import scanftpschema
from cdm_util_scripts.csv2json import csv2json
from cdm_util_scripts.json2csv import json2csv

from typing import Dict, List, NamedTuple


HELP_LABEL_WRAP = 625
ENTRY_WIDTH = 80
COMBO_WIDTH = 78
PADX, PADY = (4, 4)


def gui() -> int:
    root = tk.Tk()
    root.title("cdm-util-scripts")
    root.report_callback_exception = report_callback_exception

    Console(root)

    notebook = ttk.Notebook(root)

    CatcherDiff(notebook)
    CatcherCombineTerms(notebook)
    CatcherTidy(notebook)
    FtpTransc2Catcher(notebook)
    FtpStruct2Catcher(notebook)
    ScanFtpSchema(notebook)
    CdmSchema2Csv(notebook)
    Csv2Json(notebook)
    Json2Csv(notebook)

    notebook.grid(column=0, row=1, sticky="nsew")
    root.mainloop()

    return 0


def report_callback_exception(exc, val, tb) -> None:
    print(val)
    messagebox.showerror("Exception", message=val)


# https://stackoverflow.com/questions/68198575/how-can-i-displaymy-console-output-in-tkinter
class Console:
    def __init__(self, parent) -> None:
        frame = ttk.Labelframe(parent, text="Console Log")
        frame.grid(column=0, row=0, sticky="w")
        console = scrolledtext.ScrolledText(
            frame,
            height=12,
            width=100,
            font=("consolas", "8", "normal"),
            state="disabled",
        )
        console.grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        console_out = ConsoleOut(console)
        sys.stdout = console_out
        sys.stderr = console_out


class ConsoleOut:
    def __init__(self, textbox: scrolledtext.ScrolledText) -> None:
        self.textbox = textbox

    def write(self, text: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def flush(self) -> None:
        pass


class CatcherDiff:
    cdm_instance_url: tk.StringVar
    cdm_collection_alias: tk.StringVar
    catcher_json_file_path: tk.StringVar
    report_file_path: tk.StringVar
    check_vocabs: tk.BooleanVar
    _alias_picker: ttk.Combobox

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, width=80)
        notebook.add(frame, text="catcherdiff")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=catcherdiff.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.cdm_instance_url = tk.StringVar()
        url_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm instance URL",
        )
        url_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            url_frame,
            textvariable=self.cdm_instance_url,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            url_frame,
            text="Request collection aliases",
            command=self.request_aliases,
        ).grid(column=0, row=1, sticky="w", padx=PADX, pady=PADY)

        self.cdm_collection_alias = tk.StringVar()
        alias_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm collection alias",
        )
        alias_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        self._alias_picker = ttk.Combobox(
            alias_frame,
            textvariable=self.cdm_collection_alias,
            width=COMBO_WIDTH,
        )
        self._alias_picker.grid(column=0, row=0, sticky="ew", padx=PADX, pady=PADY)

        self.catcher_json_file_path = tk.StringVar()
        input_frame = ttk.Labelframe(
            frame,
            text="Catcher JSON input file",
        )
        input_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            input_frame,
            textvariable=self.catcher_json_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            input_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.report_file_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="HTML report",
        )
        output_frame.grid(column=0, row=4, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.report_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.check_vocabs = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Check vocabs",
            variable=self.check_vocabs,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=5, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=6, sticky="w", padx=PADX, pady=PADY)

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        collection_aliases = request_contentdm_collection_aliases(cdm_instance_url)
        self._alias_picker["values"] = tuple(
            f"{alias}={name}" for name, alias in collection_aliases.items()
        )

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose Catcher JSON file",
            filetypes=[
                ("JSON", "*.json"),
            ],
        )
        if result is not None:
            self.catcher_json_file_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save HTML Report As",
            defaultextension=".html",
        )
        if result is not None:
            self.report_file_path.set(result)

    def run(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        cdm_collection_and_alias = self.cdm_collection_alias.get()
        if not cdm_collection_and_alias:
            messagebox.showerror(message="Please enter an CONTENTdm collection alias")
            return
        cdm_collection_alias = cdm_collection_and_alias.rpartition("=")[0]
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showerror(message="Please enter a Catcher JSON file")
            return
        report_file_path = self.report_file_path.get()
        if not report_file_path:
            messagebox.showerror(message="Please enter an HTML report file path")
            return
        check_vocabs = self.check_vocabs.get()
        print(
            textwrap.dedent(f"""\
        catcherdiff(
            cdm_instance_url={cdm_instance_url},
            cdm_collection_alias={cdm_collection_alias},
            catcher_json_file_path={catcher_json_file_path},
            report_file_path={report_file_path},
            check_vocabs={check_vocabs},
        )"""))
        catcherdiff(
            cdm_instance_url=cdm_instance_url,
            cdm_collection_alias=cdm_collection_alias,
            catcher_json_file_path=catcher_json_file_path,
            report_file_path=report_file_path,
            check_vocabs=check_vocabs,
            show_progress=False,
        )


class CatcherCombineTerms:
    cdm_instance_url: tk.StringVar
    cdm_collection_alias: tk.StringVar
    catcher_json_file_path: tk.StringVar
    output_file_path: tk.StringVar
    sort_terms: tk.BooleanVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="catchercombineterms")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=catchercombineterms.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.cdm_instance_url = tk.StringVar()
        url_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm instance URL",
        )
        url_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            url_frame,
            textvariable=self.cdm_instance_url,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            url_frame,
            text="Request collection aliases",
            command=self.request_aliases,
        ).grid(column=0, row=1, sticky="w", padx=PADX, pady=PADY)

        self.cdm_collection_alias = tk.StringVar()
        alias_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm collection alias",
        )
        alias_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        self._alias_picker = ttk.Combobox(
            alias_frame,
            textvariable=self.cdm_collection_alias,
            width=COMBO_WIDTH,
        )
        self._alias_picker.grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)

        self.catcher_json_file_path = tk.StringVar()
        input_frame = ttk.Labelframe(
            frame,
            text="Catcher JSON file",
        )
        input_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            input_frame,
            textvariable=self.catcher_json_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="ew", padx=PADX, pady=PADY)
        ttk.Button(
            input_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.output_file_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Combined Catcher JSON",
        )
        output_frame.grid(column=0, row=4, padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.output_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="ew", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.sort_terms = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Sort Terms",
            variable=self.sort_terms,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=5, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=6, sticky="w", padx=PADX, pady=PADY)

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        collection_aliases = request_contentdm_collection_aliases(cdm_instance_url)
        self._alias_picker["values"] = tuple(
            f"{alias}={name}" for name, alias in collection_aliases.items()
        )

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose Catcher JSON file",
            filetypes=[
                ("JSON", "*.json"),
            ],
        )
        if result is not None:
            self.catcher_json_file_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save Combined Catcher JSON As",
            defaultextension=".json",
        )
        if result is not None:
            self.output_file_path.set(result)

    def run(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        cdm_collection_and_alias = self.cdm_collection_alias.get()
        if not cdm_collection_and_alias:
            messagebox.showerror(message="Please enter an CONTENTdm collection alias")
            return
        cdm_collection_alias = cdm_collection_and_alias.partition("=")[0]
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showerror(message="Please enter a Catcher JSON file path")
            return
        output_file_path = self.output_file_path.get()
        if not output_file_path:
            messagebox.showerror(message="Please enter a Combined Catcher JSON file path")
            return
        sort_terms = self.sort_terms.get()
        print(
            textwrap.dedent(f"""\
        catchercombineterms(
            cdm_instance_url={cdm_instance_url},
            cdm_collection_alias={cdm_collection_alias},
            catcher_json_file_path={catcher_json_file_path},
            output_file_path={output_file_path},
            sort_terms={sort_terms},
        )"""))
        catchercombineterms(
            cdm_instance_url=cdm_instance_url,
            cdm_collection_alias=cdm_collection_alias,
            catcher_json_file_path=catcher_json_file_path,
            output_file_path=output_file_path,
            sort_terms=sort_terms,
            show_progress=False,
        )


class CatcherTidy:
    cdm_instance_url: tk.StringVar
    cdm_collection_alias: tk.StringVar
    catcher_json_file_path: tk.StringVar
    output_file_path: tk.StringVar
    lcsh_separator_spaces: tk.BooleanVar
    _tidy_ops_rows: List["TidyOpsRow"]
    _tidy_ops_frame: ttk.Labelframe

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="catchertidy")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=catchertidy.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.cdm_instance_url = tk.StringVar()
        url_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm instance URL",
        )
        url_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            url_frame,
            textvariable=self.cdm_instance_url,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            url_frame,
            text="Request collection aliases",
            command=self.request_aliases,
        ).grid(column=0, row=1, sticky="w", padx=PADX, pady=PADY)

        self.cdm_collection_alias = tk.StringVar()
        alias_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm collection alias",
        )
        alias_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        self._alias_picker = ttk.Combobox(
            alias_frame,
            textvariable=self.cdm_collection_alias,
            width=COMBO_WIDTH,
        )
        self._alias_picker.grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)

        self.catcher_json_file_path = tk.StringVar()
        input_frame = ttk.Labelframe(
            frame,
            text="Catcher JSON file",
        )
        input_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            input_frame,
            textvariable=self.catcher_json_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            input_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self._tidy_ops_rows = []
        ttk.Button(
            frame,
            text="Configure Tidy Operations...",
            command=self.configure_tidy_operations,
        ).grid(column=0, row=4, sticky="w", padx=PADX, pady=PADY)

        self.output_file_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Tidied Catcher JSON",
        )
        output_frame.grid(column=0, row=5, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.output_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.lcsh_separator_spaces = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Insert subfield separator spaces in normalized LCSH",
            variable=self.lcsh_separator_spaces,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=6, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=7, sticky="w", padx=PADX, pady=PADY)

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        collection_aliases = request_contentdm_collection_aliases(cdm_instance_url)
        self._alias_picker["values"] = tuple(
            f"{alias}={name}" for name, alias in collection_aliases.items()
        )

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose Catcher JSON file",
            filetypes=[
                ("JSON", "*.json"),
            ],
        )
        if result is not None:
            self.catcher_json_file_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save Tidy Catcher JSON As",
            defaultextension=".json",
        )
        if result is not None:
            self.output_file_path.set(result)

    def configure_tidy_operations(self) -> None:
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showerror(message="Please enter a Catcher JSON file path")
            return
        nicks = get_nicks_from_edit(catcher_json_file_path)

        cdm_instance_url = self.cdm_instance_url.get()
        cdm_collection_alias = self.cdm_collection_alias.get().partition("=")[0]
        if cdm_instance_url and cdm_collection_alias:
            long_field_infos = request_contentdm_field_info(
                cdm_instance_url=cdm_instance_url,
                cdm_collection_alias=cdm_collection_alias,
            )
            short_field_infos = [
                ShortFieldInfo(name=field_info.name, nick=field_info.nick, vocab=bool(field_info.vocab))
                for field_info in long_field_infos if field_info.nick in nicks
            ]
        else:
            short_field_infos = [ShortFieldInfo(name=nick, nick=nick, vocab=False) for nick in nicks]

        self._tidy_ops_rows = []

        config_window = tk.Toplevel()
        config_window.title("Tidy Operations Configuration")
        config_frame = ttk.Frame(config_window)
        config_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        TidyOpsRow.add_label_row(config_frame, row=0)

        for row, field_info in enumerate(short_field_infos, start=1):
            ops = TidyOpsRow.from_short_info(field_info)
            self._tidy_ops_rows.append(ops)
            ops.add(config_frame, row=row)

    def run(self) -> None:
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showerror(message="Please enter a Catcher JSON file path")
            return
        output_file_path = self.output_file_path.get()
        if not output_file_path:
            messagebox.showerror(message="Please enter a tidied Catcher JSON file path")
            return
        normalize_whitespace: List[str] = []
        replace_smart_chars: List[str] = []
        normalize_lcsh: List[str] = []
        sort_terms: List[str] = []
        for row in self._tidy_ops_rows:
            if row.whitespace.get():
                normalize_whitespace.append(row.nick)
            if row.quotes.get():
                replace_smart_chars.append(row.nick)
            if row.lcsh.get():
                normalize_lcsh.append(row.nick)
            if row.sort.get():
                sort_terms.append(row.nick)
        lcsh_seperator_spaces = self.lcsh_separator_spaces.get()
        print(
            textwrap.dedent(f"""\
        catchertidy(
            catcher_json_file_path={catcher_json_file_path},
            output_file_path={output_file_path},
            normalize_whitespace={normalize_whitespace},
            replace_smart_chars={replace_smart_chars},
            normalize_lcsh={normalize_lcsh},
            sort_terms={sort_terms},
            lcsh_seperator_spaces={lcsh_seperator_spaces},
        )"""))
        catchertidy(
            catcher_json_file_path=catcher_json_file_path,
            output_file_path=output_file_path,
            normalize_whitespace=normalize_whitespace,
            replace_smart_chars=replace_smart_chars,
            normalize_lcsh=normalize_lcsh,
            sort_terms=sort_terms,
            lcsh_separator_spaces=lcsh_seperator_spaces,
            show_progress=False,
        )


class TidyOpsRow(NamedTuple):
    name: str
    nick: str
    whitespace: tk.BooleanVar
    quotes: tk.BooleanVar
    lcsh: tk.BooleanVar
    sort: tk.BooleanVar

    @classmethod
    def from_short_info(cls, short_info: "ShortFieldInfo") -> "TidyOpsRow":
        return cls(
            name=short_info.name,
            nick=short_info.nick,
            whitespace=tk.BooleanVar(value=True),
            quotes=tk.BooleanVar(value=True),
            lcsh=tk.BooleanVar(value=is_lcsh_guess(short_info.name)),
            sort=tk.BooleanVar(value=short_info.vocab),
        )

    @classmethod
    def add_label_row(cls, parent: ttk.Frame, row: int) -> None:
        ttk.Label(parent, text="Whitespace").grid(column=0, row=row, sticky="w", padx=PADX, pady=PADY)
        ttk.Label(parent, text="Quotes").grid(column=1, row=row, sticky="w", padx=PADX, pady=PADY)
        ttk.Label(parent, text="LCSH").grid(column=2, row=row, sticky="w", padx=PADX, pady=PADY)
        ttk.Label(parent, text="Sort").grid(column=3, row=row, sticky="w", padx=PADX, pady=PADY)
        ttk.Label(parent, text="Field").grid(column=4, row=row, sticky="w", padx=PADX + 4, pady=PADY)

    def add(self, parent: ttk.Frame, row: int) -> None:
        ttk.Checkbutton(parent, variable=self.whitespace).grid(column=0, row=row, sticky="w", padx=PADX)
        ttk.Checkbutton(parent, variable=self.quotes).grid(column=1, row=row, sticky="w", padx=PADX)
        ttk.Checkbutton(parent, variable=self.lcsh).grid(column=2, row=row, sticky="w", padx=PADX)
        ttk.Checkbutton(parent, variable=self.sort).grid(column=3, row=row, sticky="w", padx=PADX)
        ttk.Label(parent, text=self.name).grid(column=4, row=row, sticky="w", padx=PADX + 4)


class FtpTransc2Catcher:
    manifests_listing_path: tk.StringVar
    transcript_nick: tk.StringVar
    output_file_path: tk.StringVar
    transcript_type: tk.StringVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="ftptransc2catcher")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=ftptransc2catcher.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.manifests_listing_path = tk.StringVar()
        manifests_frame = ttk.Labelframe(
            frame,
            text="FromThePage IIIF manifests file",
        )
        manifests_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            manifests_frame,
            textvariable=self.manifests_listing_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            manifests_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.transcript_nick = tk.StringVar()
        nick_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm transcript field nick",
        )
        nick_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            nick_frame,
            textvariable=self.transcript_nick,
            width=20,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)

        self.output_file_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Catcher JSON output file",
        )
        output_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.output_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.transcript_type = tk.StringVar()
        type_frame = ttk.Labelframe(
            frame,
            text="FromThePage transcript type",
        )
        type_frame.grid(column=0, row=4, sticky="ew", padx=PADX, pady=PADY)
        transc_type_box = ttk.Combobox(
            type_frame,
            textvariable=self.transcript_type,
            values=("Verbatim Plaintext",),
            width=COMBO_WIDTH,
        )
        transc_type_box.grid(column=0, row=8, sticky="w", padx=PADX, pady=PADY)
        transc_type_box.set("Verbatim Plaintext")

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=5, sticky="w", padx=PADX, pady=PADY)

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose FromThePage IIIF manifests file",
            filetypes=[
                ("TXT", "*.txt"),
            ],
        )
        if result is not None:
            self.manifests_listing_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save Catcher JSON File As",
            defaultextension=".json",
        )
        if result is not None:
            self.output_file_path.set(result)

    def run(self) -> None:
        manifests_listing_path = self.manifests_listing_path.get()
        if not manifests_listing_path:
            messagebox.showerror(message="Please enter a FromThePage IIIF manifests listing path")
            return
        transcript_nick = self.transcript_nick.get()
        if not transcript_nick:
            messagebox.showerror(message="Please enter a CONTENTdm transcript field nick")
            return
        output_file_path = self.output_file_path.get()
        if not output_file_path:
            messagebox.showerror(message="Please enter a Catcher JOSN file path")
            return
        transcript_type = self.transcript_type.get()
        if not transcript_type:
            messagebox.showerror(message="Please enter a FromThePage transcript type")
        print(
            textwrap.dedent(f"""\
        ftptransc2catcher(
            manifests_listing_path={manifests_listing_path},
            transcript_nick={transcript_nick},
            output_file_path={output_file_path},
            transcript_type={transcript_type},
        )"""))
        ftptransc2catcher(
            manifests_listing_path=manifests_listing_path,
            transcript_nick=transcript_nick,
            output_file_path=output_file_path,
            transcript_type=transcript_type,
            show_progress=False,
        )


class FtpStruct2Catcher:
    ftp_slug: tk.StringVar
    ftp_project_name: tk.StringVar
    field_mapping_csv_path: tk.StringVar
    level: tk.StringVar
    output_file_path: tk.StringVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="ftpstruct2catcher")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=ftpstruct2catcher.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.ftp_slug = tk.StringVar()
        slug_frame = ttk.Labelframe(
            frame,
            text="FromThePage user slug",
        )
        slug_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            slug_frame,
            textvariable=self.ftp_slug,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            slug_frame,
            text="Request project names",
            command=self.request_project_names,
        ).grid(column=0, row=1, sticky="w", padx=PADX, pady=PADY)

        self.ftp_project_name = tk.StringVar()
        project_frame = ttk.Labelframe(
            frame,
            text="FromThePage project name",
        )
        project_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        self._project_picker = ttk.Combobox(
            project_frame,
            textvariable=self.ftp_project_name,
            width=COMBO_WIDTH,
        )
        self._project_picker.grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)

        self.field_mapping_csv_path = tk.StringVar()
        mapping_frame = ttk.Labelframe(
            frame,
            text="FromThePage field labels to CONTENTdm field nicks mapping CSV"
        )
        mapping_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            mapping_frame,
            textvariable=self.field_mapping_csv_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            mapping_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.level = tk.StringVar()
        level_frame = ttk.Labelframe(
            frame,
            text="Level of description to export",
        )
        level_frame.grid(column=0, row=4, sticky="w", padx=PADX, pady=PADY)
        for row, (key, (text, _)) in enumerate(FTP_LEVELS.items()):
            ttk.Radiobutton(
                level_frame, text=text, variable=self.level, value=key,
            ).grid(column=0, row=row, sticky="w")
        self.level.set("auto")

        self.output_file_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Catcher JSON output file",
        )
        output_frame.grid(column=0, row=5, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.output_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="ew", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=6, sticky="w", padx=PADX, pady=PADY)

    def request_project_names(self) -> None:
        ftp_slug = self.ftp_slug.get()
        if not ftp_slug:
            messagebox.showerror(message="Please enter a FromThePage user slug")
            return
        project_names = request_fromthepage_project_names(ftp_slug)
        self._project_picker["values"] = tuple(project_names)

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose FTP to CONTENTdm field mapping CSV file",
            filetypes=[
                ("CSV", "*.csv"),
                ("TSV", "*.tsv"),
            ],
        )
        if result is not None:
            self.field_mapping_csv_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save Catcher JSON File As",
            defaultextension=".json",
        )
        if result is not None:
            self.output_file_path.set(result)

    def run(self) -> None:
        ftp_slug = self.ftp_slug.get()
        if not ftp_slug:
            messagebox.showerror(message="Please enter a FromThePage user slug")
            return
        ftp_project_name = self.ftp_project_name.get()
        if not ftp_project_name:
            messagebox.showerror(message="Please enter a FromThePage project name")
            return
        field_mapping_csv_path = self.field_mapping_csv_path.get()
        if not field_mapping_csv_path:
            messagebox.showerror(message="Please enter a FTP to CONTENTdm field mapping CSV file")
            return
        _, level = FTP_LEVELS[self.level.get()]
        output_file_path = self.output_file_path.get()
        if not output_file_path:
            messagebox.showerror(message="Please enter a Catcher JSON output file path")
            return
        print(
            textwrap.dedent(f"""\
        ftpstruct2catcher(
            ftp_slug={ftp_slug},
            ftp_project_name={ftp_project_name},
            field_mapping_csv_path={field_mapping_csv_path},
            level={level},
            output_file_path={output_file_path},
        )"""))
        ftpstruct2catcher(
            ftp_slug=ftp_slug,
            ftp_project_name=ftp_project_name,
            field_mapping_csv_path=field_mapping_csv_path,
            level=level,
            output_file_path=output_file_path,
            show_progress=False,
        )


FTP_LEVELS = {
    "auto": ("Autodetect", Level.AUTO),
    "work": ("Work", Level.WORK),
    "page": ("Page", Level.PAGE),
    "both": ("Both", Level.BOTH),
}


class ScanFtpSchema:
    ftp_slug: tk.StringVar
    ftp_project_name: tk.StringVar
    report_path: tk.StringVar
    _project_picker: ttk.Combobox

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="scanftpschema")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=scanftpschema.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.ftp_slug = tk.StringVar()
        slug_frame = ttk.Labelframe(
            frame,
            text="FromThePage user slug",
        )
        slug_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            slug_frame,
            textvariable=self.ftp_slug,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            slug_frame,
            text="Request project names",
            command=self.request_project_names,
        ).grid(column=0, row=1, sticky="w", padx=PADX, pady=PADY)

        self.ftp_project_name = tk.StringVar()
        project_frame = ttk.Labelframe(
            frame,
            text="FromThePage project name",
        )
        project_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        self._project_picker = ttk.Combobox(
            project_frame,
            textvariable=self.ftp_project_name,
            width=COMBO_WIDTH,
        )
        self._project_picker.grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)

        self.report_path = tk.StringVar()
        report_frame = ttk.Labelframe(
            frame,
            text="HTML report output",
        )
        report_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            report_frame,
            textvariable=self.report_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            report_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=4, sticky="w", padx=PADX, pady=PADY)

    def request_project_names(self) -> None:
        ftp_slug = self.ftp_slug.get()
        if not ftp_slug:
            messagebox.showerror(message="Please enter a FromThePage user slug")
            return
        project_names = request_fromthepage_project_names(ftp_slug)
        self._project_picker["values"] = tuple(project_names)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save HTML report as",
            defaultextension=".html",
        )
        if result is not None:
            self.report_path.set(result)

    def run(self) -> None:
        ftp_slug = self.ftp_slug.get()
        if not ftp_slug:
            messagebox.showerror(message="Please enter a FromThePage user slug")
            return
        ftp_project_name = self.ftp_project_name.get()
        if not ftp_project_name:
            messagebox.showerror(message="Please enter a FromThePage project name")
            return
        report_path = self.report_path.get()
        if not report_path:
            messagebox.showerror(message="Please enter an HTML report path")
            return
        print(
            textwrap.dedent(f"""\
        scanftpschema(
            ftp_slug={ftp_slug},
            ftp_project_name={ftp_project_name},
            report_path={report_path},
        )"""))
        scanftpschema(
            ftp_slug=ftp_slug,
            ftp_project_name=ftp_project_name,
            report_path=report_path,
            show_progress=False,
        )


class CdmSchema2Csv:
    cdm_instance_url: tk.StringVar
    cdm_collection_alias: tk.StringVar
    csv_file_path: tk.StringVar
    _alias_picker: ttk.Combobox

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="cdmschema2csv")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=cdmschema2csv.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.cdm_instance_url = tk.StringVar()
        url_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm instance URL",
        )
        url_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            url_frame,
            textvariable=self.cdm_instance_url,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            url_frame,
            text="Request collection aliases",
            command=self.request_aliases,
        ).grid(column=0, row=1, sticky="w", padx=PADX, pady=PADY)

        self.cdm_collection_alias = tk.StringVar()
        alias_frame = ttk.Labelframe(
            frame,
            text="CONTENTdm collection alias",
        )
        alias_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        self._alias_picker = ttk.Combobox(
            alias_frame,
            textvariable=self.cdm_collection_alias,
            width=COMBO_WIDTH,
        )
        self._alias_picker.grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)

        self.csv_file_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Output CSV file",
        )
        output_frame.grid(column=0, row=3, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.csv_file_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=4, sticky="w", padx=PADX, pady=PADY)

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        collection_aliases = request_contentdm_collection_aliases(cdm_instance_url)
        self._alias_picker["values"] = tuple(
            f"{alias}={name}" for name, alias in collection_aliases.items()
        )

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save output CSV file as",
            defaultextension=".csv",
        )
        if result is not None:
            self.csv_file_path.set(result)

    def run(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showerror(message="Please enter a CONTENTdm instance URL")
            return
        cdm_collection_and_alias = self.cdm_collection_alias.get()
        if not cdm_collection_and_alias:
            messagebox.showerror(message="Please enter an CONTENTdm collection alias")
            return
        cdm_collection_alias = cdm_collection_and_alias.rpartition("=")[0]
        csv_file_path = self.csv_file_path.get()
        if not csv_file_path:
            messagebox.showerror(message="Please enter an output CSV file path")
            return
        print(
            textwrap.dedent(f"""\
        cdmschema2csv(
            cdm_instance_url={cdm_instance_url},
            cdm_collection_alias={cdm_collection_alias},
            csv_file_path={csv_file_path},
        )"""))
        cdmschema2csv(
            cdm_instance_url=cdm_instance_url,
            cdm_collection_alias=cdm_collection_alias,
            csv_file_path=csv_file_path,
            show_progress=False,
        )


class Csv2Json:
    input_csv_path: tk.StringVar
    output_json_path: tk.StringVar
    csv_dialect: tk.StringVar
    drop_empty_cells: tk.BooleanVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="csv2json")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=csv2json.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.input_csv_path = tk.StringVar()
        input_frame = ttk.Labelframe(
            frame,
            text="Input CSV file",
        )
        input_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            input_frame,
            textvariable=self.input_csv_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            input_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.output_json_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Output JSON file",
        )
        output_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.output_json_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.csv_dialect = tk.StringVar()
        dialect_frame = ttk.Labelframe(
            frame,
            text="Input CSV dialect",
        )
        dialect_frame.grid(column=0, row=3, sticky="w", padx=PADX, pady=PADY)
        for row, csv_dialect in enumerate(csv.list_dialects()):
            ttk.Radiobutton(
                dialect_frame,
                text=csv_dialect,
                variable=self.csv_dialect,
                value=csv_dialect,
            ).grid(column=0, row=row, sticky="w")
        self.csv_dialect.set("google-csv")

        self.drop_empty_cells = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Drop empty cells",
            variable=self.drop_empty_cells,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=4, sticky="w", padx=PADX, pady=PADY)

        ttk.Button(
            frame,
            text="Run",
            command=self.run
        ).grid(column=0, row=5, sticky="w", padx=PADX, pady=PADY)

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose input CSV file name",
            filetypes=[
                ("CSV", "*.csv"),
                ("TSV", "*.tsv"),
            ],
        )
        if result is not None:
            self.input_csv_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save JSON File As",
            defaultextension=".json",
        )
        if result is not None:
            self.output_json_path.set(result)

    def run(self) -> None:
        input_csv_path = self.input_csv_path.get()
        if not input_csv_path:
            messagebox.showerror(message="Please enter an input CSV file path")
            return
        output_json_path = self.output_json_path.get()
        if not output_json_path:
            messagebox.showerror(message="Please enter an output JSON file path")
            return
        csv_dialect = self.csv_dialect.get()
        drop_empty_cells = self.drop_empty_cells.get()
        print(
            textwrap.dedent(f"""\
        csv2json(
            input_csv_path={input_csv_path},
            output_json_path={output_json_path},
            csv_dialect={csv_dialect},
            drop_empty_cells={drop_empty_cells},
        )"""))
        csv2json(
            input_csv_path=input_csv_path,
            output_json_path=output_json_path,
            csv_dialect=csv_dialect,
            drop_empty_cells=drop_empty_cells,
            show_progress=False,
        )


class Json2Csv:
    input_json_path: tk.StringVar
    output_csv_path: tk.StringVar
    csv_dialect: tk.StringVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="json2csv")

        help_frame = ttk.Labelframe(frame, text="Help")
        help_frame.grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)
        ttk.Label(
            help_frame,
            text=json2csv.__doc__ or "",
            wraplength=HELP_LABEL_WRAP,
        ).grid(column=0, row=0, sticky="nsew", padx=PADX, pady=PADY)

        self.input_json_path = tk.StringVar()
        input_frame = ttk.Labelframe(
            frame,
            text="Input JSON file",
        )
        input_frame.grid(column=0, row=1, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            input_frame,
            textvariable=self.input_json_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            input_frame,
            text="Browse...",
            command=self.choose_input,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.output_csv_path = tk.StringVar()
        output_frame = ttk.Labelframe(
            frame,
            text="Output CSV file",
        )
        output_frame.grid(column=0, row=2, sticky="ew", padx=PADX, pady=PADY)
        ttk.Entry(
            output_frame,
            textvariable=self.output_csv_path,
            width=ENTRY_WIDTH,
        ).grid(column=0, row=0, sticky="w", padx=PADX, pady=PADY)
        ttk.Button(
            output_frame,
            text="Save as...",
            command=self.choose_output,
        ).grid(column=1, row=0, sticky="w", padx=PADX, pady=PADY)

        self.csv_dialect = tk.StringVar()
        dialect_frame = ttk.Labelframe(
            frame,
            text="Output CSV dialect",
        )
        dialect_frame.grid(column=0, row=5, sticky="w", padx=PADX, pady=PADY)
        for row, csv_dialect in enumerate(csv.list_dialects()):
            ttk.Radiobutton(
                dialect_frame,
                text=csv_dialect,
                variable=self.csv_dialect,
                value=csv_dialect
            ).grid(column=0, row=row, sticky="w")
        self.csv_dialect.set("google-csv")

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=6, sticky="w", padx=PADX, pady=PADY)

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose input JSON file",
            filetypes=[
                ("JSON", "*.json"),
            ],
        )
        if result is not None:
            self.input_json_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Save output CSV file as",
            defaultextension=".csv",
        )
        if result is not None:
            self.output_csv_path.set(result)

    def run(self) -> None:
        input_json_path = self.input_json_path.get()
        if not input_json_path:
            messagebox.showerror(message="Please enter an input JSON file path")
            return
        output_csv_path = self.output_csv_path.get()
        if not output_csv_path:
            messagebox.showerror(message="Please enter an output CSV file path")
            return
        csv_dialect = self.csv_dialect.get()
        print(
            textwrap.dedent(f"""\
        json2csv(
            input_json_path={input_json_path},
            output_csv_path={output_csv_path},
            csv_dialect={csv_dialect}
        )"""))
        json2csv(
            input_json_path=input_json_path,
            output_csv_path=output_csv_path,
            csv_dialect=csv_dialect,
            show_progress=False,
        )


def request_contentdm_collection_aliases(cdm_instance_url: str) -> Dict[str, str]:
    print("Requesting CONTENTdm collection aliases...")
    with requests.Session() as session:
        cdm_collection_list = cdm_api.request_collection_list(
            instance_url=cdm_instance_url,
            session=session,
        )
    print("Done")
    return {
        info.name: info.alias.lstrip("/") for info in cdm_collection_list
    }


class ShortFieldInfo(NamedTuple):
    name: str
    nick: str
    vocab: bool


def request_contentdm_field_info(cdm_instance_url: str, cdm_collection_alias: str) -> List[cdm_api.CdmFieldInfo]:
    print("Requesting CONTENTdm field info...")
    with requests.Session() as session:
        field_infos = cdm_api.request_field_infos(
            instance_url=cdm_instance_url,
            collection_alias=cdm_collection_alias,
            session=session,
        )
        print("Done")
        return field_infos


def request_fromthepage_project_names(ftp_slug: str) -> List[str]:
    print("Requesting FromThePage project names...")
    with requests.Session() as session:
        ftp_instance = ftp_api.FtpInstance(
            url=ftp_api.FTP_HOSTED_URL,
        )
        ftp_project_collection = ftp_instance.request_projects(
            slug=ftp_slug,
            session=session,
        )
        print("Done")
        return [project.label for project in ftp_project_collection.projects]


def get_nicks_from_edit(path: str) -> List[str]:
    with open(path, mode="r", encoding="utf-8") as fp:
        catcher_edits = json.load(fp)
    nicks: List[str] = []
    for edit in catcher_edits:
        for nick in edit:
            if nick not in nicks:
                nicks.append(nick)
    nicks.remove("dmrecord")
    return nicks


def is_lcsh_guess(fieldname: str) -> bool:
    return "LCSH" in fieldname or "LCNAF" in fieldname


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


if __name__ == "__main__":
    raise SystemExit(gui())
