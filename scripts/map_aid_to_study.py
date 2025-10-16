#!/usr/bin/env python
"""
A Python script to map AidSeq indices to study IDs
by matching citation titles in the studies.citation JSONB column.

Usage:
python scripts/map_aid_to_study.py -a <aids_file> -o <id_map_file> \
    --db-host <host> --db-port <port> --db-name <db> --db-user <user> --db-password <password>

Example:
python scripts/map_aid_to_study.py -a pdfestrian/json/aidSeq.json -o pdfestrian/json/id_map.tsv \
    --db-host localhost --db-port 5432 --db-name colandr --db-user colandr --db-password thepassword
"""
import argparse
import csv
import json
import logging
import sys

import psycopg


def add_and_parse_args() -> argparse.Namespace:
    """Parse args"""
    parser = argparse.ArgumentParser(
        description="Map AidSeq indices to study IDs by matching citation titles."
    )
    parser.add_argument("-a", "--aids", required=True, type=str,
                        help="Path to the AidSeq JSON Lines file (required)")
    parser.add_argument("-o", "--out", required=True, type=str,
                        help="Path to the idMap.tsv output file (required)")
    parser.add_argument("--db-host", required=True, type=str,
                        help="Database host")
    parser.add_argument("--db-port", required=False, type=int, default=5432,
                        help="Database port (default: 5432)")
    parser.add_argument("--db-name", required=True, type=str,
                        help="Database name")
    parser.add_argument("--db-user", required=True, type=str,
                        help="Database user")
    parser.add_argument("--db-password", required=True, type=str,
                        help="Database password")
    return parser.parse_args()


def load_aidseq(filepath: str) -> list[dict]:
    """
    Load AidSeq data from a JSON Lines file. Each line is a separate JSON object.
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


def get_study_id_by_title(conn: psycopg.Connection, title: str) -> int | None:
    """
    Query the studies table for a study with a citation title matching the given title.
    Returns the study ID if found, else None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM studies
            WHERE citation->>'title' = %s
            AND dedupe_status='not_duplicate'
            LIMIT 1
            """,
            (title,)
        )
        row = cur.fetchone()
        return row[0] if row else None


def main():
    """Main script method"""
    args = add_and_parse_args()

    aids = load_aidseq(args.aids)

    conn = psycopg.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password
    )

    aid_to_study_id = {}
    found = 0
    try:
        for aid in aids:
            aid_index = aid.get("index")
            all_fields = aid.get("allFields", {})
            title = all_fields.get("Title")
            if not title:
                continue
            study_id = get_study_id_by_title(conn, title)
            if study_id is not None:
                aid_to_study_id[aid_index] = study_id
                found += 1
        print(f"Found {found} out of {len(aids)} citations")

        with open(args.out, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            for aid_index, study_id in aid_to_study_id.items():
                writer.writerow([aid_index, study_id])
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
