"""
Распознавание голосовых сообщений через OpenAI Whisper API.
Голосовое → текст → обрабатываем как обычное сообщение.
"""
import io
import logging
import os
import tempfile

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Отправляет аудио в Whisper API и возвращает текст.
    Telegram голосовые — OGG/Opus формат.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY не задан")

    # Определяем расширение файла
    ext_map = {
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/wav": "wav",
        "audio/webm": "webm",
    }
    ext = ext_map.get(mime_type, "ogg")
    filename = f"voice.{ext}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            files={"file": (filename, audio_bytes, mime_type)},
            data={
                "model": "whisper-1",
                "language": "ru",
                "response_format": "text"
            }
        )
        response.raise_for_status()
        return response.text.strip()


async def transcribe_voice_anthropic(audio_bytes: bytes) -> str:
    """
    Запасной вариант — конвертируем OGG в текст через ffmpeg + Whisper.
    Используется если нет OpenAI ключа.
    """
    import subprocess

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        ogg_path = f.name

    mp3_path = ogg_path.replace(".ogg", ".mp3")

    try:
        # Конвертируем OGG → MP3 через ffmpeg
        subprocess.run(
            ["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", mp3_path, "-y"],
            capture_output=True,
            check=True
        )

        with open(mp3_path, "rb") as f:
            mp3_bytes = f.read()

        # Whisper через OpenAI
        return await transcribe_voice(mp3_bytes, "audio/mpeg")

    finally:
        for path in [ogg_path, mp3_path]:
            try:
                os.unlink(path)
            except Exception:
                pass
