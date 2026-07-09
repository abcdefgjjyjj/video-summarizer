#!/usr/bin/env python3
"""视频总结工具 -- 本地提取 + 云端总结。

用法:
    python summarize.py video.mp4
    python summarize.py video.mp4 --model base --keep-transcript
    python summarize.py video.mp4 --api-key sk-xxx --llm-model llm-chat
"""

import argparse
import sys
from pathlib import Path

# 确保 src 在 Python 路径中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="本地视频内容总结工具 -- 本地提取音频并转写，云端 LLM 生成总结",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python summarize.py meeting.mp4
  python summarize.py lecture.mkv -m medium --keep-transcript
  python summarize.py demo.mp4 --language zh --llm-model llm-chat
  python summarize.py video.mp4 --dry-run
        """,
    )

    parser.add_argument(
        "video",
        type=str,
        help="视频文件路径",
    )

    parser.add_argument(
        "-m", "--model",
        type=str,
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper 模型大小 (默认: large-v3)。越小越快但准确率越低。",
    )

    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="视频语言代码，不指定则自动检测 (如 zh, en, ja)",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="推理设备 (默认: auto，自动选择 CUDA 或 CPU)",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="LLM API Key (优先使用环境变量 LLM_API_KEY)",
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        default="llm-chat",
        help="LLM 模型 ID (默认: llm-chat, 也可用 llm-reasoner)",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出目录 (默认: 视频所在目录)",
    )

    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="保留提取的音频文件 (默认删除)",
    )

    parser.add_argument(
        "--keep-transcript",
        action="store_true",
        help="保留转录文本文件 (默认删除)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览将要执行的步骤，不实际运行",
    )

    parser.add_argument(
        "--hf-mirror",
        action="store_true",
        help="强制使用 HF 国内镜像 (hf-mirror.com) 下载模型",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[ERROR] Video file not found: {args.video}")
        sys.exit(1)

    if not args.dry_run:
        print(f"[Video] {video_path.name}")
        print(f"  Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"  Transcriber: {args.model} ({args.device})")
        print(f"  LLM: {args.llm_model}")

    result = run_pipeline(
        video_path=video_path,
        model_size=args.model,
        language=args.language,
        device=args.device,
        api_key=args.api_key,
        llm_model=args.llm_model,
        keep_audio=args.keep_audio,
        keep_transcript=args.keep_transcript,
        output_dir=args.output,
        dry_run=args.dry_run,
        hf_mirror=args.hf_mirror,
    )

    if result.errors:
        print(f"\n[ERROR] Pipeline failed with {len(result.errors)} error(s):")
        for i, err in enumerate(result.errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)

    if result.summary:
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print("=" * 50)
        print(result.summary)


if __name__ == "__main__":
    main()
