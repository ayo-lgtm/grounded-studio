from worker.qa import validate_script
from worker.compile_walkthrough import stub_from_transcript


def test_valid_recording_script():
    script = stub_from_transcript(
        [{"t_start_ms": 0, "t_end_ms": 1200, "text": "Click Settings."}]
    )
    assert validate_script(script) == []


def test_rejects_missing_citation():
    script = {
        "beats": [{"ord": 1, "kind": "step", "text": "Invented button", "citations": []}]
    }
    errors = validate_script(script)
    assert errors
