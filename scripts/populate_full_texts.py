#!/usr/bin/env python
"""
A Python script to bulk upload PDFs to the Colandr API,
mapping PDF files to study records using AidSeq and idMap files.

Usage:
python scripts/populate_full_texts.py -a <aids_file> -i <id_map_file> \
    -f <fulltextids_file> -d <pdf_dir> -t <auth_token> [--host <host>]

Example:
python scripts/populate_full_texts.py -a pdfestrian/json/aidSeq.json -i pdfestrian/json/id_map.tsv \
    -f pdfestrian/json/fulltextids.txt -d /path/to/pdfs -t YOUR_AUTH_TOKEN
"""

import argparse
import csv
import json
import logging
import os
import sys

import httpx


def add_and_parse_args() -> argparse.Namespace:
    """Parse command line args"""
    parser = argparse.ArgumentParser(
        description="Bulk upload PDFs to Colandr API, mapping PDF files to study records."
    )
    parser.add_argument("-a", "--aids", required=True, type=str,
                        help="Path to the AidSeq JSON Lines file (required)")
    parser.add_argument("-i", "--idMap", required=True, type=str,
                        help="Path to the idMap.tsv file (required)")
    parser.add_argument("-f", "--fulltextids", required=True, type=str,
                        help="Path to the fulltextids file (required)")
    parser.add_argument("-d", "--pdfdir", required=True, type=str,
                        help="Directory containing PDF files to upload (required)")
    parser.add_argument("-t", "--token", required=True, type=str,
                        help="Authentication token for API access (required)")
    parser.add_argument("--host", type=str, default="http://localhost:5000",
                        help="Host name of the API (default: http://localhost:5000)")
    return parser.parse_args()


def load_aidseq(filepath: str) -> list[dict]:
    """
    Load AidSeq data from a JSON Lines file.
    Each line is a separate JSON object.

    Args:
        filepath: Path to the JSON Lines file

    Returns:
        List of dictionaries containing AidSeq data
    """
    result = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                result.append(json.loads(line))
        return result
    except Exception as e:
        logging.error("Error loading AidSeq data from %s: %s", filepath, e)
        return []


def parse_id_map(filepath: str) -> dict[str, str]:
    """
    Parse file with aid index to study id map
    """
    id_map = {}
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 2:
                id_map[row[0]] = row[1]
    return id_map


def load_fulltext_ids(filepath: str) -> list[str]:
    """
    Parse file with fulltext ids that need to be processed
    """
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def put_pdf(record_id: int, filename: str, pdf_dir: str, host: str, token: str) -> bool:
    """
    Upload PDF file using Colandr API
    """
    pdf_path = os.path.join(pdf_dir, filename + ".pdf")
    if not os.path.isfile(pdf_path):
        logging.warning("PDF file not found: %s", pdf_path)
        return False
    with open(pdf_path, "rb") as pdf_file:
        response = httpx.post(
            f"{host}/api/fulltexts/{record_id}/upload",
            files={"uploaded_file": (filename + ".pdf", pdf_file, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        if not response.is_success:
            logging.error(
                "Failed to upload PDF for record %s: %s", record_id, response.text
            )
            return False
        try:
            data = response.json()
            return bool(data.get("extracted_items"))
        except Exception:
            return response.is_success


def main():
    """Main script method"""
    args = add_and_parse_args()

    aids = load_aidseq(args.aids)
    id_map = parse_id_map(args.idMap)
    rev_id_map = {v: k for k, v in id_map.items()}
    fulltext_ids = load_fulltext_ids(args.fulltextids)

    aidseq_by_index = {str(aid.get("index")): aid for aid in aids}

    for record_id in fulltext_ids:
        aid_index = rev_id_map.get(record_id)
        if not aid_index:
            logging.warning("No AidSeq index found for record ID %s", record_id)
            continue
        aid = aidseq_by_index.get(aid_index)
        if not aid:
            logging.warning("No AidSeq record found for index %s", aid_index)
            continue
        pdf_info = aid.get("pdf", {})
        filename = pdf_info.get("filename")
        if not filename:
            logging.warning("No PDF filename found for AidSeq index %s", aid_index)
            continue
        put_pdf(int(record_id), filename, args.pdfdir, args.host, args.token)


if __name__ == "__main__":
    sys.exit(main())
