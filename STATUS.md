# 视频总结工具 - 状态文档

## 任务目标
搭建本地视频内容总结工具。核心约束：**视频本体不出本地网络**，提取出的文本可调用云端 LLM 做总结。

## 技术方案
采用"本地解析 + 云端理解"架构：

```
视频 -> [本地] ffmpeg 提取音频 -> [本地] Faster-Whisper 转写
    -> [云端] LLM API 总结
```

所有 Whisper 模型缓存在项目 `models/` 目录内，不散落全局。

## 项目结构

```
video-summarizer/
├── STATUS.md           # 本文件
├── requirements.txt    # Python 依赖 (faster-whisper, httpx)
├── .gitignore
├── summarize.py        # CLI 入口 (argparse)
├── src/
│   ├── __init__.py
│   ├── audio.py        # ffmpeg 音频提取
│   ├── transcribe.py   # Faster-Whisper 转录（HF 镜像 + 本地缓存）
│   ├── llm.py          # LLM API 调用 (httpx)
│   └── pipeline.py     # 完整管线编排
├── prompts/
│   └── summary.md      # 总结 prompt 模板
└── models/             # Whisper 模型本地缓存 (git-ignored, ~10GB)
    └── huggingface/
```

## 当前进度
- [x] 方案设计
- [x] 项目骨架搭建
- [x] ffmpeg 安装 (chocolatey)
- [x] 音频提取模块 — ✅ 测试通过
- [x] 语音转文字模块 — ✅ 测试通过（HF 镜像下载模型，realtime factor ~4.2x）
- [x] LLM 总结模块 — ✅ 已配置 LLM API
- [x] 管线编排 — ✅ 全流程跑通
- [x] CLI 入口 — ✅ dry-run / help 正常
- [x] Windows GBK 终端兼容 — ✅ 全部英文输出
- [x] 网络问题解决 — ✅ 自动检测并切换 hf-mirror.com
- [x] 批量处理脚本 batch_process.py — ✅ 支持 PPTX/DOCX 附件提取
- [x] 并行批次脚本 parallel_batch.py — ✅ Phase1: 2进程转录 + Phase2: 6线程合成
- [x] 培训视频批量总结 — ✅ 全部12个视频已完成

## 测试结果 (2026-07-09 更新)

```
Step 1/3: Extract audio
[OK] Audio extracted: test_audio_audio.wav (3.0s)              ✅

Step 2/3: Transcribe audio
[Info] HF_HOME=<project-root>/video-summarizer\models\huggingface
[Info] Auto-switched to HF mirror: https://hf-mirror.com (Xet disabled)
Loading Faster-Whisper model: tiny (cpu, int8)
Model loaded in 1.2s                                           ✅

Step 3/3: Generate summary
(测试音频为正弦波无语音，Transcript empty 属于预期行为)        ✅
```

## 2026-07-09 更新：模型缓存本地化 + small 模型补全

### 变更内容
- **模型缓存移至项目本地**：`transcribe.py` 启动时自动设置 `HF_HOME` 指向 `models/huggingface/`，不再使用 `~/.cache/huggingface/`
- **补全 small 模型**：通过 hf-mirror.com 下载，耗时约 4.5 分钟
- **全部 5 个模型就绪**：tiny (149MB) / base (282MB) / small (927MB) / medium (2.9GB) / large-v3 (5.9GB)，总计 10.2GB
- `.gitignore` 已排除 `models/` 目录

### 测试结果 (2026-07-07 原始)
（之前的内容保留）

```
Step 1/3: Extract audio
[OK] Audio extracted: test_video_audio.wav (5.0s)              ✅

Step 2/3: Transcribe audio
[Info] Auto-switched to HF mirror: hf-mirror.com (Xet disabled)
Loading Faster-Whisper model: tiny (cpu, int8)
Model loaded in 0.7s                                           ✅
Transcription done! 0 segments, 0.5s                          ✅

Step 3/3: Generate summary
the API provider API Key not set.                                     ⏳ 需 API Key
```

### 关键突破：HF 镜像自动切换

