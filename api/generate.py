"""
Vercel Serverless Function: TTS Audio Generation
Supports both Edge TTS (free) and ElevenLabs (high quality)
Also supports translation via Moonshot/Claude/OpenAI APIs
POST /api/generate
"""

import asyncio
import base64
import json
import os
import urllib.request
import urllib.error

from http.server import BaseHTTPRequestHandler

# Edge TTS voices
EDGE_VOICES = {
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

# ElevenLabs popular multilingual voices
ELEVENLABS_VOICES = {
    "Rachel": {"id": "21m00Tcm4TlvDq8ikWAM", "gender": "female", "desc": "温柔自然，适合介绍"},
    "Matilda": {"id": "XrExE9yKIg1WjnnlVkGX", "gender": "female", "desc": "专业沉稳"},
    "Antoni": {"id": "ErXwobaYiN019PkySvjV", "gender": "male", "desc": "专业有力"},
    "Adam": {"id": "pNInz6obpgDQGcFmaJgB", "gender": "male", "desc": "深沉磁性"},
    "Bill": {"id": "pqHfZKP75CvOlQylNhV4", "gender": "male", "desc": "自信权威"},
    "Sarah": {"id": "EXAVITQu4vr4xnSDxMaL", "gender": "female", "desc": "亲切友好"},
}


def translate_with_llm(text, source_lang, target_lang, provider=None):
    """Translate text using LLM API (Moonshot/Claude/OpenAI)."""
    provider = provider or os.getenv("LLM_PROVIDER", "moonshot")

    if provider == "moonshot":
        return _translate_moonshot(text, source_lang, target_lang)
    elif provider == "claude":
        return _translate_claude(text, source_lang, target_lang)
    elif provider == "openai":
        return _translate_openai(text, source_lang, target_lang)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _translate_moonshot(text, source_lang, target_lang):
    """Translate using Moonshot API."""
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError("MOONSHOT_API_KEY not set")

    url = "https://api.moonshot.cn/v1/chat/completions"

    lang_map = {
        "auto": "自动检测",
        "zh-CN": "中文（简体）",
        "zh-TW": "中文（繁體）",
        "en": "英文",
        "ms": "马来文",
        "th": "泰文",
        "vi": "越南文",
        "id": "印尼文",
        "ja": "日文",
        "ko": "韩文",
    }

    source_lang_name = lang_map.get(source_lang, source_lang)
    target_lang_name = lang_map.get(target_lang, target_lang)

    prompt = f"""请将以下销售文案从{source_lang_name}翻译成{target_lang_name}。
保持原文的风格、语气和格式完全不变。只返回翻译后的文本，不需要任何说明或额外内容。

原文：
{text}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = json.dumps({
        "model": "moonshot-v1",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4096
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"Unexpected API response: {result}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise Exception(f"Moonshot API error ({e.code}): {error_body}")


def _translate_claude(text, source_lang, target_lang):
    """Translate using Claude API."""
    raise NotImplementedError("Claude translation not supported in Vercel environment. Use Moonshot instead.")


def _translate_openai(text, source_lang, target_lang):
    """Translate using OpenAI API."""
    raise NotImplementedError("OpenAI translation not supported in Vercel environment. Use Moonshot instead.")


async def generate_edge_tts(text, language, gender):
    """Generate audio using Edge TTS (free)."""
    import edge_tts

    voice_info = EDGE_VOICES.get(language)
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

    return full_audio, segments, total_duration, voice


def generate_elevenlabs(text, voice_id, api_key):
    """Generate audio using ElevenLabs API (high quality)."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

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
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.4,
            "use_speaker_boost": True
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=55) as resp:
            audio_data = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise ValueError(f"ElevenLabs API error ({e.code}): {body}")

    # Estimate segment timestamps based on text length ratio
    total_chars = sum(len(p) for p in paragraphs)
    # Rough estimate: 15 chars per second for most languages
    estimated_total = total_chars / 12
    segments = []
    cumulative = 0.0
    for para in paragraphs:
        ratio = len(para) / total_chars
        dur = estimated_total * ratio
        segments.append({
            "start": round(cumulative, 1),
            "end": round(cumulative + dur, 1),
            "text": para
        })
        cumulative += dur

    voice_name = voice_id
    for name, info in ELEVENLABS_VOICES.items():
        if info["id"] == voice_id:
            voice_name = name
            break

    return audio_data, segments, cumulative, voice_name


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except Exception:
            self._json_response(400, {"error": "Invalid JSON"})
            return

        text = data.get("text", "").strip()
        engine = data.get("engine", "edge")

        if not text:
            self._json_response(400, {"error": "请输入文案内容"})
            return

        # Handle translation if enabled
        translated_info = {"translated": False}
        original_text = text
        if data.get("translate", False):
            try:
                source_lang = data.get("source_lang", "auto")
                target_lang = data.get("target_lang")
                llm_provider = data.get("llm_provider") or os.getenv("LLM_PROVIDER", "moonshot")

                if not target_lang:
                    self._json_response(400, {"error": "翻译模式需要指定 target_lang"})
                    return

                text = translate_with_llm(text, source_lang, target_lang, llm_provider)
                translated_info = {
                    "translated": True,
                    "original_text": original_text,
                    "translated_text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "llm_provider": llm_provider
                }
            except Exception as e:
                self._json_response(500, {"error": f"翻译失败: {str(e)}"})
                return

        try:
            if engine == "elevenlabs":
                api_key = data.get("api_key", "")
                voice_id = data.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
                if not api_key:
                    self._json_response(400, {"error": "请输入 ElevenLabs API Key"})
                    return
                audio, segments, duration, voice_name = generate_elevenlabs(text, voice_id, api_key)
                engine_label = "ElevenLabs"
            else:
                language = data.get("language", "ms-MY")
                gender = data.get("gender", "female")
                audio, segments, duration, voice_name = asyncio.run(
                    generate_edge_tts(text, language, gender)
                )
                engine_label = "Edge TTS"

            result = {
                "audio_base64": base64.b64encode(audio).decode("ascii"),
                "segments": segments,
                "duration": round(duration, 1),
                "duration_fmt": f"{int(duration//60)}:{int(duration%60):02d}",
                "segment_count": len(segments),
                "file_size_mb": round(len(audio) / 1024 / 1024, 1),
                "voice": voice_name,
                "engine": engine_label,
            }
            # Merge translation info
            result.update(translated_info)

            self._json_response(200, result)

        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def do_GET(self):
        self._json_response(200, {
            "edge_voices": EDGE_VOICES,
            "elevenlabs_voices": ELEVENLABS_VOICES,
        })

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
