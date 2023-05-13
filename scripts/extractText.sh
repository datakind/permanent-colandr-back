#!/bin/bash

export APP_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )" 
# This script is used to extract text from a PDF file.
# It outputs the text to stdout.
# It calls extract_pdf_text.py, directly passing the arguments to it.

# The script is called as follows:
# extractText.sh -f <input_file> --html
python3 $APP_HOME/scripts/extract_pdf_text.py "$@"
