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
from cdm_util_scripts.csv2json import csv2json
from cdm_util_scripts.json2csv import json2csv
from cdm_util_scripts.ftptransc2catcher import ftptransc2catcher
from cdm_util_scripts.ftpstruct2catcher import ftpstruct2catcher, Level
from cdm_util_scripts.scanftpschema import scanftpschema

from typing import Dict, List, NamedTuple


def gui() -> int:
    root = tk.Tk()
    root.title("cdm-util-scripts")

    Console(root)

    notebook = ttk.Notebook(root)

    CatcherDiff(notebook)
    CatcherCombineTerms(notebook)
    CatcherTidy(notebook)
    Csv2json(notebook)
    Json2csv(notebook)

    notebook.grid(column=0, row=1, sticky="nsew")
    root.mainloop()

    return 0


# https://stackoverflow.com/questions/68198575/how-can-i-displaymy-console-output-in-tkinter
class Console:
    def __init__(self, parent) -> None:
        frame = ttk.Labelframe(parent, text="Console Log")
        frame.grid(column=0, row=0, sticky="nsew")
        console = scrolledtext.ScrolledText(
            frame,
            height=10, width=80, font=("consolas", "8", "normal"),
        )
        console.grid(column=0, row=0, sticky="nsew")
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
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="catcherdiff")

        frame_help = ttk.Labelframe(frame, text="Help")
        frame_help.grid(column=0, row=0, sticky="nsew")
        ttk.Label(
            frame_help,
            text=catcherdiff.__doc__,
        ).grid(column=0, row=0, sticky="nsew")

        self.cdm_instance_url = tk.StringVar()
        ttk.Label(frame, text="CONTENTdm instance URL").grid(column=0, row=1, sticky="w")
        ttk.Entry(frame, textvariable=self.cdm_instance_url).grid(column=0, row=2, sticky="ew")
        ttk.Button(frame, text="Request collection aliases", command=self.request_aliases).grid(column=0, row=3, sticky="w")

        self.cdm_collection_alias = tk.StringVar()
        ttk.Label(frame, text="CONTENTdm collection alias").grid(column=0, row=4, sticky="w")
        self._alias_picker = ttk.Combobox(frame, textvariable=self.cdm_collection_alias)
        self._alias_picker.grid(column=0, row=5, sticky="ew")

        self.catcher_json_file_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.catcher_json_file_path,
        ).grid(column=0, row=6, sticky="ew")
        ttk.Button(
            frame,
            text="Choose Catcher JSON file...",
            command=self.choose_input,
        ).grid(column=0, row=7, sticky="w")

        self.report_file_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.report_file_path,
        ).grid(column=0, row=8, sticky="ew")
        ttk.Button(
            frame,
            text="Save HTML Report As...",
            command=self.choose_output,
        ).grid(column=0, row=9, sticky="w")

        self.check_vocabs = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Check vocabs",
            variable=self.check_vocabs,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=10, sticky="w")

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=11, sticky="w")

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showinfo(message="Please enter a CONTENTdm instance URL")
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
            messagebox.showinfo(message="Please provide a CONTENTdm instance URL")
            return
        cdm_collection_and_alias = self.cdm_collection_alias.get()
        if not cdm_collection_and_alias:
            messagebox.showinfo(message="Please provide an CONTENTdm collection alias")
            return
        cdm_collection_alias = cdm_collection_and_alias.rpartition("=")[0]
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showinfo(message="Please provide a Catcher JSON file")
            return
        report_file_path = self.report_file_path.get()
        if not report_file_path:
            messagebox.showinfo(message="Please provide an HTML report file path")
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

        frame_help = ttk.Labelframe(frame, text="Help")
        frame_help.grid(column=0, row=0, sticky="nsew")
        ttk.Label(
            frame_help,
            text=catchercombineterms.__doc__,
        ).grid(column=0, row=0, sticky="nsew")

        self.cdm_instance_url = tk.StringVar()
        ttk.Label(frame, text="CONTENTdm instance URL").grid(column=0, row=1, sticky="w")
        ttk.Entry(frame, textvariable=self.cdm_instance_url).grid(column=0, row=2, sticky="ew")
        ttk.Button(
            frame,
            text="Request collection aliases",
            command=self.request_aliases
        ).grid(column=0, row=3, sticky="w")

        self.cdm_collection_alias = tk.StringVar()
        ttk.Label(frame, text="CONTENTdm collection alias").grid(column=0, row=4, sticky="w")
        self._alias_picker = ttk.Combobox(frame, textvariable=self.cdm_collection_alias)
        self._alias_picker.grid(column=0, row=5, sticky="ew")

        self.catcher_json_file_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.catcher_json_file_path,
        ).grid(column=0, row=6, sticky="ew")
        ttk.Button(
            frame,
            text="Choose Catcher JSON file...",
            command=self.choose_input,
        ).grid(column=0, row=7, sticky="w")

        self.output_file_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.output_file_path,
        ).grid(column=0, row=8, sticky="ew")
        ttk.Button(
            frame,
            text="Save Combined Catcher JSON As...",
            command=self.choose_output,
        ).grid(column=0, row=9, sticky="w")

        self.sort_terms = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Sort Terms",
            variable=self.sort_terms,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=10, sticky="w")

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=11, sticky="w")

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showinfo(message="Please enter a CONTENTdm instance URL")
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
            messagebox.showinfo(message="Please provide a CONTENTdm instance URL")
            return
        cdm_collection_and_alias = self.cdm_collection_alias.get()
        if not cdm_collection_and_alias:
            messagebox.showinfo(message="Please provide an CONTENTdm collection alias")
            return
        cdm_collection_alias = cdm_collection_and_alias.partition("=")[0]
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showinfo(message="Please provide a Catcher JSON file path")
            return
        output_file_path = self.output_file_path.get()
        if not output_file_path:
            messagebox.showinfo(message="Please provide a Combined Catcher JSON file path")
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

        frame_help = ttk.Labelframe(frame, text="Help")
        frame_help.grid(column=0, row=0, sticky="nsew")
        ttk.Label(
            frame_help,
            text=catchertidy.__doc__,
        ).grid(column=0, row=0, sticky="nsew")

        self.cdm_instance_url = tk.StringVar()
        ttk.Label(frame, text="CONTENTdm instance URL").grid(column=0, row=1, sticky="w")
        ttk.Entry(frame, textvariable=self.cdm_instance_url).grid(column=0, row=2, sticky="ew")
        ttk.Button(
            frame,
            text="Request collection aliases",
            command=self.request_aliases
        ).grid(column=0, row=3, sticky="w")

        self.cdm_collection_alias = tk.StringVar()
        ttk.Label(frame, text="CONTENTdm collection alias").grid(column=0, row=4, sticky="w")
        self._alias_picker = ttk.Combobox(frame, textvariable=self.cdm_collection_alias)
        self._alias_picker.grid(column=0, row=5, sticky="ew")

        self.catcher_json_file_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.catcher_json_file_path,
        ).grid(column=0, row=6, sticky="ew")
        ttk.Button(
            frame,
            text="Choose Catcher JSON File...",
            command=self.choose_input,
        ).grid(column=0, row=7, sticky="w")

        self._tidy_ops_frame = ttk.Labelframe(frame, text="Tidy Operations")
        self._tidy_ops_frame.grid(column=1, row=0, rowspan=12)
        self._tidy_ops_rows = []
        ttk.Button(
            frame,
            text="Configure Tidy Operations...",
            command=self.configure_tidy_operations,
        ).grid(column=0, row=8, sticky="w")

        self.output_file_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.output_file_path,
        ).grid(column=0, row=9, sticky="ew")
        ttk.Button(
            frame,
            text="Save Tidy Catcher JSON As...",
            command=self.choose_output,
        ).grid(column=0, row=10, sticky="w")

        self.lcsh_separator_spaces = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Insert subfield separator spaces in normalized LCSH",
            variable=self.lcsh_separator_spaces,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=11, sticky="w")

        ttk.Button(
            frame,
            text="Run",
            command=self.run,
        ).grid(column=0, row=12, sticky="w")

    def request_aliases(self) -> None:
        cdm_instance_url = self.cdm_instance_url.get()
        if not cdm_instance_url:
            messagebox.showinfo(message="Please enter a CONTENTdm instance URL")
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
            messagebox.showinfo(message="Please enter a Catcher JSON file path")
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
        for child in self._tidy_ops_frame.winfo_children():
            child.destroy()

        for row, field_info in enumerate(short_field_infos):
            ops = TidyOpsRow.from_short_info(field_info)
            self._tidy_ops_rows.append(ops)
            ops.add(self._tidy_ops_frame, row=row)

    def run(self) -> None:
        catcher_json_file_path = self.catcher_json_file_path.get()
        if not catcher_json_file_path:
            messagebox.showinfo(message="Please provide a Catcher JSON file path")
            return
        output_file_path = self.output_file_path.get()
        if not output_file_path:
            messagebox.showinfo(message="Please provide a tidied Catcher JSON file path")
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

    def add(self, parent: ttk.Labelframe, row: int) -> None:
        ttk.Checkbutton(parent, text="whitespace", variable=self.whitespace).grid(column=0, row=row, sticky="w")
        ttk.Checkbutton(parent, text="quotes", variable=self.quotes).grid(column=1, row=row, sticky="w")
        ttk.Checkbutton(parent, text="lcsh", variable=self.lcsh).grid(column=2, row=row, sticky="w")
        ttk.Checkbutton(parent, text="sort", variable=self.sort).grid(column=3, row=row, sticky="w")
        ttk.Label(parent, text=self.name).grid(column=4, row=row, sticky="w")


