"""LLM 总结模块 —— 调用 LLM API 对转录文本进行总结。"""

import os
import json
from pathlib import Path

import httpx


# 默认 prompt 模板路径
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "summary.md"

# LLM API（兼容 OpenAI 格式）
LLM_API_URL = "https://api.llm.com/v1/chat/completions"


def _load_prompt_template() -> str:
    """加载总结 prompt 模板。"""
    if PROMPT_TEMPLATE_PATH.exists():
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    # 回退：内联模板
    return """请根据以下视频的转录文本，用中文生成一份结构化的内容总结。

## 视频信息
- 文件名: {video_name}
- 时长: {duration}
- 检测语言: {language}

## 转录文本
{transcript}

请输出：1) 一句话概述 2) 核心要点（3-5条）3) 详细总结 4) 关键结论/行动项
"""


def _format_duration(seconds: float) -> str:
    """格式化时长为可读字符串。"""
    seconds = round(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}小时{m}分{s}秒"
    if m > 0:
        return f"{m}分{s}秒"
    return f"{s}秒"


def _call_llm(
    prompt: str,
    api_key: str,
    model: str = "llm-chat",
    max_tokens: int = 4096,
) -> str:
    """调用 LLM API（OpenAI 兼容格式）。

    Args:
        prompt: 用户消息内容
        api_key: LLM API Key
        model: 模型 ID（llm-chat 或 llm-reasoner）
        max_tokens: 最大输出 token

    Returns:
        LLM 的回复文本

    Raises:
        RuntimeError: API 调用失败
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(
                LLM_API_URL,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                if "error" in error_json:
                    error_detail = error_json["error"].get("message", error_detail)
            except (json.JSONDecodeError, KeyError):
                pass
            raise RuntimeError(
                f"LLM API error (HTTP {response.status_code}): {error_detail}"
            )

        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            raise RuntimeError("LLM API returned empty response")

        return choices[0]["message"]["content"].strip()

    except httpx.RequestError as e:
        raise RuntimeError(f"Network request failed: {e}")


def summarize(
    transcript: dict,
    api_key: str | None = None,
    model: str = "llm-chat",
) -> str:
    """对转录结果进行总结。

    Args:
        transcript: transcribe() 返回的 dict，包含 text, duration, language 等
        api_key: LLM API Key，不传则从环境变量 LLM_API_KEY 读取
        model: 模型 ID（默认 llm-chat）

    Returns:
        总结文本

    Raises:
        ValueError: 没有 API Key
        RuntimeError: 总结失败
    """
    api_key = api_key or os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError(
            "LLM API Key not set. Set environment variable LLM_API_KEY,\n"
            "or pass --api-key argument.\n"
            "Get an API Key: https://platform.llm.com/"
        )

    template = _load_prompt_template()

    full_text = transcript.get("text", "")
    if not full_text:
        raise ValueError("Transcript is empty")

    # 构建 prompt（带时间戳格式方便定位）
    segments = transcript.get("segments", [])
    if segments:
        anchors = []
        for seg in segments:
            minute = int(seg["start"] // 60)
            second = int(seg["start"] % 60)
            anchors.append(f"[{minute:02d}:{second:02d}] {seg['text']}")
        formatted_text = "\n".join(anchors)
    else:
        formatted_text = full_text

    prompt = template.format(
        video_name=transcript.get("video_name", "unknown"),
        duration=_format_duration(transcript.get("duration", 0)),
        language=transcript.get("language", "unknown"),
        transcript=formatted_text,
    )

    if len(prompt) > 120000:
        print(f"[WARN] Transcript is very long ({len(prompt):,} chars), may take a while...")

    print(f"Calling LLM API ({model}) for summarization...")
    summary = _call_llm(prompt, api_key, model=model)

    return summary
