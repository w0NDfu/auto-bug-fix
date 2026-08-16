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
