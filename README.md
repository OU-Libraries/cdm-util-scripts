# cdm-util-scripts

cdm-util-scripts are Python scripts developed to support Ohio University Libraries' CONTENTdm operations.

## Installation

These instructions require that you are using Python 3 (3.7+) as your `python` and are using a Unix shell with Git installed (like [Git bash on Windows](https://gitforwindows.org/) or the [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/)).

Clone the repo to a convenient local directory:

    git clone https://github.com/OU-Libraries/cdm-util-scripts

Enter your `OU-Libraries` GitHub credentials upon request and `cd` into the repo:

    cd cdm-util-scripts

In the `cdm-util-scripts` directory create a virtual environment and activate it:

    python -m venv env
    source env/Scripts/activate

(Try `source env/bin/activate` on Linux and macOS.) Install `cdm-util-scripts` in the virtual environment:

    python -m pip install .

`pip` might ask you to upgrade itself, which is a good idea. Check to see if the scripts have been installed properly:

    printcdminfo -h

should print its help information. The scripts are now available via their names in any directory through your command line as long as the virtual environment is active. You should be able to tell the environment is active because it will prepend its name to your prompt in parenthesis (`(env)`). You can deactivate the virtual environment to switch script access off:

    deactivate

You can reactivate the virtual environment from the `cdm-util-scripts` directory to regain access to the scripts:

    source env/Scripts/activate

## Update

In the `cdm-util-scripts` directory do `git pull` to update the Git repo to the latest version. Make sure the virtual environment is activated and do `python -m pip install .` to upgrade the package.

You can also delete the cloned repo directory and repeat the installation instructions.

## Usage

All the scripts will give help from the command line if asked via `SCRIPTNAME -h`.

### printcdminfo

`printcdminfo` takes a CONTENTdm repository URL and prints collections and field metadata, including collection and field nicknames. If given a repository base URL it will print a table of collection data for that repository; if passed the `--alias` option with a collection alias, it will print the field information for that collection.

Example:
```
$ printcdminfo https://cdmdemo.contentdm.oclc.org/ --alias oclcsample
name                  nick         type      size   find    req   search   hide   vocdb   vocab   dc        admin   readonly
----                  ----         ----      ----   ----    ---   ------   ----   -----   -----   --        -----   --------
'Title'               'title'      'TEXT'    0      'a0'    1     1        0      ''      0       'title'   0       0
'Subject'             'subjec'     'TEXT'    0      'a5'    0     1        0      'LCTGM' 1       'subjec'  0       0
'Description'         'descri'     'TEXT'    1      'b0'    0     1        0      ''      0       'descri'  0       0
'Creator'             'creato'     'TEXT'    0      'b5'    0     1        0      ''      0       'creato'  0       0
'Publisher'           'publis'     'TEXT'    0      'c0'    0     1        0      ''      0       'publis'  0       0
'Date'                'date'       'DATE'    0      'd0'    0     1        0      ''      0       'date'    0       0
'Type'                'type'       'TEXT'    0      'd5'    0     1        0      ''      0       'type'    0       0
'Format'              'format'     'TEXT'    0      'e0'    0     1        0      ''      0       'format'  0       0
'Contributors'        'contri'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'contri'  0       0
'Identifier'          'identi'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'identi'  0       0
'Source'              'source'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'source'  0       0
'Language'            'langua'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'langua'  0       0
'Relation'            'relati'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'relati'  0       0
'Coverage'            'covera'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'covera'  0       0
'Rights'              'rights'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'rights'  0       0
'Audience'            'audien'     'TEXT'    0      'BLANK' 0     0        0      ''      0       'audien'  0       0
'Transcript'          'transc'     'FTS'     1      'i4'    0     1        0      ''      0       'describ' 0       0
'Archival file'       'fullrs'     'FULLRES' 0      'BLANK' 0     0        1      0       ''      'BLANK'   1       0
'OCLC number'         'dmoclcno'   'TEXT'    0      'BLANK' 0     0        1      0       ''      'BLANK'   1       0
'Date created'        'dmcreated'  'DATE'    0      'f9'    1     1        0      0       ''      'BLANK'   1       1
'Date modified'       'dmmodified' 'DATE'    0      'BLANK' 1     0        1      0       ''      'BLANK'   1       1
'CONTENTdm number'    'dmrecord'   'TEXT'    0      'BLANK' 1     0        1      0       ''      'BLANK'   1       1
'CONTENTdm file name' 'find'       'TEXT'    0      'BLANK' 1     0        1      0       ''      'BLANK'   1       1
```

If you make too many of the same request (10+?), OCLC will start rejecting them, resulting in an error, so it's a good idea to record frequently used queries. You can do this using bash's file redirection operator `>`, as:

    printcdminfo https://media.library.ohio.edu > ou-collections.txt

`printcdminfo` also has an `--output` option that will write CSV and JSON, as:

    printcdminfo https://media.library.ohio.edu --alias donswaim --output csv > donswaim-fields.csv

There is also a `--columns` option that takes a list of column names separated with commas and no spaces and returns only those columns.

Example:
```
$ printcdminfo https://media.library.ohio.edu --alias p15808coll15 --output csv --columns name,nick
name,nick
Title,title
Transcript,descri
Respondent,creato
Respondent- rank (during this event),respod
Respondent- nationality,respoa
Respondent- branch of service,respon
Respondent- formation,respob
...
```

### printftpinfo

`printftpinfo` takes a FromThePage user slug (like `ohiouniversitylibraries`) and prints the collections available from that user on fromthepage.com. It is designed to be helpful for getting exact collection/project names for FromThePage projects.

```
$ printftpinfo ohiouniversitylibraries
@id                                                                                        @type           label
---                                                                                        -----           -----
'https://fromthepage.com/iiif/collection/ohio-university-board-of-trustees-minutes'        'sc:Collection' 'Board of Trustees minutes, Ohio University'
'https://fromthepage.com/iiif/collection/cornelius-ryan-collection-of-world-war-ii-papers' 'sc:Collection' 'Cornelius Ryan Collection of World War II Papers'
'https://fromthepage.com/iiif/collection/william-e-peters-papers'                          'sc:Collection' 'William E. Peters Papers'
'https://fromthepage.com/iiif/collection/farfel-research-notebooks'                        'sc:Collection' 'Farfel Research Notebooks'
'https://fromthepage.com/iiif/collection/los-amigos-records-1947-1952'                     'sc:Collection' 'Los Amigos records, 1947-1952'
'https://fromthepage.com/iiif/collection/ryan-metadata'                                    'sc:Collection' 'Ryan collection metadata'
'https://fromthepage.com/iiif/collection/dance-posters-metadata'                           'sc:Collection' 'Dance Posters Metadata'
```

### scanftpfields

`scanftpfields` takes
* A FromThePage user slug
* A FromThePage project label

and outputs a detailed report on the field schemas in use in that FromThePage project. The report is output in the current directory and has a name of the form `field-label-report_<collection-alias>_<year>-<month>-<day>_<24-hour>-<minutes>-<seconds>.<format>`. This report is designed to be helpful for ensuring schema consistency inside of a collection.

Optionally, the format of the report can be specified using the `--output` argument, which defaults to `html`, but can be changed to `json` to output a machine-readable version of the report's data.

### csv2catcher

`csv2catcher` takes
* A YAML or JSON reconciliation configuration file
* A CSV mapping field data CSV column names to CONTENTdm collection field nicknames
* A field data CSV containing the new metadata values to be uploaded to CONTENTdm
* An output file name

and outputs a JSON file containing the field data from the CSV reconciled against the specified CONTENTdm collection for use with [cdm-catcher](https://github.com/wastatelibrary/cdm-catcher)'s `edit` action.

The reconciliation configuration file specifies these parameters:
* `repository-url` the CONTENTdm instance URL
* `collection-alias` the collection CONTENTdm alias
* `identifier-nick` the CONTENTdm nickname for an object-level metadata field to match CSV rows to CONTENTdm objects
* `match-mode` one of `page`, to match field data CSV rows to page-level metadata, or `object` to match field data CSV rows to object-level metadata
* `page-position-column-name` the name of the column in the field data CSV that enumerates the page the CSV row corresponds to in a compound object if `match-mode` is `page`

Only `match-mode` is required (if provided by itself csv2catcher will simply transpose the field data CSV into JSON). If any of `repository-url`, `collection-alias`, or `identifier-nick` is specified, they must all be specified. If `match-mode` is `page`, `page-position-column-name` must be specified (otherwise it is ignored).

Example of a JSON reconciliation configuration file:
```
{
    "repository-url": "https://media.library.ohio.edu",
    "collection-alias": "p15808coll15",
    "identifier-nick": "identi",
    "match-mode": "object"
}
```

If [PyYAML](https://github.com/yaml/pyyaml) is installed in the current environment, you may use a `.yaml` or `.yml` configuration file instead of JSON. You can install it when the virtual environment is active with `pip install pyyaml`.

Example of a YAML reconciliation configuration file:
```
# You can have comments in YAML
repository-url: https://media.library.ohio.edu
collection-alias: p15808coll15
identifier-nick: identi
match-mode: page
page-position-column-name: Page Position
```

The column mapping CSV must have two columns named `name` and `nick` in that order, and must include a mapping for the `identifier-nick` nickname if specified. Columns mapped to the same field nickname in the column mapping CSV will have their field data CSV contents joined with a semicolon. Multiple rows in the column mapping CSV with the same column name will have their field data CSV contents joined with a semicolon to each of the fields specified in their respective `nick` values. The designated `identifier-nick` field will only be used for reconciliation and will not be included in the output edit records.

Example of a column mapping CSV:
```
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

All cell values in the field data CSV will have leading and trailing whitespace removed. Columns with identical names in the field data CSV will have their contents joined with a semicolon before being mapped according to the column mapping CSV.

The `page` reconciliation mode matches field data CSV rows to page level-metadata in CONTENTdm compound objects using the object-level `identifier-nick` key and the specified page number in the `page-position-column-name` column. The `object` reconciliation mode matches field data CSV rows to object level metadata using the `identifier-nick` key, which must be unique in the field data CSV.

Example, using the `object` mode:
```
$ cat object-config.json
{
    "repository-url": "https://media.library.ohio.edu",
    "collection-alias": "p15808coll15",
    "identifier-nick": "identi",
    "match-mode": "object"
}
$ csv2catcher object-config.json col-map.csv fromthepage-tables-export.csv csv2catcher-objects.json
Requesting object pointers: 397/397 100%
$ head csv2catcher-objects.json
[
  {
    "dmrecord": "5193",
    "creato": "",
    "respoa": "United States of America",
    "respon": "Army",
    "respod": "",
    "respob": "4th Infantry Division",
    "respoc": "8th Infantry Regiment",
```

Example, using the `page` mode: 
```
$ cat page-config.yaml
repository-url: https://media.library.ohio.edu
collection-alias: p15808coll15
identifier-nick: identi
match-mode: page
page-position-column-name: Page Position
$ csv2catcher page-config.yaml col-map.csv fromthepage-tables-export.csv csv2catcher-pages.json
Requesting object pointers: 397/397 100%
Requesting page pointers: 4/4 100%
$ head csv2catcher-pages.json
[
  {
    "dmrecord": "5173",
    "creato": "",
    "respoa": "United States of America",
    "respon": "Army",
    "respod": "",
    "respob": "4th Infantry Division",
    "respoc": "8th Infantry Regiment",
```
Note that the `dmrecord` pointer now points to a page in the object referenced in the previous example.

### ftpfields2catcher

`ftpfields2catcher` takes
* A match mode, either `object` or `page`
* A FromThePage user slug
* A FromThePage project label
* A CSV mapping field data CSV column names to CONTENTdm collection field nicknames
* An output file name

and outputs a JSON file containing field data from FromThePage project for use with [cdm-catcher](https://github.com/wastatelibrary/cdm-catcher)'s `edit` action.

The FromThePage project _must_:
1. Be field-based
2. Have the same field schema for each transcript
3. Have been loaded from CONTENTdm (so that FromThePage stored the corresponding CONTENTdm object URLs)

The match modes differ only in their treatment of compound objects. Both match field-based transcriptions for simple, single-item objects. There can be only one match mode per-collection.

Match mode `page` matches each field-based transcription to the page-level metadata for the corresponding page inside the page's compound object. If a page's field-based transcription is blank, it skips it.

Match mode `object` matches a single field-based transcription page to the object-level metadata for a compound object. It chooses the first filled page,  meaning the first page in an object that has a non-empty value in any field. It ignores any filled pages after the first. If there are no filled pages in a FromThePage work, it skips it.

### ftp2catcher

`ftp2catcher` takes
* A CONTENTdm repository URL
* A CONTENTdm collection alias
* The CONTENTdm collection's field nickname for the identifier used in FromThePage's IIIF `dc:source` metadata field
* The CONTENTdm field nickname for the collection's transcript field
* A text file listing the URLs for FromThePage's IIIF manifests separated by newlines
* An output file name

and outputs a JSON file of FromThePage transcripts hopefully suitable for upload to CONTENTdm with cdm-catcher.

FromThePage provides its own set of IIIF manifests for transcribed CONTENTdm objects. These manifests contain links to transcripts corresponding to the pages of the object in several flavors:

* `Verbatim Plaintext` provides "the verbatim text, with all formatting, emendation, and subject linking stripped out" designed for "human download."
* `Emended Plaintext` differs from `Verbatim Plaintext` by applying "normalization ... to all subjects mentioned so that while the verbatim text may read `"I greeted Mr. Jones and his wife this morning."`, the emended plaintext will read `"I greeted James Jones and Elizabeth Smith Jones this morning"`.
* `Verbatim Translation Plaintext` provides a `Verbatim Plaintext` version of the text of a translation
* `Emended Translation Plaintext` provides an `Emended Plaintext` version of the text of a translation
* `Searchable Plaintext` provides a plaintext transcript with "words broken by hyphenated newlines are joined together, and a list of the canonical names mentioned within each page is appended to the end of the page"
* `XHTML` provides the "existing XHTML export... with all formatting, emendation, and subject linking stripped out" 
* `TEI-XML` provides the "existing TEI-XML export of the work"
* `Subject CSV` provides a CSV of the "subjects mentioned within the work"

Please consult FromThePage's API [documentation on renderings](https://github.com/benwbrum/fromthepage/wiki/FromThePage-Support-for-the-IIIF-Presentation-API-and-Web-Annotations#sequence-level-rendering) for up-to-date explanations and examples.

`ftp2catcher` currently defaults to `Verbatim Plaintext`, but there is an optional `--transcript_type` argument where you can specify the transcript flavor.

FromThePage IIIF manifests do not contain explicit links back to CONTENTdm objects, but they do publish a `dc:source` metadata field that contains an object identifier (perhaps based on designated `dc:identifier` in collection field data?):

```
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@id": "https://fromthepage.com/iiif/45434/manifest",
  "@type": "sc:Manifest",
  "label": "Box 013, folder 01: 4th Infantry Division, after action reports",
  "metadata": [
    {
      "label": "dc:source",
      "value": "ryan_box013-tld_f01"
    }
  ],
  ...
```

`ftp2catcher` uses this `"metadata"` `"value"` to search CONTENTdm for the corresponding object so it can provide `dmrecord` numbers for cdm-catcher. To search for this identifier, `ftp2catcher` needs to know the field nickname to search in. This may be `identi` (because of the way CONTENTdm names `dc:identifer` fields), but should be ascertained from the CONTENTdm collection admin page, inspecting item page source, or `printcdminfo`.

`ftp2catcher` associates transcripts with object pages by assuming that they're in the same order in FromThePage and CONTENTdm, "zipping" them together. It may be a good idea to check that this assumption is reliable.

`ftp2catcher` must also be provided with the field nickname for the transcript field in the target collection. This field will be type `FTS` in `printcdminfo` output.

Example:
```
$ cat ftp-manifest-urls.txt
https://fromthepage.com/iiif/45434/manifest
https://fromthepage.com/iiif/36866/manifest
$ ftp2catcher http://media.library.ohio.edu p15808coll15 identi descri ftp-manifest-urls.txt cdm-catcher-edits.json
Requesting 'https://fromthepage.com/iiif/45434/manifest'...
Searching 'p15808coll15' field 'identi' for 'ryan_box013-tld_f01'...
Requesting 20 'Verbatim Plaintext' page transcripts: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
Requesting 'https://fromthepage.com/iiif/36866/manifest'...
Searching 'p15808coll15' field 'identi' for 'ryan_box013-tld_f31'...
Requesting 11 'Verbatim Plaintext' page transcripts: 1 2 3 4 5 6 7 8 9 10 11
Writing JSON file...
Done
$ head cdm-catcher-edits.json
[
  {
    "dmrecord": "5173",
    "descri": "After Action Reports\n4th Infantry\nDivision, 8th\nRegt--statem.\nBox 13, #1\n\n\n"
  },
  {
    "dmrecord": "5174",
    "descri": "This extract is from the after action report of the 8th Infantry\nRegiment of teh 4th Infantry Division.\nOn the 30th of May the troops turned in their English money which was added to a\npartial payment of $4.03 and returned in French invasion currency. Excitement\nsurrounding the forthcoming mission had by this time increased to high pitch. It\nwas planned that the 8th Infantry and 3rd Battalion of the 22nd Infantry and its\ncombat team attachment as the foremost assault elemest of the 4th Division would\nbreach the enemy beach defenses on the Contentin peninsular of France and drive\ninland, then north to take the port of Cherbourg from the rear to facilitate the\nreopening of the Port and the landing of sufficient troops and material to participate\na crushing drive against the Germans through central France.\nBy the first of June the command post group had completed the plans for the regiment's\nparticipation in the operations. General Barton visiting headquarters in the early\nevening made a final check on the work completed by the staff officers which was\nendorsed with his enthusiastic approval. The 4th Divison and 8th Infantry was now\nready to load aboard the invasion transport and to wait the combination of the\nexact element to [crossed out] [illegible] [end crossed out] [inserted] tide, weather [end inserted] and the enemy situation which would signify D-Day\nand H hour. On Thursday, the 2nd of June, the 8th Infantry commenced loading aboard\n\n"
  },
  {
```

`ftp2catcher` can also have its arguments specified via a text file, prefixed with `@`:
```
$ cat arguments.txt
http://media.library.ohio.edu
p15808coll15
identi
descri
ftp-manifest-urls.txt
cdm-catcher-edits.json
$ ftp2catcher @arguments.txt
```
The optional argument can also be provided with file-specified arguments:

    ftp2catcher @arguments.txt --transcript_type 'Searchable Plaintext'

### csv2json

`csv2json` accepts a CSV, TSV or other delimited file and transposes its rows into a list of JSON objects with column headers as keys, hopefully suitable for use with the Washington State Library's [cdm-catcher](https://github.com/wastatelibrary/cdm-catcher) metadata `edit` action.
