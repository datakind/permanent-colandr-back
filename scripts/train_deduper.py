import argparse
import json
import logging
import pathlib
import sys
from typing import Any

from colandr.lib.models import Deduper


def main():
    args = add_and_parse_args()
    logging.basicConfig(level=args.loglevel)

    deduper = Deduper(num_cores=args.num_cores, in_memory=args.in_memory)
    data = prep_training_data(args.data_fpath, args.data_id_key, deduper)
    deduper.fit(data)
    if args.save_dir:
        deduper.save(args.save_dir)


def add_and_parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a model to deduplicate citation records."
    )
    parser.add_argument("--data-fpath", type=pathlib.Path, required=True)
    parser.add_argument("--data-id-key", type=str, default="id")
    parser.add_argument("--training-fpath", type=pathlib.Path, default=None)
    parser.add_argument("--num-cores", type=int, default=1)
    parser.add_argument("--save-dir", type=pathlib.Path, default=None)
    parser.add_argument("--in-memory", action="store_true", default=False)
    parser.add_argument("--loglevel", type=int, default=logging.INFO)
    return parser.parse_args()


def prep_training_data(
    data_fpath: pathlib.Path, data_id_key: str, deduper: Deduper
) -> dict[Any, dict[str, Any]]:
    with data_fpath.open(mode="r") as f:
        data = json.load(f)
    return deduper.preprocess_data(data, data_id_key)


if __name__ == "__main__":
    sys.exit(main())
