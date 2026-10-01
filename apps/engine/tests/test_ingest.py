import io
import unittest
import zipfile

from grounded.compile_deck import compile_document
from grounded.ingest import IngestError, parse_docx
from grounded.qa import validate_script


def _docx(paragraphs):
    body = "".join(f"<w:p>{runs}</w:p>" for runs in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buf.getvalue()


def _run(*texts):
    return "".join(f"<w:r><w:t>{text}</w:t></w:r>" for text in texts)


class IngestTest(unittest.TestCase):
    def test_paragraphs_become_ordered_blocks(self):
        data = _docx([_run("Jane Doe"), _run("Built pipelines."), _run("Led oncall.")])
        doc = parse_docx(data)
        self.assertEqual(doc["title"], "Jane Doe")
        self.assertEqual(doc["title_block"], "p1")
        self.assertEqual([block["id"] for block in doc["blocks"]], ["p2", "p3"])
        self.assertEqual(doc["blocks"][0]["text"], "Built pipelines.")
        self.assertEqual(doc["blocks"][0]["role"], "evidence")

    def test_split_runs_tabs_and_breaks_join(self):
        para = (
            "<w:r><w:t>Hel</w:t></w:r><w:r><w:t>lo</w:t></w:r>"
            "<w:r><w:tab/></w:r><w:r><w:t>there</w:t></w:r>"
            "<w:r><w:br/></w:r><w:r><w:t>friend</w:t></w:r>"
        )
        doc = parse_docx(_docx([_run("Title"), para]))
        self.assertEqual(doc["blocks"][0]["text"], "Hello there friend")

    def test_empty_paragraphs_skipped(self):
        doc = parse_docx(_docx([_run("Title"), "<w:r></w:r>", _run("  "), _run("Body")]))
        self.assertEqual(doc["title"], "Title")
        self.assertEqual([block["text"] for block in doc["blocks"]], ["Body"])

    def test_bad_bytes_rejected(self):
        with self.assertRaises(IngestError):
            parse_docx(b"not a zip")

    def test_missing_document_xml_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("other.txt", "hi")
        with self.assertRaises(IngestError):
            parse_docx(buf.getvalue())

    def test_parsed_doc_compiles_and_validates(self):
        doc = parse_docx(_docx([_run("Jane Doe"), _run("Shipped $4.82M in pipeline. RAN 41.2% growth.")]))
        script = compile_document(doc, "leadership-brief")
        self.assertEqual(validate_script(script), [])
        self.assertEqual([beat["text"] for beat in script["beats"]], [
            "Jane Doe",
            "Shipped $4.82M in pipeline. RAN 41.2% growth.",
        ])

    def test_table_row_is_one_block_and_approve_is_an_ask(self):
        body = (
            "<w:p><w:r><w:t>Pricing change</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Pipeline closed at $4.82M.</w:t></w:r></w:p>"
            "<w:tbl><w:tr>"
            "<w:tc><w:p><w:r><w:t>Region</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>EMEA slipped $120,000.</w:t></w:r></w:p></w:tc>"
            "</w:tr></w:tbl>"
            "<w:p><w:r><w:t>Approve the collections standup.</w:t></w:r></w:p>"
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}</w:body></w:document>"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("word/document.xml", xml)
        doc = parse_docx(buf.getvalue())
        self.assertEqual(doc["title"], "Pricing change")
        self.assertEqual(
            [(block["role"], block["text"]) for block in doc["blocks"]],
            [
                ("evidence", "Pipeline closed at $4.82M."),
                ("evidence", "Region EMEA slipped $120,000."),
                ("ask", "Approve the collections standup."),
            ],
        )
        script = compile_document(doc, "leadership-brief")
        self.assertEqual(validate_script(script), [])
        self.assertEqual(
            [beat["layout"] for beat in script["beats"]],
            ["cover", "statement", "statement", "ask"],
        )
        self.assertEqual(script["beats"][0]["text"], "Pricing change")
        self.assertNotIn("Pricing change", [beat["text"] for beat in script["beats"][1:]])


if __name__ == "__main__":
    unittest.main()
