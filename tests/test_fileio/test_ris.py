import json
import pathlib

import flask
import pytest

from colandr.lib.fileio import ris


class TestRisFile:
    @pytest.mark.parametrize(
        "file_name",
        [
            "example.ris",
            "example-endnote.ris",
            "example-mendeley.ris",
            "example-zotero.ris",
        ],
    )
    def test_read(self, file_name, app, request):
        fixtures_dir: pathlib.Path = request.config.rootpath / "tests" / "fixtures"
        file_path = fixtures_dir / file_name
        citations = ris.read(file_path)
        with (fixtures_dir / "example-citations.json").open(mode="r") as f:
            exp_citations = json.load(f)
        assert (
            citations
            and isinstance(citations, list)
            and len(citations) == len(exp_citations)
        )
        # filter out keys in case source doesn't provide all fields in raw ris data
        for citation, exp_citation in zip(citations, exp_citations):
            shared_keys = citation.keys() & exp_citation.keys()
            citation = {k: v for k, v in citation.items() if k in shared_keys}
            exp_citation = {k: v for k, v in exp_citation.items() if k in shared_keys}
            try:
                assert flask.jsonify(citation).json == exp_citation
            # HACK: mendeley exports newspaper articles as generic references (!!!)
            except AssertionError:
                if (
                    file_name == "example-mendeley.ris"
                    and exp_citation["type_of_reference"] == "book"
                ):
                    del citation["type_of_reference"]
                    del exp_citation["type_of_reference"]
                    assert flask.jsonify(citation).json == exp_citation
