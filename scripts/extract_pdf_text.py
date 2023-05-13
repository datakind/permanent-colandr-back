import fitz
import sys
import argparse

def extract_pdf_text(pdf_path: str, output_type: str = "text" ):
    """ Extracts text from a PDF file and writes it to a text file. """
    with fitz.open(pdf_path) as doc:
        for page in doc: # iterate the document pages
	        text = page.get_text(output_type).encode("utf8") # get plain text (is in UTF-8)
	        sys.stdout.buffer.write(text) # write text of page
	        sys.stdout.buffer.write(bytes((12,))) # write page delimiter (form feed 0x0C)


def main(): 
    parser = argparse.ArgumentParser(description='Extract text from PDF file.', add_help=False)
    parser.add_argument('-f', '--filename', type=str, required=True, help='Filename of pdf.')
    parser.add_argument('-h', '--html', action='store_true', help='flag, if on will extract html string instead of plain text.')
    args = parser.parse_args()
    extract_pdf_text(args.filename, "html" if args.html else "text")

if __name__ == '__main__':
    sys.exit(main())
