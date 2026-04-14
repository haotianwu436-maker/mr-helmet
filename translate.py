"""
Mr. Helmet TTS 翻译模块
支持 Moonshot / Claude / OpenAI 多种大模型 API
"""

import os
import json
import urllib.request
import urllib.error


def translate_with_llm(
    text: str,
    source_lang: str,
    target_lang: str,
    provider: str = None
) -> str:
    """
    使用大模型翻译文本（同步版本）

    Args:
        text: 待翻译文本
        source_lang: 源语言代码 (zh-CN, en, etc.)
        target_lang: 目标语言代码 (ms, en, th, etc.)
        provider: 翻译服务商 (moonshot, claude, openai) - 默认从环境变量获取

    Returns:
        翻译后的文本
    """
    provider = provider or os.getenv("LLM_PROVIDER", "moonshot")

    if provider == "moonshot":
        return _translate_moonshot(text, source_lang, target_lang)
    elif provider == "claude":
        return _translate_claude(text, source_lang, target_lang)
    elif provider == "openai":
        return _translate_openai(text, source_lang, target_lang)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _translate_moonshot(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """Moonshot API 翻译（推荐）"""
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError("MOONSHOT_API_KEY not set. Get it from https://platform.moonshot.cn/")

    url = "https://api.moonshot.cn/v1/chat/completions"

    prompt = f"""请将以下销售文案从{_get_lang_name(source_lang)}翻译成{_get_lang_name(target_lang)}。
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
    except urllib.error.URLError as e:
        raise Exception(f"Network error: {e}")


def _translate_claude(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """Claude API 翻译"""
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required. Install with: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""请将以下文本从{_get_lang_name(source_lang)}翻译成{_get_lang_name(target_lang)}。
保持销售文案的风格、语气和格式不变。只返回翻译后的文本，不需要其他说明。

原文：
{text}"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def _translate_openai(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """OpenAI API 翻译"""
    try:
        import openai
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)

    prompt = f"""Please translate the following text from {_get_lang_name(source_lang)} to {_get_lang_name(target_lang)}.
Keep the style, tone and format of the sales copy unchanged. Return only the translated text.

Original:
{text}"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content


def _get_lang_name(code: str) -> str:
    """语言代码转名称"""
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
    return lang_map.get(code, code)
