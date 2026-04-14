"""
Mr. Helmet TTS Generator - FastAPI Web App
本地内部工具：输入文案 → 选语言/音色 → 生成音频 → 下载/试听
"""

import asyncio
import json
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import edge_tts

app = FastAPI(title="Mr. Helmet TTS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

# Voice mapping: language -> {female, male}
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


@app.get("/", response_class=HTMLResponse)
async def generator_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voices": VOICES,
    })


@app.get("/player", response_class=HTMLResponse)
async def player_page(request: Request):
    return templates.TemplateResponse("player.html", {"request": request})


@app.get("/api/voices")
async def get_voices():
    return VOICES


@app.post("/api/generate")
async def generate_audio(request: Request):
    data = await request.json()
    text = data.get("text", "").strip()
    language = data.get("language", "ms-MY")
    gender = data.get("gender", "female")

    if not text:
        return JSONResponse({"error": "请输入文案内容"}, status_code=400)

    voice_info = VOICES.get(language)
    if not voice_info:
        return JSONResponse({"error": "不支持的语言"}, status_code=400)

    voice = voice_info.get(gender, voice_info["female"])

    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    # Generate audio for each paragraph
    segments = []
    temp_files = []
    cumulative_time = 0.0

    for i, para in enumerate(paragraphs):
        temp_path = os.path.join(BASE_DIR, f"_temp_seg_{i}.mp3")
        temp_files.append(temp_path)

        communicate = edge_tts.Communicate(para, voice)
        word_boundaries = []

        with open(temp_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_boundaries.append({
                        "offset": chunk["offset"],
                        "duration": chunk["duration"],
                    })

        # Duration from word boundaries
        if word_boundaries:
            last = word_boundaries[-1]
            duration_sec = (last["offset"] + last["duration"]) / 10_000_000
        else:
            duration_sec = os.path.getsize(temp_path) / 6000

        gap = 0.3 if i < len(paragraphs) - 1 else 0

        segments.append({
            "start": round(cumulative_time, 1),
            "end": round(cumulative_time + duration_sec, 1),
            "text": para
        })
        cumulative_time += duration_sec + gap

    # Concatenate MP3
    output_mp3 = os.path.join(PUBLIC_DIR, "helmet_sales_audio.mp3")
    with open(output_mp3, "wb") as out:
        for tf in temp_files:
            with open(tf, "rb") as inp:
                out.write(inp.read())

    # Cleanup
    for tf in temp_files:
        os.remove(tf)

    # Write segments.json
    output_segments = os.path.join(PUBLIC_DIR, "segments.json")
    with open(output_segments, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    total_duration = segments[-1]["end"] if segments else 0
    file_size = os.path.getsize(output_mp3)

    return {
        "success": True,
        "duration": round(total_duration, 1),
        "duration_fmt": f"{int(total_duration//60)}:{int(total_duration%60):02d}",
        "segments": len(segments),
        "file_size_mb": round(file_size / 1024 / 1024, 1),
        "voice": voice,
        "language": voice_info["label"],
    }


@app.get("/download")
async def download_audio():
    mp3_path = os.path.join(PUBLIC_DIR, "helmet_sales_audio.mp3")
    if not os.path.exists(mp3_path):
        return JSONResponse({"error": "还没有生成音频"}, status_code=404)
    return FileResponse(mp3_path, filename="mr_helmet_audio.mp3", media_type="audio/mpeg")


if __name__ == "__main__":
    import uvicorn
    print("Mr. Helmet TTS Generator")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
