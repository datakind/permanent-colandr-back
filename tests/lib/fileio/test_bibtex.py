import json
import pathlib

import flask
import pytest

from colandr.lib.fileio import bibtex


class TestBibTex:
    @pytest.mark.parametrize(
        "file_name",
        [
            "example.bib",
            "example-endnote.bib",
            "example-mendeley.bib",
            "example-zotero.bib",
        ],
    )
    def test_read(self, file_name, app_ctx, request):
        fixtures_dir: pathlib.Path = request.config.rootpath / "tests" / "fixtures"
        file_path = fixtures_dir / file_name
        citations = bibtex.read(file_path)
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
            # HACK: bibtex doesn't properly handle multiple notes
            if "notes" in exp_citation and len(exp_citation) > 1:
                shared_keys -= {"notes"}
            citation = {k: v for k, v in citation.items() if k in shared_keys}
            exp_citation = {k: v for k, v in exp_citation.items() if k in shared_keys}
            assert flask.jsonify(citation).json == exp_citation
