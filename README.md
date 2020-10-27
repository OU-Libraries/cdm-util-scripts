# cdm-util-scripts

cdm-util-scripts are Python scripts developed to support Ohio University Libraries' CONTENTdm operations.

Clone the repo to get a local copy of the scripts `git clone https://github.com/versteeg-ou/cdm-util-scripts`. Do `git pull` to get the latest versions.

You'll need to have the Python `requests` library installed (`pip install requests`).

## csv2json.py

`csv2json.py` accepts a CSV, TSV or other delimited file and transposes its rows into a list of JSON objects hopefully suitable for use with the Washington State Library's [cdm-catcher](https://github.com/wastatelibrary/cdm-catcher) metadata `edit` action.

## ftp2catcher.py

`ftp2catcher.py` takes
* A CONTENTdm collection alias
* The CONTENTdm collection's field nickname for the identifier used in FromThePage's IIIF `dc:source` metadata field
* The CONTENTdm field nickname for the collection's transcript field
* A text file listing the URLs for FromThePage's IIIF manifests separated by newlines
* An output file name

and outputs a JSON file of FromThePage transcripts hopefully suitable for upload to CONTENTdm with cdm-catcher.

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

`printcdminfo.py` takes a CONTENTdm repository URL and prints collections and field metadata, including collection and field nicknames.

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
