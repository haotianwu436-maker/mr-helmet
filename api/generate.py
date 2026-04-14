"""
Vercel Serverless Function: TTS Audio Generation
POST /api/generate
Returns: { audio_base64, segments, duration, ... }
"""

import asyncio
import base64
import json
import os
import tempfile

from http.server import BaseHTTPRequestHandler


# Voice mapping
VOICES = {
    "ms-MY": {"label": "马来语 (Malay)", "female": "ms-MY-YasminNeural", "male": "ms-MY-OsmanNeural"},
    "zh-CN": {"label": "中文普通话", "female": "zh-CN-XiaoxiaoNeural", "male": "zh-CN-YunjianNeural"},
    "zh-HK": {"label": "粤语 (Cantonese)", "female": "zh-HK-HiuGaaiNeural", "male": "zh-HK-WanLungNeural"},
    "en-US": {"label": "英语 (English)", "female": "en-US-JennyNeural", "male": "en-US-GuyNeural"},
    "id-ID": {"label": "印尼语 (Indonesian)", "female": "id-ID-GadisNeural", "male": "id-ID-ArdiNeural"},
    "vi-VN": {"label": "越南语 (Vietnamese)", "female": "vi-VN-HoaiMyNeural", "male": "vi-VN-NamMinhNeural"},
    "th-TH": {"label": "泰语 (Thai)", "female": "th-TH-PremwadeeNeural", "male": "th-TH-NiwatNeural"},
    "ja-JP": {"label": "日语 (Japanese)", "female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"},
    "ko-KR": {"label": "韩语 (Korean)", "female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"},
    "ar-SA": {"label": "阿拉伯语 (Arabic)", "female": "ar-SA-ZariyahNeural", "male": "ar-SA-HamedNeural"},
}


async def generate_tts(text, language, gender):
    import edge_tts

    voice_info = VOICES.get(language)
    if not voice_info:
        raise ValueError("不支持的语言")
    voice = voice_info.get(gender, voice_info["female"])

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    segments = []
    audio_chunks = []
    cumulative_time = 0.0

    for i, para in enumerate(paragraphs):
        communicate = edge_tts.Communicate(para, voice)
        word_boundaries = []
        para_audio = bytearray()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                para_audio.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "offset": chunk["offset"],
                    "duration": chunk["duration"],
                })

        if word_boundaries:
            last = word_boundaries[-1]
            duration_sec = (last["offset"] + last["duration"]) / 10_000_000
        else:
            duration_sec = len(para_audio) / 6000

        gap = 0.3 if i < len(paragraphs) - 1 else 0

        segments.append({
            "start": round(cumulative_time, 1),
            "end": round(cumulative_time + duration_sec, 1),
            "text": para
        })

        audio_chunks.append(bytes(para_audio))
        cumulative_time += duration_sec + gap

    full_audio = b"".join(audio_chunks)
    total_duration = segments[-1]["end"] if segments else 0

    return {
        "audio_base64": base64.b64encode(full_audio).decode("ascii"),
        "segments": segments,
        "duration": round(total_duration, 1),
        "duration_fmt": f"{int(total_duration//60)}:{int(total_duration%60):02d}",
        "segment_count": len(segments),
        "file_size_mb": round(len(full_audio) / 1024 / 1024, 1),
        "voice": voice,
        "language": voice_info["label"],
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        text = data.get("text", "").strip()
        language = data.get("language", "ms-MY")
        gender = data.get("gender", "female")

        if not text:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "请输入文案内容"}).encode())
            return

        try:
            result = asyncio.run(generate_tts(text, language, gender))

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"voices": VOICES}).encode())
