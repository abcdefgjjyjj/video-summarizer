#!/usr/bin/env python3
"""
Spawner: launches detached_worker.py as a fully independent process and exits
immediately. LLM CLI sees a ~1s command, but the real work runs for hours
in a separate process tree that survives the parent.

Usage:
    python spawn.py                          # process ALL relevant unprocessed folders
    python spawn.py "folder1" "folder2" ...  # process specific folders
"""
import sys, os, subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
WORKER = PROJECT_DIR / "detached_worker.py"

RELEVANT_PATTERNS = [
    "ACS应用介绍(二)", "电机特殊运动", "1210时序规划与分析", "FC1250时序分析",
    "相机镜头建模", "新版视觉2.0", "AI技术在芯片检测", "视觉2新功能",
    "视觉基础知识", "MIT视觉GP", "视觉GP软件培训-员工H",
    "FC1250所用传感器", "凌华卡与雷赛卡", "基于1210的通讯",
    "建模注意事项",
    "EAP介绍和调试", "EAP的软件安装", "EAP模拟器",
    "设备稳定性能指标参数", "svn提交规则与1250贴片时序",
    "设备模块的封装和应用", "1220框架讲解",
    "Pick&Place工艺讲解(一)", "Pick&Place工艺讲解(二)", "Pick&Place工艺讲解(三)",
    "BGA封装流程", "Memory工艺",
    "1250设备常见问题及其分析方法（一）",
    "1250设备常见问题及其分析方法（二）",
    "1250设备常见问题及其分析方法（三）",
]


def find_unprocessed(base_dir):
    """Return list of relevant folders that don't have _DONE or 培训文档.md."""
    unprocessed = []
    for d in sorted(os.listdir(base_dir)):
        folder = os.path.join(base_dir, d)
        if not os.path.isdir(folder):
            continue

        # Relevance check
        relevant = any(pat in d for pat in RELEVANT_PATTERNS)
        if not relevant:
            continue

        # Already done?
        if os.path.exists(os.path.join(folder, "_DONE")):
            continue
        has_doc = any(f.endswith("_培训文档.md") or f.endswith("培训文档.md") for f in os.listdir(folder))
        if has_doc:
            continue

        unprocessed.append(folder)

    return unprocessed


def main():
    if len(sys.argv) > 1:
        folders = sys.argv[1:]
    else:
        base = r"<training-videos-directory>"
        folders = find_unprocessed(base)

    if not folders:
        print("No unprocessed folders found.")
        return

    print(f"Spawning detached worker for {len(folders)} folder(s):")
    for f in folders:
        print(f"  {os.path.basename(f)}")
    print()

    # Build command
    cmd = [sys.executable, str(WORKER)] + folders

    # Launch as fully detached process
    if sys.platform == "win32":
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )

    print(f"Launched! PID={proc.pid}")
    print(f"Each folder will get a _worker.log with progress.")
    print(f"A _DONE marker file appears when complete.")
    print(f"\nCheck status: find . -name '_DONE' | wc -l")
    print(f"Check logs:   cat <folder>/_worker.log")
    print(f"Check pid:    tasklist | findstr {proc.pid}")

    # Exit immediately — worker runs independently
    sys.exit(0)


if __name__ == "__main__":
    main()
