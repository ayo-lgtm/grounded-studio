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
        self.assertEqual([block["id"] for block in doc["blocks"]], ["p1", "p2", "p3"])
        self.assertEqual(doc["blocks"][1]["text"], "Built pipelines.")

    def test_split_runs_tabs_and_breaks_join(self):
        para = (
            "<w:r><w:t>Hel</w:t></w:r><w:r><w:t>lo</w:t></w:r>"
            "<w:r><w:tab/></w:r><w:r><w:t>there</w:t></w:r>"
            "<w:r><w:br/></w:r><w:r><w:t>friend</w:t></w:r>"
        )
        doc = parse_docx(_docx([_run("Title"), para]))
        self.assertEqual(doc["blocks"][1]["text"], "Hello there friend")

    def test_empty_paragraphs_skipped(self):
        doc = parse_docx(_docx([_run("Title"), "<w:r></w:r>", _run("  "), _run("Body")]))
        self.assertEqual(len(doc["blocks"]), 2)

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
        self.assertEqual(len(script["beats"]), 3)


if __name__ == "__main__":
    unittest.main()
