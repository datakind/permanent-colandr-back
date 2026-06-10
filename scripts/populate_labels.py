#!/usr/bin/env python
"""
A Python script to populate labels for documents in the database using AidSeq data.

Usage:
python scripts/populate_labels.py -a <aids_file> -i <id_map_file> -t <auth_token> [--host <host>]

Example:
python scripts/populate_labels.py -a pdfestrian/json/aidSeq.json -i pdfestrian/json/idMap.tsv -t AT
"""

import argparse
import csv
import json
import logging
import sys
from dataclasses import dataclass

import httpx2


@dataclass
class Label:
    """Label definition"""
    label: str
    value: list[str]


biome_map: dict[str, str] = {
    "T_T": "Tundra",
    "T_TSTMBF": "Forest",
    "T_TSTGSS": "Grasslands",
    "T_TSTDBF": "Forest",
    "T_TSTCF": "Forest",
    "T_TGSS": "Grasslands",
    "T_TCF": "Forest",
    "T_TBMF": "Forest",
    "T_MGS": "Grasslands",
    "T_MFWS": "Forest",
    "T_M": "Mangrove",
    "T_FGS": "Grasslands",
    "T_DXS": "Desert",
    "T_BFT": "Forest",
    "M_TU": "Marine",
    "M_TSTSS": "Marine",
    "M_TSS": "Marine",
    "M_TRU": "Marine",
    "M_TRC": "Marine",
    "FW_XFEB": "Freshwater",
    "FW_TSTUR": "Freshwater",
    "FW_TSTFRW": "Freshwater",
    "FW_TSTCR": "Freshwater",
    "FW_TCR": "Freshwater",
    "FW_MF": "Freshwater",
    "FW_LRD": "Freshwater",
    "FW_LL": "Freshwater",
    "FW_TFRW": "Freshwater",
    "FW_TUR": "Freshwater"
}

interv_map: dict[str, str] = {
    "area_mgmt": "area management",
    "area_protect": "area protection",
    "sub": "substitution",
    "training": "training",
    "restoration": "restoration",
    "sus_use": "sustainable use",
    "legis": "legislation",
    "form_ed": "formal education",
    "aware_comm": "awareness and communications",
    "compl_enfor": "compliance and enforcement",
    "inst_civ_dev": "institutional and civil society development",
    "market": "market forces",
    "non_mon": "non-monetary values",
    "other": "other",
    "pol_reg": "policies and regulations",
    "priv_codes": "private sector standards and codes",
    "sp_control": "species control",
    "sp_mgmt": "species management",
    "sp_recov": "species recovery",
    "sp_reint": "species re-introduction",
    "cons_fin": "conservation finance",
    "part_dev": "partnership and alliance development",
    "liv_alt": "enterprises and livelihood alternatives",
    "res_mgmt": "resource protection and management"
}

outcome_map: dict[str, str] = {
    "free_choice": "freedom of choice/action",
    "other": "other",
    "culture": "cultural and spiritual",
    "health": "health",
    "eco_liv_std": "economic living standards",
    "mat_liv_std": "material living standards",
    "sec_saf": "security and safety",
    "sub_well": "subjective well-being",
    "education": "education",
    "soc_rel": "social relations",
    "env": "environment",
    "gov": "governance and empowerment",
    "NA": "other"
}


def add_and_parse_args() -> argparse.Namespace:
    """Parse command line args"""
    parser = argparse.ArgumentParser(
        description="Populate labels for documents in the database using AidSeq data"
    )
    parser.add_argument("-a", "--aids", required=True, type=str,
                        help="Path to the AidSeq JSON Lines file (required)")
    parser.add_argument("-i", "--idMap", required=True, type=str,
                        help="Path to the idMap file that maps AidSeq indices to DB IDs (required)")
    parser.add_argument("-t", "--token", required=True, type=str,
                        help="Authentication token for API access (required)")
    parser.add_argument("--host", type=str, default="http://localhost:5000",
                        help="Host name of the API (default: http://localhost:5000)")
    return parser.parse_args()


def put_labels(id: int, labels: list[Label], host: str, token: str) -> bool:
    """Put labels to the API endpoint for a specific ID using Bearer token authentication"""
    try:
        labels_dict = [{"label": label.label, "value": label.value} for label in labels]

        response = httpx2.put(
            f"{host}/api/data_extractions/{id}",
            json=labels_dict,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        data = response.json()
        return len(data.get("extracted_items", [])) > 0
    except Exception as e:
        logging.error("Error putting labels for ID %s: %s", id, e)
        return False


def to_labels(label: str, labels: list[str]) -> list[Label]:
    """Convert list of label values to Label objects"""
    if labels:
        return [Label(label=label, value=labels)]
    return []


def parse_id_map(filepath: str) -> dict[str, str]:
    """Parse ID map file that maps AidSeq indices to API IDs"""
    id_map = {}
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 2:
                id_map[row[0]] = row[1]
    return id_map


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


def main():
    """Main script method"""
    args = add_and_parse_args()

    aids = load_aidseq(args.aids)
    id_map = parse_id_map(args.idMap)

    lbm = {"grasslands": "grassland"}

    successful = []

    for aid in aids:
        aid_index = str(aid.get("index", 0))
        if aid_index in id_map:
            id_val = id_map[aid_index]

            biomes = []
            for biome_data in aid.get("biome", []):
                if isinstance(biome_data, dict) and "biome" in biome_data:
                    biome = biome_data["biome"]
                    biome = biome_map.get(biome, biome).lower()
                    biome = lbm.get(biome, biome)
                    biomes.append(biome)
            biomes = list(set(biomes))

            intervs = []
            for interv_data in aid.get("interv", []):
                if isinstance(interv_data, dict) and "Int_type" in interv_data:
                    interv = interv_map.get(interv_data["Int_type"], "other")
                    intervs.append(interv)
            intervs = list(set(intervs))

            outcomes = []
            for outcome_data in aid.get("outcome", []):
                if isinstance(outcome_data, dict) and "Outcome" in outcome_data:
                    outcome = outcome_map.get(outcome_data["Outcome"], "other")
                    outcomes.append(outcome)
            outcomes = list(set(outcomes))

            labels = (to_labels("biome", biomes) +
                     to_labels("intervention_type", intervs) +
                     to_labels("outcome_type", outcomes))

            if put_labels(int(id_val), labels, args.host, args.token):
                successful.append(int(id_val))
                print(f"Added for {id_val}")
            else:
                print(f"Failed for {id_val}")

    print(", ".join(map(str, successful)))


if __name__ == "__main__":
    sys.exit(main())
