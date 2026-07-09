#!/usr/bin/env python3
"""Master batch processor: spawns process_one.py for each remaining video as a subprocess."""
import subprocess, sys, os, time
from pathlib import Path

BASE = r"<training-videos-directory>"
SCRIPT = Path(__file__).resolve().parent / "process_one.py"

TARGETS = [
    "42.1250设备常见问题及其分析方法（二）-员工A",
    "43.1250设备常见问题及其分析方法（三）-员工A",
    "44.设备模块的封装和应用-员工B",
    "48.1220框架讲解-员工C",
    "49.BGA封装流程介绍-员工D",
    "52.EAP的软件安装过程和四大模块的应用-员工E",
    "53.视觉2新功能介绍和标定方式-员工B",
    "54.Memory工艺培训",
    "56.EAP模拟器和EAP代码的应用-员工E",
    "57. 视觉基础知识 及 镜头相机选型 - 员工F",
    "59.MIT视觉GP软件培训-Colleague G",
    "60.视觉GP软件培训-员工H",
    "61.FC1250时序分析-员工I",
]

LOG_FILE = Path(__file__).resolve().parent / "batch_master.log"

total = len(TARGETS)
results = []

for i, t in enumerate(TARGETS):
    folder = os.path.join(BASE, t)
    if not os.path.isdir(folder):
        print(f"[{i+1}/{total}] MISSING: {t}", flush=True)
        continue

    # Check if already done
    has_doc = any(f.endswith("_培训文档.md") or f.endswith("培训文档.md") for f in os.listdir(folder))
    if has_doc:
        print(f"[{i+1}/{total}] SKIP (done): {t}", flush=True)
        results.append((t, "SKIP"))
        continue

    print(f"[{i+1}/{total}] START: {t}", flush=True)
    t0 = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), folder],
            capture_output=True, text=True, timeout=3600,
            cwd=str(Path(__file__).resolve().parent),
        )
        elapsed = time.time() - t0
        if result.returncode == 0:
            print(f"[{i+1}/{total}] DONE ({elapsed:.0f}s): {t}", flush=True)
            results.append((t, f"DONE_{elapsed:.0f}s"))
        else:
            print(f"[{i+1}/{total}] FAIL ({elapsed:.0f}s, rc={result.returncode}): {t}", flush=True)
            results.append((t, f"FAIL_rc{result.returncode}"))
            # Print last few lines of stderr
            if result.stderr:
                lines = result.stderr.strip().split("\n")
                for line in lines[-5:]:
                    print(f"  STDERR: {line}", flush=True)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        print(f"[{i+1}/{total}] TIMEOUT ({elapsed:.0f}s): {t}", flush=True)
        results.append((t, "TIMEOUT"))
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[{i+1}/{total}] ERROR ({elapsed:.0f}s): {t} - {e}", flush=True)
        results.append((t, f"ERROR_{e}"))

    # Log progress
    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        lf.write(f"{time.strftime('%H:%M:%S')} {t} -> {results[-1][1]}\n")

print(f"\n{'='*60}", flush=True)
print(f"BATCH COMPLETE", flush=True)
for name, status in results:
    print(f"  {status:20s} {name}", flush=True)
print(f"{'='*60}", flush=True)
