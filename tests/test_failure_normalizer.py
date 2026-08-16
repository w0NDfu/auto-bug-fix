import json

import pytest

from autobugfix.evidence import (
    EvidenceLimits,
    EvidenceValidationError,
    RepairRequest,
)
from autobugfix.failure_normalizer import normalize_failure

TRACEBACK = """Traceback (most recent call last):
  File "C:\\work\\tests\\test_math.py", line 8, in test_divide
    divide(1, 0)
  File "C:\\work\\math.py", line 3, in divide
    return numerator / denominator
ZeroDivisionError: division by zero
"""


def test_traceback_produces_ordered_factual_frames_and_separate_issue_text():
    request = normalize_failure(TRACEBACK, issue_text="Please investigate this regression.")

    assert request.evidence.source == "traceback"
    assert [frame.location.file for frame in request.evidence.frames] == [
        r"C:\work\tests\test_math.py",
        r"C:\work\math.py",
    ]
    assert request.evidence.frames[0].location.line == 8
    assert request.evidence.frames[1].function == "divide"
    assert request.evidence.message == "ZeroDivisionError: division by zero"
    assert request.issue_text == "Please investigate this regression."


def test_chained_tracebacks_keep_all_frames_and_last_observed_error():
    log = (
        'Traceback (most recent call last):\n  File "a.py", line 1, in first\nValueError: first\n'
        "\nThe above exception was the direct cause of the following exception:\n\n"
        'Traceback (most recent call last):\n  File "b.py", line 2, in second\nRuntimeError: second\n'
    )
    request = normalize_failure(log)

    assert [frame.location.file for frame in request.evidence.frames] == ["a.py", "b.py"]
    assert request.evidence.message == "RuntimeError: second"
    assert all(frame.excerpt is None for frame in request.evidence.frames)


def test_traceback_frame_without_source_excerpt_does_not_capture_exception_line():
    request = normalize_failure(
        'Traceback (most recent call last):\n  File "a.py", line 1, in f\nValueError: bad\n'
    )

    assert request.evidence.frames[0].excerpt is None
    assert request.evidence.message == "ValueError: bad"


def test_traceback_keeps_real_indented_source_excerpt():
    request = normalize_failure(
        'Traceback (most recent call last):\n  File "a.py", line 1, in f\n    explode()\nValueError: bad\n'
    )

    assert request.evidence.frames[0].excerpt == "explode()"


def test_custom_exception_name_is_preserved_in_traceback_context():
    request = normalize_failure(
        'Traceback (most recent call last):\n  File "a.py", line 1, in run\n'
        '    raise MyProjectFailure("broken")\nMyProjectFailure: broken\n'
    )

    assert request.evidence.message == "MyProjectFailure: broken"


def test_malformed_frame_is_not_a_stack_frame_and_does_not_crash():
    request = normalize_failure(
        'Traceback (most recent call last):\nFile "broken.py", line not-a-number, in bad\n'
        'MyProjectFailure: broken\n'
    )

    assert request.evidence.frames == ()
    assert request.evidence.message == "MyProjectFailure: broken"


def test_traceback_header_can_preserve_summary_without_valid_frames():
    request = normalize_failure(
        'Traceback (most recent call last):\nMyProjectFailure: broken\n'
    )

    assert request.evidence.frames == ()
    assert request.evidence.raw_log.startswith("Traceback")
    assert request.evidence.message == "MyProjectFailure: broken"


def test_mixed_pytest_traceback_keeps_ordered_frames_and_observed_messages():
    request = normalize_failure(
        'FAILED tests/test_x.py::test_x - expected 1\n'
        'Traceback (most recent call last):\n  File "x.py", line 2, in test_x\n'
        'AssertionError: expected 1\n'
    )

    assert request.evidence.source == "traceback"
    assert request.evidence.parser == "python-traceback"
    assert [frame.location.file for frame in request.evidence.frames] == ["x.py"]
    assert request.evidence.message == "AssertionError: expected 1"


def test_pytest_and_raw_logs_are_bounded_evidence():
    pytest_request = normalize_failure("E   AssertionError: expected 1\nFAILED tests/test_x.py::test_x - expected 1\n")
    raw_request = normalize_failure("worker reported a failure", source="ci-log")

    assert pytest_request.evidence.source == "pytest"
    assert pytest_request.evidence.parser == "pytest"
    assert pytest_request.evidence.raw_log.startswith("E   AssertionError")
    assert raw_request.evidence.source == "ci-log"
    assert raw_request.evidence.parser == "raw"


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("", "empty_input"),
        ("unsafe\x1b[31m", "control_character"),
        (b"\xff", "invalid_utf8"),
    ],
)
def test_hostile_input_returns_structured_validation_errors(value, code):
    with pytest.raises(EvidenceValidationError) as exc_info:
        normalize_failure(value)

    assert exc_info.value.code == code
    assert exc_info.value.to_dict()["error"]["code"] == code


def test_oversized_input_is_rejected_without_silent_truncation():
    with pytest.raises(EvidenceValidationError) as exc_info:
        normalize_failure("x" * 11, limits=EvidenceLimits(max_input_bytes=10))

    assert exc_info.value.code == "input_too_large"


def test_serialization_is_deterministic_and_round_trips():
    request = normalize_failure(TRACEBACK, issue_text="issue text")
    serialized = request.to_json()
    restored = RepairRequest.from_json(serialized)

    assert restored == request
    assert serialized == request.to_json()
    assert json.loads(serialized)["issue_text"] == "issue text"


def test_serialization_rejects_non_finite_confidence_and_invalid_source_lines():
    request = normalize_failure("ValueError: bad")
    payload = request.to_dict()
    payload["evidence"]["parser_confidence"] = float("nan")
    with pytest.raises(ValueError, match="parser_confidence"):
        RepairRequest.from_json(json.dumps(payload))

    payload = request.to_dict()
    payload["evidence"]["frames"] = [
        {"location": {"file": "a.py", "line": 0, "column": None}}
    ]
    with pytest.raises(ValueError, match="line"):
        RepairRequest.from_dict(payload)


def test_cli_inspection_is_offline_and_json_safe(capsys):
    from autobugfix.cli import main

    assert main(["inspect-failure", "--log", "ValueError: bad", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["evidence"]["message"] == "ValueError: bad"

    assert main(["inspect-failure", "--log", "bad\x1b"]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "control_character"


def test_normalization_does_not_open_network_connections(monkeypatch):
    def fail_network(*_args, **_kwargs):
        pytest.fail("failure normalization must not open network connections")

    monkeypatch.setattr("socket.create_connection", fail_network)

    request = normalize_failure("ValueError: offline")

    assert request.evidence.message == "ValueError: offline"
