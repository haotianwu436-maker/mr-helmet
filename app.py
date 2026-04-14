"""
Mr. Helmet TTS Generator - FastAPI Web App (Local)
本地内部工具：输入文案 -> 选语言/音色 -> 生成音频 -> 下载/试听
支持 Edge TTS (免费) + ElevenLabs (高质量)
"""

import asyncio
import base64
import json
import os
import urllib.request
import urllib.error

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import edge_tts

app = FastAPI(title="Mr. Helmet TTS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

ELEVENLABS_VOICES = {
    "Rachel": {"id": "21m00Tcm4TlvDq8ikWAM", "gender": "female"},
    "Matilda": {"id": "XrExE9yKIg1WjnnlVkGX", "gender": "female"},
    "Sarah": {"id": "EXAVITQu4vr4xnSDxMaL", "gender": "female"},
    "Antoni": {"id": "ErXwobaYiN019PkySvjV", "gender": "male"},
    "Adam": {"id": "pNInz6obpgDQGcFmaJgB", "gender": "male"},
    "Bill": {"id": "pqHfZKP75CvOlQylNhV4", "gender": "male"},
}

EDGE_VOICES = {
    "ms-MY": {"label": "Malay", "female": "ms-MY-YasminNeural", "male": "ms-MY-OsmanNeural"},
    "zh-CN": {"label": "Chinese", "female": "zh-CN-XiaoxiaoNeural", "male": "zh-CN-YunjianNeural"},
    "zh-HK": {"label": "Cantonese", "female": "zh-HK-HiuGaaiNeural", "male": "zh-HK-WanLungNeural"},
    "en-US": {"label": "English", "female": "en-US-JennyNeural", "male": "en-US-GuyNeural"},
    "id-ID": {"label": "Indonesian", "female": "id-ID-GadisNeural", "male": "id-ID-ArdiNeural"},
    "vi-VN": {"label": "Vietnamese", "female": "vi-VN-HoaiMyNeural", "male": "vi-VN-NamMinhNeural"},
    "th-TH": {"label": "Thai", "female": "th-TH-PremwadeeNeural", "male": "th-TH-NiwatNeural"},
    "ja-JP": {"label": "Japanese", "female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"},
    "ko-KR": {"label": "Korean", "female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"},
    "ar-SA": {"label": "Arabic", "female": "ar-SA-ZariyahNeural", "male": "ar-SA-HamedNeural"},
}


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(PUBLIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/player", response_class=HTMLResponse)
async def player():
    with open(os.path.join(PUBLIC_DIR, "player.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/generate")
async def generate_audio(request: Request):
    data = await request.json()
    text = data.get("text", "").strip()
    engine = data.get("engine", "edge")

    if not text:
        return JSONResponse({"error": "请输入文案内容"}, status_code=400)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    if engine == "elevenlabs":
        api_key = data.get("api_key", "")
        voice_id = data.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        if not api_key:
            return JSONResponse({"error": "请输入 ElevenLabs API Key"}, status_code=400)

        full_text = "\n\n".join(paragraphs)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = json.dumps({
            "text": full_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.4, "use_speaker_boost": True}
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                audio = resp.read()
        except urllib.error.HTTPError as e:
            return JSONResponse({"error": f"ElevenLabs API error: {e.read().decode()}"}, status_code=500)

        total_chars = sum(len(p) for p in paragraphs)
        estimated_total = total_chars / 12
        segments, cum = [], 0.0
        for para in paragraphs:
            dur = estimated_total * (len(para) / total_chars)
            segments.append({"start": round(cum, 1), "end": round(cum + dur, 1), "text": para})
            cum += dur

        voice_name = voice_id
        for name, info in ELEVENLABS_VOICES.items():
            if info["id"] == voice_id:
                voice_name = name
                break
        engine_label = "ElevenLabs"

    else:
        language = data.get("language", "ms-MY")
        gender = data.get("gender", "female")
        voice_info = EDGE_VOICES.get(language)
        if not voice_info:
            return JSONResponse({"error": "不支持的语言"}, status_code=400)
        voice = voice_info.get(gender, voice_info["female"])

        segments, audio_chunks, cum = [], [], 0.0
        for i, para in enumerate(paragraphs):
            communicate = edge_tts.Communicate(para, voice)
            boundaries, para_audio = [], bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    para_audio.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    boundaries.append({"offset": chunk["offset"], "duration": chunk["duration"]})

            dur = (boundaries[-1]["offset"] + boundaries[-1]["duration"]) / 10_000_000 if boundaries else len(para_audio) / 6000
            gap = 0.3 if i < len(paragraphs) - 1 else 0
            segments.append({"start": round(cum, 1), "end": round(cum + dur, 1), "text": para})
            audio_chunks.append(bytes(para_audio))
            cum += dur + gap

        audio = b"".join(audio_chunks)
        voice_name = voice
        engine_label = "Edge TTS"

    # Save to public/ for player page
    with open(os.path.join(PUBLIC_DIR, "helmet_sales_audio.mp3"), "wb") as f:
        f.write(audio)
    with open(os.path.join(PUBLIC_DIR, "segments.json"), "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    duration = segments[-1]["end"] if segments else 0
    return {
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "segments": segments,
        "duration": round(duration, 1),
        "duration_fmt": f"{int(duration//60)}:{int(duration%60):02d}",
        "segment_count": len(segments),
        "file_size_mb": round(len(audio) / 1024 / 1024, 1),
        "voice": voice_name,
        "engine": engine_label,
    }


@app.get("/download")
async def download():
    mp3 = os.path.join(PUBLIC_DIR, "helmet_sales_audio.mp3")
    if not os.path.exists(mp3):
        return JSONResponse({"error": "还没有生成音频"}, status_code=404)
    return FileResponse(mp3, filename="mr_helmet_audio.mp3", media_type="audio/mpeg")


if __name__ == "__main__":
    import uvicorn
    print("Mr. Helmet TTS Generator")
    print("Open http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