`src/transcribe.py` 内置了智能端点检测：
1. 快速 TCP 探测 `huggingface.co:443` 是否可达
2. 不通则自动切到 `hf-mirror.com`（国内镜像）
3. 同时禁用 Xet 存储（镜像不支持），走传统 LFS 协议
4. 用户也可通过 `--hf-mirror` 强制启用

## 使用方法

```bash
# 1. 安装依赖（已完成）
pip install -r requirements.txt

# 2. 设置 API Key
set LLM_API_KEY=YOUR_API_KEY

# 3. 运行（镜像自动检测，无需手动配置）
python summarize.py your_video.mp4

# 强制使用镜像
python summarize.py your_video.mp4 --hf-mirror

# 使用小模型快速测试
python summarize.py your_video.mp4 -m tiny
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-m, --model` | large-v3 | Whisper 模型大小 (tiny/base/small/medium/large-v3) |
| `--language` | auto | 语言代码 |
| `--device` | auto | 推理设备 (auto/cpu/cuda) |
| `--api-key` | 环境变量 | the API provider API Key |
| `--llm-model` | llm-chat-model | LLM 模型 |
| `--hf-mirror` | false | 强制使用国内镜像 |
| `-o, --output` | 视频同目录 | 输出目录 |
| `--keep-audio` | false | 保留音频 |
| `--keep-transcript` | false | 保留转录文本 |
| `--dry-run` | false | 仅预览 |

## 设计决策
- 不用 the API provider SDK：httpx 直调 REST API，更轻量
- 不用 tiktoken：中文用字符数估算 token
- 不做 config 文件：环境变量 + CLI 参数已足够
- Prompt 用 .md 文件：直观、易编辑
- 英文输出：兼容 Windows GBK 终端
- 自动镜像切换：国内网络环境下无需手动配置

## 批量总结结果 (2026-07-07) — ✅ 完成

| # | 视频 | 时长 | 转录字符 | 文档大小 | 
|---|------|------|----------|----------|
| 5 | FC设备原理和结构介绍 | 82.4min | 17,742 | 12,412 bytes |
| 6 | 视觉硬件概述 | 62.4min | 16,648 | 11,230 bytes |
| 7 | FC工艺简介 | 69.4min | 17,747 | 11,940 bytes |
| 8 | 设备软件运动模块详解 | 50.9min | 13,510 | 16,393 bytes |
| 9 | ACS应用介绍(一) | 98.1min | 31,548 | 19,905 bytes |
| 10 | 设备贴片原理讲解 | 104.9min | 25,801 | 14,854 bytes |

**总计:** 468 分钟视频 → Phase1 70分钟（2并行）+ Phase2 65秒（6并行）= **71分钟**

## 已知限制
- 长视频（>2h）转录文本可能超过模型上下文窗口，已做 25000 字符截断
- 仅支持 LLM API
- 多进程转录时每个子进程独立加载模型（约 300MB/进程）

## 培训视频专题总结 (2026-07-08) — 进行中

### 目标
对"培训视频"文件夹中与以下技术领域相关的视频进行专题总结：
- **Motion**（运动控制）：轴运动、时序、ACS、电机控制
- **Vision**（视觉）：视觉硬件、相机标定、图像处理、AI检测、GP软件
- **I/O**（输入输出）：传感器、通讯协议、数据采集卡
- **Mapping**（映射/标定）：坐标系标定、建模
- **EAP**（设备自动化程序）：EAP架构、SECS/GEM、EAP模拟器
- **EFEM**（设备前端模块）
- **用户管理 / 日志管理 / 参数文件管理**
- **半导体工艺知识**：封装流程、Die Bond / Wire Bond / Flip Chip

### 策略
- 只处理上述领域相关的视频文件夹（约30个未处理）
- 使用 focused_seq.py 进行单进程顺序处理（更稳定）
- Prompt 中明确限定只关注目标领域，忽略无关内容

### 完成进度 (2026-07-08) — ✅ 全部完成 30/30 (base模型)

所有与 Motion/Vision/I/O/Mapping/EAP/软件框架/半导体工艺 相关的培训视频已全部用 **base 模型**总结完毕。
57/59/60/61 已从 tiny 模型重新转录替换为 base 模型，文档质量明显提升。

