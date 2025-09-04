# cdm-util-scripts

cdm-util-scripts are Python tools developed to support Ohio University Libraries' CONTENTdm operations.

cdm-util-scripts has two interfaces, a CLI (Command Line Interface) and a GUI (Graphical User Interface) that both offer the same functionality:
* [catcherdiff](#catcherdiff): generates a HTML report on what CONTENTdm field values will change if a cdm-catcher JSON edit is implemented.
* [catchercombineterms](#catchercombineterms): combines a cdm-catcher JSON edit of controlled vocabulary fields with terms currently in CONTENTdm.
* [catchertidy](#catchertidy): tidies up cdm-catcher JSON edits, including options for normalizing whitespace, replacing Microsoft Word smart characters, and sorting controlled vocabularies.
* [scanftpschema](#scanftpschema): generates a HTML report on the Metadata Fields/Transcription Fields schema(s) in a FromThePage project.
* [ftpstruct2catcher](#ftpstruct2catcher): requests FromThePage Metadata Fields and/or Transcription Fields data as cdm-catcher JSON edits.
* [ftptransc2catcher](#ftptransc2catcher): requests transcripts from FromThePage works corresponding to manifest URLs listed in a text file as cdm-catcher JSON edits.
* [json2csv](#json2csv): transposes a list of JSON objects (cdm-catcher JSON edits) into a CSV file.
* [csv2json](#csv2json): transposes a CSV file into a list of JSON objects (cdm-catcher JSON edits).

## Installation

To run cdm-util-scripts, you need Python 3 version 3.7 or later installed and available on a command line. While cdm-util-scripts has a GUI interface, it still has to be installed and launched from the command line at this time. You should be able to use any of Windows' Command Prompt, Git Bash on Windows, or macOS's Terminal to run cdm-util-scripts.

First, check that Python 3.7 or later is available. On Command Prompt:

```console
C:\Users\username>python3 --version
Python 3.7.12

```

On Git Bash or macOS Terminal (`$` is the prompt used here but yours might be different):

```console
$ python3 --version
Python 3.7.12
```

Some systems might use `py` or `python` instead of `python3`. cdm-util-scripts is best installed using a Python [virtual environment](https://docs.python.org/3/tutorial/venv.html) that makes `cdmutil` available as a command and can be switched on and off to avoid interfering with other Python software. To do this, the following commands can be executed in Windows' Command Prompt, where `username` is your username and cdm-util-scripts could be any subdirectory of your choice:

```console
C:\Users\username>mkdir cdm-util-scripts

C:\Users\username>cd cdm-util-scripts

C:\Users\username>python3 -m venv env

C:\Users\username>env\Scripts\activate

(env) C:\Users\username>python3 -m pip install git+https://github.com/OU-Libraries/cdm-util-scripts@main
```

The following slightly different commands can be used on macOS Terminal or Linux:

```console
$ mkdir cdm-util-scripts
$ cd cdm-util-scripts
$ python3 -m venv env
$ source env/bin/activate
(env) $ python3 -m pip install git+https://github.com/OU-Libraries/cdm-util-scripts@main
```

And the following also slightly different commands can be used on Git Bash on Windows:

```console
$ mkdir cdm-util-scripts
$ cd cdm-util-scripts
$ python3 -m venv env
$ source env/Scripts/activate
(env) $ python3 -m pip install git+https://github.com/OU-Libraries/cdm-util-scripts@main
```


You can see the virtual environment is active and `cdmutil` is available because of the `(env)` prefix on the command line prompt. To check to see if everything is working, run:

    cdmutil --help

should print help information. `cdmutil` will now be available in any directory in your command line as long as the virtual environment is active. You can deactivate the virtual environment with:

    deactivate

You can reactivate the virtual environment from the `cdm-util-scripts` directory (or wherever `env` is) to regain access to the scripts:

    env/Scripts/activate

or `source env/bin/activate` on Linux and macOS.

## Update

To update `cdm-util-scripts` just reinstall the package while its virtual environment is active:

    python -m pip install git+https://github.com/OU-Libraries/cdm-util-scripts@main

## cdm-catcher

Several cdm-util-scripts are intended for use with [cdm-catcher](https://github.com/Baledin/cdm-catcher). As of cdm-catcher's May 27th, 2020 commit (`ede517f`), you can install it by cloning its GitHub repo and installing its requirements (shown here using a Windows virtual environment):

    git clone https://github.com/Baledin/cdm-catcher
    cd cdm-catcher
    python3 -m venv env
    source env/Scripts/activate
    python3 -m pip install -r requirements.txt

It should be configured according to its instructions. It can then be invoked from its cloned cdm-catcher directory.

## The GUI interface

The cdm-util-scripts GUI can be launched using:

```console
$ cdmutil gui
```

The GUI window should then popup on your desktop. Most of its functionality and arguments are the same as the CLI interface documented below, except that instead of providing the `cdminfo` and `ftpinfo` subcommands there are `Request collection aliases` and `Request project names` buttons that fill the FromThePage project names and CONTENTdm collection aliases combo boxes on request, and `cdmschema2csv` which jump starts a column mapping CSV with CONTENTdm field names and nicks.

Because the GUI interface is an overlay on the CLI functionality without a GUI progress reporting mechanism, Windows will often designate cdm-util-scripts as "Non Responsive" during long runs even when they're not hung or frozen.

## The CLI interface

cdm-util-scripts CLI interface provides command `cdmutil` with the following subcommands.

(`head` is a macOS/Linux command that prints the top of a text file used occasionally in the following console examples to show file inputs and outputs.)

<a name="cdminfo"/>

### cdminfo

`cdminfo` takes a CONTENTdm instance URL and prints collections and field metadata. If given only a repository base URL it will print collection data for that repository, if also passed the `-a` option with a collection alias, it will print the field information for that collection. This script is intended to be useful for looking up collection aliases and field nicknames for use with other cdm-util-scripts.


For a CONTENTdm instance:

```console
$ cdmutil cdminfo https://cdmdemo.contentdm.oclc.org/
          alias : '/oclcsample'
           name : 'An OCLC Sample Collection'
           path : '/cdm/sites/15700/data/oclcsample'
secondary_alias : 'oclcsample'

          alias : '/myfirstcollection'
           name : 'My First Collection'
           path : '/cdm/sites/15700/data/myfirstcollection'
secondary_alias : 'myfirstcollection'

...
```

For a CONTENTdm collection:

```console
$ cdmutil cdminfo https://cdmdemo.contentdm.oclc.org/ -a oclcsample
    name : 'Title'
    nick : 'title'
    type : 'TEXT'
    size : 0
    find : 'a0'
     req : 1
  search : 1
    hide : 0
   vocdb : ''
   vocab : 0
      dc : 'Title'
   admin : 0
readonly : 0

    name : 'Subject'
    nick : 'subjec'
    type : 'TEXT'
    size : 0
    find : 'a5'
     req : 0
  search : 1
    hide : 0
   vocdb : 'LCTGM'
   vocab : 1
      dc : 'Subject'
   admin : 0
readonly : 0

...
```

`cdminfo` can be used to jump start a CONTENTdm nickname mapping CSV required for `cdmutil` 2catcher subcommands, as:

```console
$ cdmutil cdminfo https://media.library.ohio.edu -a p15808coll19 -f csv -c name,nick > farfel-mapping.csv
$ head farfel-mapping.csv
name,nick
Title,title
Source title - LCSH,sourca
Author/ editor - LCSH,creato
Collection,colleb
Subcollection,collec
Part of,part
Leaf identifier,farfel
Ege number,ege
Container,is
```

<a name="ftpinfo"/>

### ftpinfo

`ftpinfo` takes a FromThePage user slug (like `ohiouniversitylibraries`) and prints the projects available from that user on fromthepage.com. It is intended to be helpful for getting exact collection/project names for FromThePage projects for use as parameters in other subcommands:

```console
$ cdmutil ftpinfo ohiouniversitylibraries
  @id : 'https://fromthepage.com/iiif/collection/ohio-university-board-of-trustees-minutes'
label : 'Board of Trustees minutes, Ohio University'

  @id : 'https://fromthepage.com/iiif/collection/cornelius-ryan-collection-of-world-war-ii-papers'
label : 'Cornelius Ryan Collection of World War II Papers'

  @id : 'https://fromthepage.com/iiif/collection/william-e-peters-papers'
label : 'William E. Peters Papers'

...
```

<a name="scanftpschema"/>

### scanftpschema

`scanftpschema` takes
* A FromThePage user slug
* A FromThePage project label
* A HTML report output file path

and outputs a detailed report on the field schemas currently in use in that FromThePage project. FromThePage's field-based transcription and Metadata Creation tools can end up using different schema for works in a FromThePage project if that feature's configuration is changed during a transcription project. The `scanftpschema` report is intended to be useful for ensuring schema consistency inside of a collection, and is especially useful for checking if a FromThePage project will be fully loaded into CONTENTdm using `ftpstruct2catcher`.

Example:
```console
$ cdmutil scanftpschema ohiouniversitylibraries "Farfel Leaves Metadata" farfel-fields-report.html
Requesting FromThePage project data...
Requesting FromThePage project structured data configuration...
Requesting FromThePage project work data...
100%|███████████████████████████████████| 59/59 [00:10<00:00,  5.37it/s]
Requesting FromThePage project structured descriptions...
100%|███████████████████████████████████| 59/59 [00:08<00:00,  6.58it/s]
Collating field sets...
Compiling report...
```

The HTML report can then be reviewed by opening it in a web browser.

<a name="catcherdiff"/>

### catcherdiff

`catcherdiff` takes
* A CONTENTdm instance URL
* A CONTENTdm collection alias
* A cdm-catcher `edit` action JSON file
* An HTML report output file name

and outputs an HTML report showing on a per-item basis what fields would be changed in a CONTENTdm collection if that cdm-catcher JSON file were used in a cdm-catcher `edit` action. This script is intended to be useful for cross-checking the output of the 2catcher series of subcommands and checking to see if a Catcher edit action has been completely implemented by the Catcher service.

Because Catcher trims leading and trailing whitespace from applied edits, `catcherdiff` ignores it when comparing values.

```console
$ cdmutil catcherdiff https://media.library.ohio.edu p15808coll19 catcher-edits.json report.html
Requesting CONTENTdm field info...
Requesting CONTENTdm item info...
100%|███████████████████████████████████| 59/59 [00:05<00:00, 10.42it/s]
catcherdiff found 59 out of 59 total edit actions would change at least one field.
```

Optionally, the `-c` (or `--check-vocabs`) flag can be used, which will add a list to each controlled vocabulary field edit indicating if its terms are in that field's controlled vocabulary:

```console
$ catcherdiff -c https://media.library.ohio.edu p15808coll19 catcher-edits.json report.html
Requesting CONTENTdm field info...
Requesting CONTENTdm item info...
100%|███████████████████████████████████| 59/59 [00:05<00:00, 11.65it/s]
Requesting CONTENTdm controlled vocabularies...
Requesting 'Source title - LCSH' vocab...
Requesting 'Author/ editor - LCSH' vocab...
Requesting 'Collection' vocab...
Requesting 'Subcollection' vocab...
Requesting 'Part of' vocab...
Requesting 'Leaf identifier' vocab...
Requesting 'Ege number' vocab...
Requesting 'Container' vocab...
Requesting 'Printer/ publisher - LCSH' vocab...
Requesting 'Scribe - LCSH' vocab...
Requesting 'Translator - LCSH' vocab...
Requesting 'Artist/ engraver - LCSH' vocab...
Requesting 'Commissioner/ bookseller - LCSH' vocab...
Requesting 'Previous owner' vocab...
Requesting 'Primary language(s)' vocab...
Requesting 'Creation location - modern country' vocab...
Requesting 'Creation location - modern city' vocab...
Requesting 'Century' vocab...
Requesting 'Creation date' vocab...
Requesting 'Document genre - AAT' vocab...
Requesting 'Features - AAT' vocab...
Requesting 'Materials (substrate) - AAT' vocab...
Requesting 'Letterform type - AAT' vocab...
Requesting 'Repository' vocab...
Requesting 'Rights' vocab...
Requesting 'RightsStatements.org URI' vocab...
catcherdiff found 59 out of 59 total edit actions would change at least one field.
```

The HTML report can then be reviewed by opening it in a web browser.

<a name="catchercombineterms"/>

### catchercombineterms

`catchercombineterms` takes:
* A CONTENTdm instance URL
* A CONTENTdm collection alias
* A cdm-catcher `edit` action JSON file which edits _only_ controlled vocabulary fields
* An output file name

and outputs a JSON file containing the controlled vocabulary terms from the input cdm-catcher edits combined with the existing terms in those CONTENTdm fields. It is intended to allow terms to be added to CONTENTdm controlled vocabulary fields given that Catcher only overwrites field values. Terms are de-duplicated and sorted alphabetically default, but the optional `-u` flag (or unchecking the "Sort terms" box in the GUI) can be used to append new terms instead of sorting them.

Example usage:

```console
$ head  -n 12 farfel-leaves-metadata-edits.json
[
  {
    "dmrecord": "3001",
    "langua": "German; Latin",
    "docume": "Incunabula"
  },
  {
    "dmrecord": "3012",
    "langua": "Latin",
    "docume": "Comedies (literary works); Drama (literary genre); Incunabula",
    "featur": "Glosses (annotations); Illustrations (layout features); Marginalia (annotations); Woodcuts (prints)"
  },
$ cdmutil catchercombineterms https://media.library.ohio.edu/ p15808coll19 farfel-leaves-metadata-edits.json farfel-leaves-metadata-edits-combined.json
Requesting CONTENTdm item info...
100%|███████████████████████████████████| 59/59 [00:06<00:00,  9.26it/s]
$ head -n 12 farfel-leaves-metadata-edits-combined.json
[
  {
    "dmrecord": "3001",
    "langua": "German; Latin",
    "docume": "Incunabula"
  },
  {
    "dmrecord": "3012",
    "langua": "Latin",
    "docume": "Comedies (literary works); Drama (literary genre); Incunabula; Printed materials (object genre)",
    "featur": "Glosses (annotations); Illustrations (layout features); Marginalia (annotations); Woodcuts (prints)"
  },
```

<a name="catchertidy"/>

### catchertidy

Unlike the other cdm-util-scripts, `catchertidy` GUI and CLI interfaces differ in their inputs because the GUI has a configuration feature that reconciles field nicks with field metadata not present in the CLI. The GUI `catchertidy` interface takes:
* An optional CONTENTdm instance URL
* An optional CONTENTdm collection alias
* A cdm-catcher `edit` action JSON file
* A tidy operations configuration initiated by the `Configure Tidy Operations...` button
* An output file name

and outputs a tidied `cdm-catcher` JSON file with the configured tidy operations performed on the specified fields.

The tidy operations `Configure Tidy Operations...` button initiates a pop-up window with a list of field names with checkboxes corresponding to the available tidy operations. If the user has provided both the optional CONTENTdm URL and collection alias, cdm-util-scripts will request that collection's field information from CONTENTdm and use it to initialize the tidy operations configuration with operation defaults and full field names. If the URL and alias are not provided, only the field nicks in the Catcher edit will appear in the tidy operations configuration table and only `Quotes` and `Whitespace` will be checked by default.

There are four tidy operations:

- `Whitespace` (GUI), `-w` / `--normalize-whitespace` (CLI): reduces all whitespace (newlines, tabs, double spaces etc.) to single spaces between words
- `Quotes` (GUI), `-r` / `--replace-smart-chars` (CLI): replaces smart characters frequently inserted into text by Microsoft Word:
  - `‘` and `’` become `'`
  - `“` and `”` become `"`
  - `—` (em dash) becomes `--`
  - `–` (en dash) becomes `-`
- `LCSH` (GUI), `-l` / `--normalize-lcsh` (CLI): inserts single spaces between `--` divided subfields in LCSH and LCNAF terms
- `Sort` (GUI), `-s` / `--sort-terms` (CLI): lexically sort controlled vocabulary terms separated by `;`

`LCSH` / `--normalize-lcsh` also normalizes whitespace and replaces smart characters. `Sort` / `--sort-terms` also normalizes whitespace between terms.

The `catchertidy` CLI takes:
* Zero or more tidy operation options with field nicks as arguments
* A cdm-catcher `edit` action JSON file path
* An output file path

and outputs a tidied `cdm-catcher` JSON file with the configured operations performed on the specified fields.

The CLI interface offers "compound" tidy operation options that run more than one tidy operation on the specified edit nick argument, such as `--wr`, which both tidies white space and replaces smart characters. `cdmutil catchertidy --help` shows the full list of compound options.

Example usage:

``` console
$ head edit.json
[
  {
    "dmrecord": "1",
    "origin": "This string has “smart” quotes",
    "series": "7.\tPress and   promotion\n",
    "locati": "Zanesville (Ohio); Athens (Ohio)--Social life and customs"
  }
]
$ cdmutil catchertidy --wr origin --wr series --wrls locati edit.json edit-tidy.json
$ head dance-edit-tidy.json
[
  {
    "dmrecord": "1",
    "origin": "This string has \"smart\" quotes",
    "series": "7. Press and promotion",
    "locati": "Athens (Ohio) -- Social life and customs; Zanesville (Ohio)"
  }
]
```

<a name="ftpstruct2catcher"/>

### ftpstruct2catcher

`ftpstruct2catcher` takes
* A FromThePage user slug
* A FromThePage project label
* A CSV mapping FromThePage field labels to CONTENTdm collection field nicknames
* An output file name

and outputs a JSON file containing field data from FromThePage project for use with cdm-catcher's `edit` action.

The FromThePage project _must_ have been imported from CONTENTdm (so that FromThePage stored the corresponding CONTENTdm object URLs).

* The column mapping CSV must have two columns named `name` and `nick` indicating which FromThePage field `name`s correspond to which CONTENTdm fields (`nick`s). Other columns will be ignored.
* Multiple rows in the column mapping CSV with the same CONTENTdm field nickname in `nick` will have their corresponding field values joined with a semicolon.
* Multiple rows in the column mapping CSV with the same FromThePage field `name` will have their corresponding values appended with a semicolon to each of the CONTENTdm fields specified in their `nick`s.

Example of a column mapping CSV mapping multiple FromThePage fields to single CONTENTdm fields:

```CSV
name,nick
"Work Title",identi
"Respondent name (last, first middle) (text)",creato
"Respondent nationality (text)",respoa
"Respondent branch of service (text)",respon
"Respondent rank (text)",respod
"Rank, if other (text)",respod
"Respondent formation (examples include divisions and corps) (text)",respob
"Formation, if other (text)",respob
"Respondent unit (examples include battalions, brigades, regiments, and squadrons) (text)",respoc
"Unit, if other (text)",respoc
"Format of folder materials (text)",format
"Additional formats (text)",format
```

Since non-`name` and `nick` columns are ignored, they can be used for comments (below `cdm-name` is the CONTENTdm field name corresponding to the nick):

```CSV
name,cdm-name,nick
Language(s) - Use Google Translate to identify the language of the leaf text: https://translate.google.com/,Primary language(s),langua
Document genre(s) - Search online for the leaf author and source title to determine the work's genre,Document genre - AAT,docume
Feature(s) - Identify design features present on the leaf (recto and verso),Features - AAT,featur
```

Example usage:

```console
$ cdmutil ftpstruct2catcher ohiouniversitylibraries "Farfel Leaves Metadata" farfel-mapping.csv farfel-edits.json
Requesting project information...
100%|███████████████████████████████████| 59/59 [00:11<00:00,  5.25it/s]
Farfel Leaves Metadata has 59 works with 160 total pages
Found 59 works described
Found 0 pages with transcripts
Requesting structured data configuration...
Requesting structured data...
100%|███████████████████████████████████| 59/59 [00:09<00:00,  6.38it/s]
Writing 59 catcher edits...
```

Optionally, `-l` (or `--level`) can be used to specify the level of description to be requested:
* `work` specifies that only work-level Metadata Fields should be requested
* `page` specifies that only page-level field-based transcriptions should be requested
* `both` specifies that both `work` and `page` level data should be requested
* `auto` (the default) specifies that the FromThePage project configuration should be used to detect what data is available

`ftpstruct2catcher` creates Catcher edits based on the principle of "make the fields in CONTENTdm how they are in FromThePage", meaning:
* Blank fields in FromThePage will be passed on to Catcher and may overwrite existing CONTENTdm metadata with nothing (therefore deleting it)
* It will take whatever (mapped) fields exist in corresponding work or page description or transcription so you must verify the integrity of a project's field schema using `scanftpschema`

`ftpstruct2catcher` will print warnings about fields that exist in a FromThePage project but are not mapped to a CONTENTdm nick at the beginning of a run.

`ftpstruct2catcher` strips leading and trailing whitespace from field values and replaces CRLF line endings with LF.

<a name="ftptransc2catcher"/>

### ftptransc2catcher

`ftptransc2catcher` takes
* A text file listing the URLs for FromThePage's IIIF manifests separated by newlines
* The CONTENTdm field nickname for the collection's full-text transcript field
* An output file name

and outputs a JSON file of FromThePage transcripts matched to CONTENTdm objects for upload via cdm-catcher `edit`. `ftptransc2catcher` should to the same thing that FromThePage's "Export to CONTENTdm" feature does, but only on the specified works and via a cdm-catcher JSON file that can be `catcherdiff`-ed.

The listed FromThePage manifests _must_ have been imported from CONTENTdm, so that the FromThePage manifest lists their CONTENTdm URLs.

`ftptransc2catcher` trims leading and trailing whitespace from transcript edit values.

Optionally, a FromThePage [transcript type](https://github.com/benwbrum/fromthepage/wiki/FromThePage-Support-for-the-IIIF-Presentation-API-and-Web-Annotations#seealso) may be specified via the `--transcript-type` argument. The default is `Verbatim Plaintext`.

Example:
```console
$ head manifests.txt
https://fromthepage.com/iiif/45345/manifest
https://fromthepage.com/iiif/45346/manifest
$ cdmutil ftptransc2catcher manifests.txt transc catcher-edits.json
Requesting transcripts...
100%|███████████████████████████████████| 2/2 [00:38<00:00, 19.20s/it]
Writing JSON file...
$ head catcher-edits.json
[
  {
    "dmrecord": "1959",
    "transc": ""
  },
  {
    "dmrecord": "1960",
    "transc": "#433\nFairfax\nMurray\nFol I Von sant Ambrosio  Dec 7\n(174) CLXXII ..."
  },
  {
```

<a name="json2csv"/>

### json2csv

`json2csv` accepts a cdm-catcher `edit` action JSON file (of the sort output by the 2catcher scripts and `csv2json`) and transposes it into a CSV formatted file, suitable for editing in a spreadsheet. Optionally, the `-d` flag can be used to specify the dialect of CSV (tab-separated is the default).

Example usage:

```console
$ head example.json
[
  {
    "dmrecord": "3001",
    "docume": "Incunabula"
  },
  {
    "dmrecord": "3012",
    "langua": "Latin"
  }
]
$ cdmutil json2csv -d excel example.json example.csv
$ head example.csv
dmrecord,langua,docume
3001,,Incunabula
3012,Latin,
```

<a name="csv2json"/>

### csv2json

`csv2json` accepts a CSV file and transposes its rows into a list of JSON objects with column headers as keys, suitable for use with cdm-catcher's `edit` action (if the column names are CONTENTdm field nicks and one is `dmrecord`):

```console
$ head example.csv
dmrecord,langua,docume
3001,German; Latin,Incunabula
3012,Latin,Comedies (library works); Drama (literary genre); Incunabula
$ cdmutil csv2json -d excel example.csv example-edits.json
$ head example-edits.json
[
  {
    "dmrecord": "3001",
    "langua": "German; Latin",
    "docume": "Incunabula"
  },
  {
    "dmrecord": "3012",
    "langua": "Latin",
    "docume": "Comedies (library works); Drama (literary genre); Incunabula"
```

The `-d` or `--csv-dialect` option should be used to specify the input CSV dialect. Dialects for Google Sheets (`google-csv` and `google-tsv`) have been included to avoid ambiguity, even though they are currently the same as `excel` and `excel-tab`.

By default `csv2json` will drop empty cells from the CSV when creating edits, but will include them as empty strings if the `-k` flag is provided (or "Drop empty CSV cells" is unchecked in the GUI):

```console
$ head example.csv
dmrecord,langua,docume
3001,,Incunabula
3012,Latin,
$ cdmutil csv2json example.csv example.json
$ head example.json
[
  {
    "dmrecord": "3001",
    "docume": "Incunabula"
  },
  {
    "dmrecord": "3012",
    "langua": "Latin"
  }
$ cdmutil csv2json -k example.csv example.json
$ head -n 12 example.json
[
  {
    "dmrecord": "3001",
    "langua": "",
    "docume": "Incunabula"
  },
  {
    "dmrecord": "3012",
    "langua": "Latin",
    "docume": ""
  }
```

## Development

cdm-util-scripts is tested with [pytest](https://pypi.org/project/pytest/) and [vcrpy](https://pypi.org/project/vcrpy/) (via [pytest-recording](https://github.com/kiwicom/pytest-recording)). These development dependencies can be installed using the `dev` extra, like so (using an editable installation of the development branch in a virtual environment on Windows):

    git clone https://github.com/OU-Libraries/cdm-util-scripts
    cd cdm-util-scripts
    git checkout development
    python3 -m venv env
    source env/Scripts/activate
    python3 -m pip install -e .[dev]

vcrpy records web API responses in local cache files called "cassettes" so tests can be reliably run against real, version-controlled data without the lag of using the network every time they are run.
