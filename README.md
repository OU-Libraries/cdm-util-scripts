# cdm-util-scripts

cdm-util-scripts are Python scripts developed to support Ohio University Libraries' CONTENTdm operations.

Clone the repo to get a local copy of the scripts: `git clone https://github.com/versteeg-ou/cdm-util-scripts`. Do `git fetch` in the repo directory to see if there are updates available; do `git pull` to get the latest versions.

You'll need to have Python and the Python `requests` library installed (`pip install requests`).

## csv2json.py

`csv2json.py` accepts a CSV, TSV or other delimited file and transposes its rows into a list of JSON objects with column headers as keys, hopefully suitable for use with the Washington State Library's [cdm-catcher](https://github.com/wastatelibrary/cdm-catcher) metadata `edit` action.

## ftp2catcher.py

`ftp2catcher.py` takes
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

Please consult FromThePage's API [documentation on renderings](https://github.com/benwbrum/fromthepage/wiki/FromThePage-Support-for-the-IIIF-Presentation-API-and-Web-Annotations#sequence-level-rendering) for up-to-date explications and examples.

`ftp2catcher.py` currently provides `Verbatim Plaintext`.

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

`ftp2catcher.py` uses this `"metadata"` `"value"` to search CONTENTdm for the corresponding object so it can provide `dmrecord` numbers for cdm-catcher. To search for this identifier, `ftp2catcher.py` needs to know the field nickname to search in. This may be `identi` (because of the way CONTENTdm names `dc:identifer` fields), but should be ascertained from the CONTENTdm collection admin page, inspecting item page source, or `printcdminfo.py`.

`ftp2catcher.py` associates transcripts with object pages by assuming that they're in the same order in FromThePage and CONTENTdm, "zipping" them together. It may be a good idea to check that this assumption is reliable.

`ftp2catcher.py` must also be provided with the field nickname for the transcript field in the target collection. This field will be type `FTS` in `printcdminfo.py` output.

Example:
```
$ cat test.txt
https://fromthepage.com/iiif/45434/manifest
$ python ftp2catcher.py p15808coll15 identi descri test.txt test.json
Requesting 'https://fromthepage.com/iiif/45434/manifest'...
Searching 'p15808coll15' field 'identi' for 'ryan_box013-tld_f01'...
Requesting 20 'Verbatim Plaintext' page transcripts: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
Writing JSON file...
Done
$ head test.json
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

## printcdminfo.py

`printcdminfo.py` takes a CONTENTdm repository URL and prints collections and field metadata, including collection and field nicknames. If given a repository base URL it will print a table of collection data for that repository; if passed the `--alias` option with a collection alias, it will print the field information for that collection.

Example:
```
$ python printcdminfo.py https://cdmdemo.contentdm.oclc.org/ --alias oclcsample
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

If you make too many of the same request (10+?), OCLC will start rejecting them, resulting in an error, so it's a good idea to record frequently used queries. You can do this using bash, as:

    python printcdminfo.py https://media.library.ohio.edu >ou-collections.txt

`printcdminfo.py` also has an `--output` option that will write CSV and JSON, as:

    python printcdminfo.py https://media.library.ohio.edu --alias donswaim --output csv >donswaim-fields.csv
