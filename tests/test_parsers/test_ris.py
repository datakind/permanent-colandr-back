import flask
import pytest

from colandr.lib.parsers import RisFile


class TestRisFile:
    @pytest.mark.parametrize(
        "file_name",
        [
            "example.ris",
            # TODO: none of these work as we want with the current code
            # "example-endnote.ris",
            # "example-mendeley.ris",
            # "example-zotero.ris",
        ],
    )
    def test_parse(self, file_name, app, seed_data, request):
        file_path = request.config.rootpath / "tests" / "fixtures" / file_name
        rf = RisFile(str(file_path))
        citations = list(rf.parse())
        assert citations and len(citations) == len(seed_data["citations"])
        assert flask.jsonify(citations).json == seed_data["citations"]
