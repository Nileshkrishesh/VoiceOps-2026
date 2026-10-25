"""Voice Agent integrating Gnani.ai Speech-to-Text and Text-to-Speech.

Implements Step 4 of VoiceOps 2026:
- Uses official Gnani STT (GnaniSTTClient) and TTS (GnaniTTSClient).
- Formats dates with full year and long order numbers with digit spacing for acoustic clarity.
- Feeds recognized speech directly into the Step 3 ConversationManager.
- Synthesizes spoken replies to WAV audio files.
- Strictly adheres to capstone rules: no external fallback speech providers allowed.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

from src.config import (
    GNANI_API_KEY, GNANI_STT_LANG, GNANI_TTS_VOICE,
    GNANI_TTS_MODEL, GNANI_TTS_LANG, OUTPUTS_DIR
)
from src.conversation import ConversationSession

class VoiceAgent:
    """End-to-end voice processing wrapper using Gnani.ai."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        stt_lang: str = GNANI_STT_LANG,
        tts_voice: str = GNANI_TTS_VOICE,
        tts_model: str = GNANI_TTS_MODEL,
        tts_lang: str = GNANI_TTS_LANG,
    ):
        self.api_key = api_key or os.getenv("GNANI_API_KEY") or ""
        self.stt_lang = stt_lang
        self.tts_voice = tts_voice
        self.tts_model = tts_model
        self.tts_lang = tts_lang
        
        self.stt_client = None
        self.tts_client = None
        self._init_gnani()

    def _init_gnani(self):
        """Initialize official Gnani SDK clients if API key is present."""
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                from gnani.stt import GnaniSTTClient
                from gnani.tts import GnaniTTSClient
                # Gnani clients automatically read GNANI_API_KEY from env or accepts token
                os.environ["GNANI_API_KEY"] = self.api_key
                self.stt_client = GnaniSTTClient()
                self.tts_client = GnaniTTSClient()
            except Exception as e:
                # Log initialization error
                pass

    def is_gnani_active(self) -> bool:
        """Check if live Gnani voice services are ready."""
        return self.stt_client is not None and self.tts_client is not None

    def normalize_for_speech(self, text: str) -> str:
        """Format text for acoustic naturalness.
        
        - Breaks 8-digit order numbers into spaced digit pairs for clear spoken pronunciation.
        - Expands date patterns to include full year.
        - Expands currency abbreviations like 'Rs.' or '₹' to 'Rupees'.
        """
        if not text:
            return ""
            
        speech_text = text
        # Format currency
        speech_text = re.sub(r"[₹]\s*(\d+)", r"Rupees \1", speech_text)
        speech_text = re.sub(r"\bRs\.?\s*(\d+)", r"Rupees \1", speech_text)
        
        # Format 8-digit order IDs into spaced digit groups: 8978 2837
        def _space_digits(m):
            digits = m.group(1).replace(" ", "")
            return f"{digits[:4]} {digits[4:]}"
            
        speech_text = re.sub(r"\border\s*#?\s*(\d{4}\s*\d{4}|\d{8})\b", _space_digits, speech_text, flags=re.IGNORECASE)
        
        # Ensure year is present for dates like '20 October' -> '20 October 2026'
        speech_text = re.sub(
            r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December))\b(?!\s*\d{4})",
            r"\1 2026",
            speech_text,
            flags=re.IGNORECASE
        )
        return speech_text

    def process_audio_turn(
        self,
        audio_file_path: Union[str, Path],
        session: ConversationSession,
        output_file_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Process a single audio file through Gnani STT -> Brain -> Gnani TTS."""
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Input audio file not found: {audio_path}")

        # 1. Transcribe customer audio via Gnani STT
        heard_text = ""
        stt_error = None
        if self.stt_client:
            try:
                stt_res = self.stt_client.transcribe(
                    audio=str(audio_path),
                    language_code=self.stt_lang,
                )
                heard_text = stt_res.get("transcript", "").strip()
            except Exception as e:
                stt_error = str(e)
        else:
            stt_error = "GNANI_API_KEY is not configured in environment."

        # Handle empty or unclear transcription
        if not heard_text.strip():
            if stt_error:
                reply_text = f"Audio received, but Gnani STT could not process it ({stt_error}). Please ensure GNANI_API_KEY is set."
            else:
                reply_text = "Sorry, I didn't catch that. Could you say it again?"
            turn_result = {
                "turn": len(session.history) + 1,
                "reply": reply_text,
                "decision": "clarify",
                "tool_calls": [],
                "evidence": [],
                "verified": session.order_verified,
            }
        else:
            # 2. Feed recognized text into existing Step 3 conversation agent
            turn_result = session.process_turn(heard_text)
            reply_text = turn_result["reply"]

        # 3. Format reply for speech and synthesize via Gnani TTS
        speech_ready_reply = self.normalize_for_speech(reply_text)
        
        if output_file_path is None:
            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
            output_file_path = OUTPUTS_DIR / f"{audio_path.stem}_reply.wav"

        tts_success = False
        tts_error = None
        if self.tts_client:
            try:
                self.tts_client.synthesize(
                    text=speech_ready_reply,
                    voice=self.tts_voice,
                    model=self.tts_model,
                    language=self.tts_lang,
                    output_file=str(output_file_path),
                )
                tts_success = True
            except Exception as e:
                tts_error = str(e)

        return {
            "input_audio": str(audio_path),
            "transcript": heard_text,
            "raw_reply": reply_text,
            "spoken_reply": speech_ready_reply,
            "output_audio": str(output_file_path) if tts_success else None,
            "turn_result": turn_result,
            "stt_error": stt_error,
            "tts_error": tts_error,
        }
