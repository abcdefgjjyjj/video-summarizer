"""音频提取模块 —— 使用 ffmpeg 从视频中提取音频轨道。"""

import subprocess
import shutil
import sys
from pathlib import Path


def check_ffmpeg() -> bool:
    """检查系统中是否安装了 ffmpeg。"""
    return shutil.which("ffmpeg") is not None


def extract_audio(
    video_path: str | Path,
    output_dir: str | Path | None = None,
    sample_rate: int = 16000,
) -> Path:
    """从视频文件中提取音频，转为 Whisper 友好的 WAV 格式。

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录，默认为视频同目录
        sample_rate: 采样率，默认 16000 Hz（Whisper 最佳输入）

    Returns:
        提取出的音频文件路径 (.wav)

    Raises:
        FileNotFoundError: 视频文件不存在
        RuntimeError: ffmpeg 不可用或提取失败
    """
    if not check_ffmpeg():
        raise RuntimeError(
            "ffmpeg not found. Please install:\n"
            "  Windows: winget install ffmpeg  or  choco install ffmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   sudo apt install ffmpeg"
        )

    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    output_dir = Path(output_dir or video_path.parent)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = video_path.stem
    output_path = output_dir / f"{stem}_audio.wav"

    # ffmpeg 命令：提取音频，转为 16kHz 单声道 16-bit PCM WAV
    # -vn: 不要视频流
    # -acodec pcm_s16le: 16-bit PCM
    # -ar {sample_rate}: 采样率
    # -ac 1: 单声道
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-y",  # 覆盖已有文件
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Audio extraction timed out (10 min limit), check the video file")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{stderr}")

    if not output_path.exists():
        raise RuntimeError(f"Audio file was not created: {output_path}")

    return output_path


def get_audio_duration(audio_path: str | Path) -> float:
    """获取音频文件时长（秒），使用 ffprobe。

    Args:
        audio_path: 音频文件路径

    Returns:
        时长（秒）
    """
    audio_path = Path(audio_path)
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return 0.0

    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0
