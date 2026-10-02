import unittest

from worker.transcribe_aws import TranscribeError, parse_transcribe_json, stage_from_store, transcribe_media


class CloudTranscribeDisabledTest(unittest.TestCase):
    def test_parse_path_is_retired(self):
        with self.assertRaises(TranscribeError):
            parse_transcribe_json({"results": {"items": []}})

    def test_cloud_staging_is_blocked(self):
        with self.assertRaises(TranscribeError):
            stage_from_store()

    def test_aws_transcribe_is_blocked(self):
        with self.assertRaises(TranscribeError):
            transcribe_media()


if __name__ == "__main__":
    unittest.main()