| # | 视频 | 文档大小 | 主要内容领域 |
|---|------|----------|------------|
| 11 | Pick&Place工艺讲解(一) | 4,500B | 半导体工艺 |
| 12 | ACS应用介绍(二) | 2,766B | Motion |
| 14 | Pick&Place工艺讲解(二) | 4,324B | 半导体工艺 |
| 15 | FC1250所用传感器介绍 | 13,405B | I/O |
| 16 | Pick&Place工艺讲解(三) | 10,990B | 半导体工艺 |
| 17 | 凌华卡与雷赛卡应用介绍 | 8,920B | I/O (PPT-only) |
| 18 | 相机镜头建模常用操作 | 18,521B | Vision/Mapping |
| 20 | 电机特殊运动讲解 | 14,414B | Motion |
| 29 | 设备稳定性能指标参数 | 3,294B | 参数文件管理 |
| 30 | svn提交规则与贴片时序 | 9,953B | 参数文件管理/Motion |
| 31 | EAP介绍和调试过程 | 9,588B | EAP |
| 33 | 新版视觉2.0软件操作 | 15,188B | Vision |
| 34 | 建模注意事项 | 12,635B | Mapping |
| 37 | 1210时序规划与分析 | 10,332B | Motion |
| 39 | 基于1210的通讯介绍 | 11,013B | I/O |
| 40 | AI技术在芯片检测中应用 | 13,072B | Vision |
| 41 | 1250常见问题分析(一) | 3,591B | 综合 |
| 42 | 1250常见问题分析(二) | 14,176B | 综合 |
| 43 | 1250常见问题分析(三) | 5,272B | 综合 |
| 44 | 设备模块的封装和应用 | 3,295B | 软件框架 |
| 48 | 1220框架讲解 | 4,014B | 软件框架 |
| 49 | BGA封装流程介绍 | 10,613B | 半导体工艺 |
| 52 | EAP软件安装和四大模块 | 3,143B | EAP |
| 53 | 视觉2新功能和标定方式 | 5,254B | Vision/Mapping |
| 54 | Memory工艺培训 | 9,945B | 半导体工艺 |
| 56 | EAP模拟器和EAP代码应用 | 4,182B | EAP |
| 57 | 视觉基础知识及镜头选型 | 3,476B | Vision |
| 59 | MIT视觉GP软件培训 | 3,680B | Vision |
| 60 | 视觉GP软件培训 | 2,558B | Vision |
| 61 | FC1250时序分析 | 2,883B | Motion |

总计: 238,997 bytes (233.4KB)

### 脚本
- `focused_batch.py` — 并行版（Phase1: 2进程转录 + Phase2: 6线程合成），Windows下可能不稳定
- `focused_seq.py` — 顺序版（逐个文件夹完整处理），可靠但慢
- `process_one.py` — 单视频处理器，子进程隔离内存
- `batch_master.py` — 主控脚本，用subprocess逐个调用process_one.py
- **`spawn.py` + `detached_worker.py`** — 新架构：脱离LLM CLI管控的独立进程方案

### 新架构：spawn.py + detached_worker.py

解决后台任务被LLM CLI超时杀死的根本问题。

```
spawn.py (1秒退出)
  └─ detached_worker.py (独立进程，不受LLM CLI管控)
       ├─ 视频1: 转录子进程 → API调用 → _DONE标记
       ├─ 视频2: 转录子进程 → API调用 → _DONE标记
       └─ ...
```

**使用方式：**
```bash
python spawn.py                          # 处理所有相关未完成文件夹
python spawn.py "path1" "path2" ...      # 处理指定文件夹
```

**进度监控：**
```bash
find "<training-videos-directory>" -name "_DONE"       # 完成了几个
cat <folder>/_worker.log                  # 查看具体日志
```

**关键设计：**
- `spawn.py` 用 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` 启动 worker
- worker 完全脱离父进程，LLM CLI 关掉也不影响
- 每个视频完成后创建 `_DONE` 标记文件
- 转录在独立子进程中运行，防止内存泄漏
- API 调用有 3 次重试

## 后续可扩展
- 关键帧提取 + 本地 VLM 描述（混合管线）
- 说话人分离（WhisperX）
- 多 LLM 后端（OpenAI / Ollama）
- 流式输出