class Csv2json:
    input_csv_path: tk.StringVar
    output_json_path: tk.StringVar
    csv_dialect: tk.StringVar
    drop_empty_cells: tk.BooleanVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="csv2json")

        frame_help = ttk.Labelframe(frame, text="Help")
        frame_help.grid(column=0, row=0, sticky="nsew")
        ttk.Label(
            frame_help,
            text=csv2json.__doc__,
        ).grid(column=0, row=0, sticky="nsew")

        self.input_csv_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.input_csv_path,
        ).grid(column=0, row=1, sticky="ew")
        ttk.Button(
            frame,
            text="Choose Input CSV File...",
            command=self.choose_input
        ).grid(column=0, row=2, sticky="w")

        self.output_json_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.output_json_path,
        ).grid(column=0, row=3, sticky="ew")
        ttk.Button(
            frame,
            text="Save JSON File As...",
            command=self.choose_output
        ).grid(column=0, row=4, sticky="w")

        self.csv_dialect = tk.StringVar()
        for row, csv_dialect in enumerate(csv.list_dialects(), start=5):
            ttk.Radiobutton(
                frame,
                text=csv_dialect,
                variable=self.csv_dialect,
                value=csv_dialect
            ).grid(column=0, row=row, sticky="w")
        self.csv_dialect.set("google-csv")

        self.drop_empty_cells = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Drop empty cells",
            variable=self.drop_empty_cells,
            onvalue=True,
            offvalue=False,
        ).grid(column=0, row=row + 1, sticky="w")

        ttk.Button(
            frame,
            text="Run",
            command=self.run
        ).grid(column=0, row=row + 2, sticky="w")

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
            messagebox.showinfo(message="Please provide an input CSV file path")
            return
        output_json_path = self.output_json_path.get()
        if not output_json_path:
            messagebox.showinfo(message="Please provide an output JSON file path")
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


