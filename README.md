# cdm-util-scripts

cdm-util-scripts are Python scripts developed to support Ohio University Libraries' CONTENTdm operations.

Clone the repo to get a local copy of the scripts `git clone https://github.com/versteeg-ou/cdm-util-scripts`. Do `git pull` to get the latest versions.

You'll need to have the Python `requests` library installed (`pip install requests`).

## csv2json

`csv2json.py` accepts a CSV, TSV or other delimited file and transposes its rows into a list of JSON objects hopefully suitable for use with the Washington State Library's [cdm-catcher](https://github.com/wastatelibrary/cdm-catcher) metadata `edit` action.

## ftp2catcher

`ftp2catcher.py` takes
* A CONTENTdm collection alias
* The CONTENTdm collection's field nickname for the identifier used in FromThePage's IIIF `dc:source` metadata field
* The CONTENTdm field nickname for the collection's transcript field
* A text file listing the URLs for FromThePage's IIIF manifests separated by newlines
* An output file name
and outputs a JSON file of FromThePage transcripts hopefully suitable for upload to CONTENTdm with cdm-catcher.

## printcdminfo

`printcdminfo.py` takes a CONTENTdm repository URL and prints collections and field metadata, including collection and field nicknames.
