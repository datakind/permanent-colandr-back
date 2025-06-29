import json
import pathlib

import flask
import pytest

from colandr.lib.fileio.studies import BibTexReader


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
        "example.bib",
        "example-endnote.bib",
        "example-mendeley.bib",
        "example-zotero.bib",
    ],
)
def test_reader(file_name, exp_records, app_ctx, request):
    fixtures_dir: pathlib.Path = (
        request.config.rootpath / "tests" / "fixtures" / "citations"
    )
    file_path = fixtures_dir / file_name
    reader = BibTexReader()
    records = list(reader.sanitize(reader.read(file_path)))
    assert records
    assert len(records) == len(exp_records)
    for record, exp_record in zip(records, exp_records):
        shared_keys = record.keys() & exp_record.keys()
        # HACK: bibtex doesn't properly handle multiple notes
        if "notes" in exp_record and len(exp_record) > 1:
            shared_keys -= {"notes"}
        record = {k: v for k, v in record.items() if k in shared_keys}
        exp_record = {k: v for k, v in exp_record.items() if k in shared_keys}
        assert flask.jsonify(record).json == exp_record