class Json2csv:
    input_json_path: tk.StringVar
    output_csv_path: tk.StringVar
    csv_dialect: tk.StringVar

    def __init__(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="json2csv")

        frame_help = ttk.Labelframe(frame, text="Help")
        frame_help.grid(column=0, row=0, sticky="nsew")
        ttk.Label(
            frame_help,
            text=json2csv.__doc__,
        ).grid(column=0, row=0, sticky="nsew")

        self.input_json_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.input_json_path,
        ).grid(column=0, row=1, sticky="ew")
        ttk.Button(
            frame,
            text="Choose input JSON file...",
            command=self.choose_input
        ).grid(column=0, row=2, sticky="w")

        self.output_csv_path = tk.StringVar()
        ttk.Entry(
            frame,
            textvariable=self.output_csv_path,
        ).grid(column=0, row=3, sticky="ew")
        ttk.Button(
            frame,
            text="Save CSV file as...",
            command=self.choose_output
        ).grid(column=0, row=4, sticky="w")

        self.csv_dialect = tk.StringVar()
        for row, csv_dialect in enumerate(csv.list_dialects(), start=5):
            ttk.Radiobutton(
                frame,
                text=csv_dialect,
                variable=self.csv_dialect,
                value=csv_dialect
            ).grid(column=0, row=row, sticky="w")
        self.csv_dialect.set("google-csv")

        ttk.Button(
            frame,
            text="Run",
            command=self.run
        ).grid(column=0, row=row + 1, sticky="w")

    def choose_input(self) -> None:
        result = filedialog.askopenfilename(
            title="Choose input JSON file name",
            filetypes=[
                ("JSON", "*.json"),
            ],
        )
        if result is not None:
            self.input_json_path.set(result)

    def choose_output(self) -> None:
        result = filedialog.asksaveasfilename(
            title="Choose output CSV file name",
            defaultextension=".csv",
        )
        if result is not None:
            self.output_csv_path.set(result)

    def run(self) -> None:
        input_json_path = self.input_json_path.get()
        if not input_json_path:
            messagebox.showinfo(message="Please provide an input JSON file path")
            return
        output_csv_path = self.output_csv_path.get()
        if not output_csv_path:
            messagebox.showinfo(message="Please provide an output CSV file path")
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


if __name__ == "__main__":
    raise SystemExit(gui())
