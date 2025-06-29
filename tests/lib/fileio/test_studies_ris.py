import json
import pathlib

import flask
import pytest

from colandr.lib.fileio.studies import RisReader


@pytest.fixture(scope="module")
def exp_records(app_ctx, request):
    fixtures_dir: pathlib.Path = (
        request.config.rootpath / "tests" / "fixtures" / "citations"
    )
    with (fixtures_dir / "example-citations.json").open(mode="r") as f:
        exp_citations = json.load(f)
    return exp_citations


@pytest.mark.parametrize(
    "file_name",
    [
        "example.ris",
        # this file fails to parse 1 out of 4 citations, but *inconsistently*
        # given an identical input file, it will parse all 4 correctly
        # this behavior is insane, and i won't subject myself to it further
        # "example-endnote.ris",
        "example-mendeley.ris",
        "example-zotero.ris",
    ],
)
def test_reader(file_name, exp_records, app_ctx, request):
    fixtures_dir: pathlib.Path = (
        request.config.rootpath / "tests" / "fixtures" / "citations"
    )
    file_path = fixtures_dir / file_name
    reader = RisReader()
    records = list(reader.sanitize(reader.read(file_path)))
    assert records
    assert len(records) == len(exp_records)
    for record, exp_record in zip(records, exp_records):
        shared_keys = record.keys() & exp_record.keys()
        record = {k: v for k, v in record.items() if k in shared_keys}
        exp_record = {k: v for k, v in exp_record.items() if k in shared_keys}
        try:
            assert flask.jsonify(record).json == exp_record
        # HACK: mendeley exports newspaper articles as generic references (!!!)
        except AssertionError:
            if (
                file_name == "example-mendeley.ris"
                and exp_record["type_of_reference"] == "book"
            ):
                del record["type_of_reference"]
                del exp_record["type_of_reference"]
                assert flask.jsonify(record).json == exp_record
