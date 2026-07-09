"""语音转文字模块 -- 使用 Faster-Whisper 将音频转录为文本。"""

import os
import socket
import time
from pathlib import Path


# HF 镜像站列表，按优先级排序
_HF_MIRRORS = [
    "https://hf-mirror.com",
]


def _check_host(host: str, port: int = 443, timeout: float = 3.0) -> bool:
    """快速检测主机是否可达。"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, OSError):
        return False


def _setup_hf_env(force_mirror: bool = False):
    """配置 HuggingFace 环境：本地缓存 + 端点选择。

    - HF_HOME 指向项目目录下的 models/huggingface/，模型不散落全局
    - 如果 hf-mirror.com 被显式指定或 huggingface.co 不通，则自动切换到镜像站
    """
    # —— 本地缓存路径 ——
    if not os.environ.get("HF_HOME"):
        project_root = Path(__file__).resolve().parent.parent
        local_cache = project_root / "models" / "huggingface"
        local_cache.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(local_cache)
        print(f"[Info] HF_HOME={local_cache}")

    # —— 端点选择 ——
    if os.environ.get("HF_ENDPOINT"):
        print(f"[Info] Using HF_ENDPOINT={os.environ['HF_ENDPOINT']}")
        return

    if force_mirror or not _check_host("huggingface.co"):
        for mirror in _HF_MIRRORS:
            host = mirror.replace("https://", "").replace("http://", "").rstrip("/")
            if _check_host(host):
                os.environ["HF_ENDPOINT"] = mirror
                os.environ["HF_HUB_DISABLE_XET"] = "1"
                print(f"[Info] Auto-switched to HF mirror: {mirror} (Xet disabled)")
                return

    print("[Info] Using default huggingface.co endpoint")


def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 HH:MM:SS 或 MM:SS 格式。"""
    seconds = round(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def transcribe(
    audio_path: str | Path,
    model_size: str = "large-v3",
    language: str | None = None,
    device: str = "auto",
    hf_mirror: bool = False,
) -> dict:
    """使用 Faster-Whisper 将音频转录为文本。

    Args:
        audio_path: 音频文件路径 (.wav)
        model_size: 模型大小，可选 tiny/base/small/medium/large-v3
        language: 语言代码，None 为自动检测（推荐）
        device: 设备，可选 auto/cpu/cuda
        hf_mirror: 强制使用 HF 镜像站（hf-mirror.com）

    Returns:
        dict: {
            "text": "完整转录文本",
            "segments": [{"start": 0.0, "end": 2.5, "text": "..."}, ...],
            "language": "zh",
            "duration": 120.5,
            "model": "large-v3",
        }

    Raises:
        FileNotFoundError: 音频文件不存在
        RuntimeError: 转录失败
    """
    audio_path = Path(audio_path).resolve()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # 在导入 faster_whisper 前配置 HF 环境（缓存路径 + 端点）
    _setup_hf_env(force_mirror=hf_mirror)

    from faster_whisper import WhisperModel

    # 自动推断 compute_type
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    compute_type = "float16" if device == "cuda" else "int8"
    if model_size == "large-v3" and device == "cpu":
        # CPU 上 large-v3 用 int8 量化以节省内存和加速
        compute_type = "int8"

    print(f"Loading Faster-Whisper model: {model_size} ({device}, {compute_type})")
    t0 = time.time()

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        raise RuntimeError(f"Failed to load Whisper model ({model_size}): {e}")

    load_time = time.time() - t0
    print(f"Model loaded in {load_time:.1f}s")

    print("Transcribing...")
    t1 = time.time()

    try:
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,  # 过滤静音段
        )

        segments = []
        full_text_parts = []

        for seg in segments_iter:
            segments.append({
                "start": round(seg.start, 1),
                "end": round(seg.end, 1),
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text.strip())

            # 每处理一段显示进度
            if len(segments) % 10 == 0:
                elapsed = time.time() - t1
                print(f"  Processed {len(segments)} segments, {elapsed:.1f}s...")

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")

    transcribe_time = time.time() - t1
    full_text = " ".join(full_text_parts)

    duration = segments[-1]["end"] if segments else 0.0
    speed = duration / transcribe_time if transcribe_time > 0 else 0

    print(f"Transcription done! {len(segments)} segments, {transcribe_time:.1f}s")
    print(f"Realtime factor: {speed:.1f}x")

    return {
        "text": full_text,
        "segments": segments,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration": round(duration, 1),
        "model": model_size,
    }


def format_transcript_with_timestamps(segments: list[dict]) -> str:
    """将带时间戳的片段列表格式化为易读文本。

    Args:
        segments: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]

    Returns:
        带时间戳的格式化文本
    """
    lines = []
    for seg in segments:
        start_ts = _format_timestamp(seg["start"])
        end_ts = _format_timestamp(seg["end"])
        lines.append(f"[{start_ts} -> {end_ts}] {seg['text']}")
    return "\n".join(lines)
