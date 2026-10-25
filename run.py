"""VoiceOps 2026 ZentroMart Customer Support Agent - Unified Batch Runner.

Converts supported recordings to 16 kHz mono WAV with FFmpeg, then processes
the WAV files through Gnani STT -> Conversation/RAG/Tools -> Gnani TTS.

Usage:
    python run.py --input-dir ./sample_audio --output-dir ./outputs
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Reduce noisy background logs before importing ML/audio libraries.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    OUTPUTS_DIR,
    GNANI_STT_LANG,
    GNANI_TTS_VOICE,
    GNANI_TTS_MODEL,
)
from src.knowledge_base import KnowledgeBase  # noqa: E402
from src.conversation import ConversationSession  # noqa: E402
from src.voice_agent import VoiceAgent  # noqa: E402


# WAV files are processed directly. Every other supported input is converted
# to WAV first. FFmpeg can decode many additional formats, listed here.
CONVERTIBLE_EXTENSIONS = {
    ".m4a", ".mp3", ".mp4", ".ogg", ".flac", ".aac", ".wma",
    ".webm", ".mov", ".mkv", ".mpeg", ".mpg", ".aiff", ".aif",
    ".opus", ".amr", ".3gp", ".m4v",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="VoiceOps 2026 ZentroMart Audio Batch Processor"
    )
    parser.add_argument(
        "--input-dir", "-i",
        type=str,
        required=True,
        help="Folder containing customer audio/video recordings",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=str(OUTPUTS_DIR),
        help="Folder for spoken replies and JSON results",
    )
    parser.add_argument(
        "--stt-lang",
        type=str,
        default=GNANI_STT_LANG,
        help="Gnani STT language code (e.g. en-IN, hi-IN, gu-IN)",
    )
    parser.add_argument(
        "--tts-voice",
        type=str,
        default=GNANI_TTS_VOICE,
        help="Gnani TTS voice name (e.g. Kaveri, Pranav, Trupti, Shlok)",
    )
    parser.add_argument(
        "--tts-model",
        type=str,
        default=GNANI_TTS_MODEL,
        help="Gnani TTS model version (default: timbre-v2.5)",
    )
    return parser.parse_args()


def extract_conversation_id(file_path: Path) -> str:
    """Extract a shared conversation ID from common turn filename patterns.

    Examples:
      PC002_turn1.wav       -> PC002
      PC002_turn_2.wav      -> PC002
      conv01_01.wav         -> conv01
      call_1029_turn_2.wav  -> call_1029
      customer_voice.wav    -> customer_voice
    """
    stem = file_path.stem
    if "_turn" in stem.lower():
        return re.split(r"_turn", stem, flags=re.IGNORECASE)[0]

    parts = stem.split("_")
    if len(parts) >= 2 and parts[-1].isdigit():
        return "_".join(parts[:-1])

    return stem


def convert_recordings_to_wav(input_dir: Path) -> Tuple[List[Path], List[Dict[str, str]]]:
    """Convert supported non-WAV recordings in the input folder to WAV.

    Requires FFmpeg to be installed and available on PATH. Original files are
    kept. Converted WAV files are saved beside the originals. Files in nested
    subfolders are not scanned.
    """
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    ffmpeg_path = shutil.which("ffmpeg")
    source_files = sorted(
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in CONVERTIBLE_EXTENSIONS
    )
    conversion_errors: List[Dict[str, str]] = []

    if source_files and not ffmpeg_path:
        raise RuntimeError(
            "FFmpeg was not found. Install FFmpeg and ensure 'ffmpeg' works "
            "in a new terminal, then run this command again."
        )

    for source in source_files:
        target = source.with_suffix(".wav")
        print(f"Converting: {source.name} -> {target.name}")

        command = [
            ffmpeg_path,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(source),
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(target),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            if not target.exists() or target.stat().st_size == 0:
                raise RuntimeError("FFmpeg did not create a non-empty WAV file.")
            print(f"  Converted successfully: {target.name}")
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            detail = ""
            if isinstance(exc, subprocess.CalledProcessError):
                detail = (exc.stderr or "").strip()
            else:
                detail = str(exc)

            # Do not accidentally process an older WAV if the latest conversion
            # failed for a same-stem source.
            if target.exists():
                try:
                    target.unlink()
                except OSError:
                    pass

            message = detail or str(exc)
            conversion_errors.append({
                "input_file": source.name,
                "status": "conversion_error",
                "error": message,
            })
            print(f"  CONVERSION FAILED: {source.name}: {message}")

    # Only process WAVs, so a source file and its converted copy are not both
    # sent through STT as duplicate turns.
    wav_files = sorted(
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".wav"
    )
    return wav_files, conversion_errors


def run_batch_pipeline(
    input_dir: Path,
    output_dir: Path,
    stt_lang: str = GNANI_STT_LANG,
    tts_voice: str = GNANI_TTS_VOICE,
    tts_model: str = GNANI_TTS_MODEL,
) -> Dict[str, Any]:
    """Convert recordings if needed, then run the VoiceOps batch pipeline."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("VoiceOps 2026: ZentroMart AI Customer Support Agent Batch Runner")
    print("=" * 70)
    print(f"Input Directory  : {input_dir}")
    print(f"Output Directory : {output_dir}")

    wav_files, conversion_errors = convert_recordings_to_wav(input_dir)

    print(f"WAV Files to Process : {len(wav_files)}")
    print(f"Conversion Failures  : {len(conversion_errors)}")
    print(f"STT Language         : {stt_lang}")
    print(f"TTS Model/Voice      : {tts_model} / {tts_voice}")
    print("-" * 70)

    if not wav_files:
        print("No WAV files are available to process.")
        if conversion_errors:
            print("Some recordings failed to convert. See batch_summary.json.")
        elif not any(
            p.is_file() for p in input_dir.iterdir()
        ):
            print("The input folder is empty.")
        else:
            print("Check that the folder contains supported audio/video files.")

        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "input_directory": str(input_dir),
            "total_files": len(conversion_errors),
            "successful": 0,
            "failed": len(conversion_errors),
            "conversion_failures": conversion_errors,
            "total_duration_seconds": 0.0,
            "results": conversion_errors,
        }
        with (output_dir / "batch_summary.json").open("w", encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2)
        return summary

    # Initialize shared knowledge base and voice agent once per batch.
    kb = KnowledgeBase()
    voice_agent = VoiceAgent(
        stt_lang=stt_lang,
        tts_voice=tts_voice,
        tts_model=tts_model,
    )

    # Keep a separate session for each conversation ID.
    active_sessions: Dict[str, ConversationSession] = {}
    batch_results: List[Dict[str, Any]] = list(conversion_errors)
    success_count = 0
    failure_count = len(conversion_errors)
    t0 = time.time()

    for idx, audio_file in enumerate(wav_files, 1):
        conv_id = extract_conversation_id(audio_file)
        if conv_id not in active_sessions:
            active_sessions[conv_id] = ConversationSession(
                conversation_id=conv_id,
                kb=kb,
            )

        session = active_sessions[conv_id]
        out_audio_path = output_dir / f"{audio_file.stem}_reply.wav"
        out_json_path = output_dir / f"{audio_file.stem}_result.json"

        print(f"[{idx}/{len(wav_files)}] Processing '{audio_file.name}' (Conv ID: {conv_id})...")

        try:
            turn_output = voice_agent.process_audio_turn(
                audio_file_path=audio_file,
                session=session,
                output_file_path=out_audio_path,
            )

            turn_res = turn_output.get("turn_result", {})
            record = {
                "input_file": audio_file.name,
                "conversation_id": conv_id,
                "turn": turn_res.get("turn", 1),
                "transcript": turn_output.get("transcript", ""),
                "reply": turn_output.get("raw_reply", ""),
                "spoken_reply": turn_output.get("spoken_reply", ""),
                "decision": turn_res.get("decision", "answer"),
                "tool_calls": turn_res.get("tool_calls", []),
                "evidence": turn_res.get("evidence", []),
                "verified": turn_res.get("verified", False),
                "output_audio": str(out_audio_path) if out_audio_path.exists() else None,
                "status": "success",
                "stt_error": turn_output.get("stt_error"),
                "tts_error": turn_output.get("tts_error"),
            }
            success_count += 1
            print(f"    Transcript : {record['transcript'] or '[No Speech Detected]'}")
            print(f"    Reply      : {record['reply'][:90]}...")
            print(f"    Decision   : {record['decision']} | Tools: {record['tool_calls']}")

        except Exception as err:
            failure_count += 1
            record = {
                "input_file": audio_file.name,
                "conversation_id": conv_id,
                "status": "error",
                "error": str(err),
            }
            print(f"    ERROR processing file: {err}")

        with out_json_path.open("w", encoding="utf-8") as jf:
            json.dump(record, jf, indent=2, ensure_ascii=False)

        batch_results.append(record)

    total_time = time.time() - t0
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_directory": str(input_dir),
        "total_files": len(wav_files) + len(conversion_errors),
        "wav_files_processed": len(wav_files),
        "successful": success_count,
        "failed": failure_count,
        "conversion_failures": conversion_errors,
        "total_duration_seconds": round(total_time, 2),
        "results": batch_results,
    }

    with (output_dir / "batch_summary.json").open("w", encoding="utf-8") as sf:
        json.dump(summary, sf, indent=2, ensure_ascii=False)

    print("=" * 70)
    print(f"Batch Processing Complete in {total_time:.2f}s")
    print(
        f"WAV processed: {len(wav_files)} | "
        f"Success: {success_count} | Failed: {failure_count}"
    )
    print(f"Structured results and summary written to: {output_dir}")
    print("=" * 70)
    return summary


if __name__ == "__main__":
    args = parse_args()
    try:
        run_batch_pipeline(
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output_dir),
            stt_lang=args.stt_lang,
            tts_voice=args.tts_voice,
            tts_model=args.tts_model,
        )
    except (FileNotFoundError, NotADirectoryError, RuntimeError) as exc:
        print(f"FATAL ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
