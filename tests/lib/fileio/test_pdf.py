import pathlib

import pytest

from colandr.lib.fileio import pdf


class TestPdfFile:
    @pytest.mark.parametrize(
        ["file_name", "redact_tables", "included_snippets", "excluded_snippets"],
        [
            (
                "example-journal-short.pdf",
                False,
                [
                    # document title
                    "Article title",
                    # abstract content
                    "Sample text inserted for illustration. Replace with abstract text.",
                    # section title
                    "1. Section heading",
                    # section content
                    "Sample text inserted for illustration. Replace with article",
                    # subsection title
                    "1.1 Subsection heading",
                    # reference line
                    "Surname A, Surname B and Surname C 2015 Journal Name",
                ],
                [],
            ),
            (
                "example-journal.pdf",
                False,
                [
                    # document title
                    "Preparation of Papers for IEEE Access",
                    # abstract content
                    "These instructions give you guidelines for preparing papers for IEEE Access.",
                    # section title
                    "I.INTRODUCTION",
                    # image caption
                    "Magnetization as a function of applied field.",
                    # reference line
                    "W.-K. Chen, Linear Networks and Systems. Belmont, CA, USA",
                ],
                [],
            ),
            (
                "example-journal.pdf",
                True,
                [],
                # TODO: find an example pdf with a more obvious table to exclude
                [],
            ),
        ],
    )
    def test_read(
        self,
        file_name,
        redact_tables,
        included_snippets,
        excluded_snippets,
        app_ctx,
        request,
    ):
        fixtures_dir: pathlib.Path = (
            request.config.rootpath / "tests" / "fixtures" / "fulltexts"
        )
        file_path = fixtures_dir / file_name
        fulltext = pdf.read(file_path=file_path, redact_tables=redact_tables)
        assert fulltext and isinstance(fulltext, str)
        for snippet in included_snippets:
            assert snippet in fulltext
        for snippet in excluded_snippets:
            assert snippet not in fulltext
