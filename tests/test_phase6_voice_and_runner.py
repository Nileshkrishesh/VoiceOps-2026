
"""Test suite for Phase 6 & 7: Voice Agent, Normalization, and Batch Runner Pipeline."""

import sys
import wave
import struct
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.voice_agent import VoiceAgent
from run import run_batch_pipeline, extract_conversation_id


def create_synthetic_wav(
    file_path: Path,
    duration_seconds: float = 0.5,
):
    """Generate a valid, minimal PCM WAV audio file using the standard library."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_seconds)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)

        # Write silence
        data = struct.pack(
            f"<{num_samples}h",
            *([0] * num_samples),
        )
        wf.writeframes(data)


def test_speech_normalization():
    """Verify acoustic text formatting for spoken clarity."""
    va = VoiceAgent()

    # 1. Eight-digit order number spacing
    norm1 = va.normalize_for_speech(
        "Your order 89782837 has been shipped."
    )
    assert "8978 2837" in norm1

    # 2. Date year formatting
    norm2 = va.normalize_for_speech(
        "Delivery is promised on 20 October."
    )
    assert "20 October 2026" in norm2

    # 3. Currency symbol formatting
    norm3 = va.normalize_for_speech(
        "The reverse pickup fee is ₹49."
    )
    assert "Rupees 49" in norm3


def test_conversation_id_extraction():
    """Verify deterministic extraction of multi-turn conversation IDs."""
    assert extract_conversation_id(
        Path("PC002_turn1.wav")
    ) == "PC002"

    assert extract_conversation_id(
        Path("conv12_02.wav")
    ) == "conv12"

    assert extract_conversation_id(
        Path("isolated_sample.wav")
    ) == "isolated_sample"


def test_batch_runner_execution_and_artifacts(tmp_path):
    """Verify that the batch pipeline writes structured output files."""
    input_dir = tmp_path / "audio_inputs"
    output_dir = tmp_path / "audio_outputs"

    # Create two synthetic WAV files representing turns 1 and 2.
    file1 = input_dir / "TEST_CONV_turn1.wav"
    file2 = input_dir / "TEST_CONV_turn2.wav"

    create_synthetic_wav(file1)
    create_synthetic_wav(file2)

    summary = run_batch_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
    )

    assert summary["total_files"] == 2
    assert summary["successful"] == 2
    assert summary["failed"] == 0

    # Verify that individual JSON files and the batch summary exist.
    result1 = output_dir / "TEST_CONV_turn1_result.json"
    result2 = output_dir / "TEST_CONV_turn2_result.json"
    batch_summary = output_dir / "batch_summary.json"

    assert result1.exists()
    assert result2.exists()
    assert batch_summary.exists()

    data1 = json.loads(
        result1.read_text(encoding="utf-8")
    )

    assert data1["conversation_id"] == "TEST_CONV"
    assert data1["turn"] == 1
    assert "reply" in data1
    assert "decision" in data1
    assert "tool_calls" in data1
