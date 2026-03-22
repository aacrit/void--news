"""
Daily Brief generator for void --news.

Produces per-edition editorial briefs:
  - TL;DR text (3-line summary for homepage display)
  - Audio script (BBC World Service-style broadcast)
  - Audio file (Gemini 2.5 Flash TTS, native multi-speaker)

Called as step 7d in the main pipeline, after editorial triage (7c)
and before cluster storage (8).
"""

from .daily_brief_generator import generate_daily_briefs
from .audio_producer import produce_audio
from .voice_rotation import get_voice_for_today, get_voices_for_today

__all__ = ["generate_daily_briefs", "produce_audio", "get_voice_for_today", "get_voices_for_today"]
