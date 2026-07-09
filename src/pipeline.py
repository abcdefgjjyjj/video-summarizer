"""管线编排模块 -- 串联音频提取、转录、总结三个步骤。"""

import time
from pathlib import Path

from .audio import extract_audio, get_audio_duration
from .transcribe import transcribe, format_transcript_with_timestamps
from .llm import summarize


class PipelineResult:
    """管线执行结果。"""

    def __init__(self):
        self.video_path: str = ""
        self.video_name: str = ""
        self.audio_path: str | None = None
        self.duration: float = 0.0
        self.transcript: dict | None = None
        self.summary: str | None = None
        self.total_time: float = 0.0
        self.errors: list[str] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "video_name": self.video_name,
            "audio_path": self.audio_path,
            "duration": self.duration,
            "language": self.transcript.get("language") if self.transcript else None,
            "transcript_text": self.transcript.get("text") if self.transcript else None,
            "segments": self.transcript.get("segments") if self.transcript else None,
            "summary": self.summary,
            "total_time": round(self.total_time, 1),
            "errors": self.errors,
        }


def run_pipeline(
    video_path: str | Path,
    *,
    model_size: str = "large-v3",
    language: str | None = None,
    device: str = "auto",
    api_key: str | None = None,
    llm_model: str = "llm-chat",
    keep_audio: bool = False,
    keep_transcript: bool = False,
    output_dir: str | Path | None = None,
    dry_run: bool = False,
    hf_mirror: bool = False,
) -> PipelineResult:
    """运行完整的视频总结管线。"""
    result = PipelineResult()
    result.video_path = str(Path(video_path).resolve())
    result.video_name = Path(video_path).name

    t_start = time.time()

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(video_path).parent

    if dry_run:
        print("=" * 50)
        print("[DRY RUN] Steps to execute:")
        print(f"  1. Extract audio -> {Path(video_path).stem}_audio.wav")
        print(f"  2. Transcribe with Faster-Whisper ({model_size})")
        print(f"  3. Summarize with LLM API ({llm_model})")
        print("=" * 50)
        return result

    # ========== Step 1: Extract audio ==========
    print("\n" + "=" * 50)
    print("Step 1/3: Extract audio")
    print("=" * 50)

    try:
        audio_path = extract_audio(video_path, output_dir=output_dir)
        result.audio_path = str(audio_path)
        result.duration = get_audio_duration(audio_path)
        print(f"[OK] Audio extracted: {audio_path.name} ({result.duration:.1f}s)")
    except Exception as e:
        result.errors.append(f"Audio extraction failed: {e}")
        result.total_time = time.time() - t_start
        return result

    # ========== Step 2: Transcribe ==========
    print("\n" + "=" * 50)
    print("Step 2/3: Transcribe audio")
    print("=" * 50)

    try:
        transcript = transcribe(
            audio_path,
            model_size=model_size,
            language=language,
            device=device,
            hf_mirror=hf_mirror,
        )
        transcript["video_name"] = result.video_name
        result.transcript = transcript

        if keep_transcript:
            txt_path = output_dir / f"{Path(video_path).stem}_transcript.txt"
            txt_path.write_text(transcript["text"], encoding="utf-8")
            print(f"[Save] Transcript saved: {txt_path}")

            ts_path = output_dir / f"{Path(video_path).stem}_transcript_timed.txt"
            ts_text = format_transcript_with_timestamps(transcript["segments"])
            ts_path.write_text(ts_text, encoding="utf-8")
            print(f"[Save] Timed transcript saved: {ts_path}")

        print(f"[OK] Transcription done: {len(transcript['text']):,} chars, language={transcript['language']}")
    except Exception as e:
        result.errors.append(f"Transcription failed: {e}")
        result.total_time = time.time() - t_start
        return result

    # ========== Step 3: Summarize ==========
    print("\n" + "=" * 50)
    print("Step 3/3: Generate summary")
    print("=" * 50)

    try:
        summary = summarize(
            transcript,
            api_key=api_key,
            model=llm_model,
        )
        result.summary = summary

        summary_path = output_dir / f"{Path(video_path).stem}_summary.md"
        summary_path.write_text(summary, encoding="utf-8")
        print(f"[Save] Summary saved: {summary_path}")

        print("[OK] Summary generated")
    except Exception as e:
        result.errors.append(f"Summarization failed: {e}")
        result.total_time = time.time() - t_start
        return result

    # ========== Cleanup ==========
    if not keep_audio and result.audio_path:
        audio_file = Path(result.audio_path)
        if audio_file.exists():
            audio_file.unlink()
            print(f"\n[Clean] Removed temp audio: {audio_file.name}")

    result.total_time = time.time() - t_start

    print("\n" + "=" * 50)
    print(f"[Done] Pipeline completed in {result.total_time:.1f}s")
    print("=" * 50)

    return result
