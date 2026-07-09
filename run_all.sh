#!/bin/bash
# Process remaining training videos one at a time
BASE="<training-videos-directory>"
SCRIPT="<project-root>/video-summarizer/process_one.py"

TARGETS=(
    "34.建模注意事项-员工H"
    "37.1210时序规划与分析-员工J"
    "39.基于1210的通讯介绍-员工K"
    "40.AI技术在芯片检测中应用-员工B"
    "41.1250设备常见问题及其分析方法（一）-员工A"
    "42.1250设备常见问题及其分析方法（二）-员工A"
    "43.1250设备常见问题及其分析方法（三）-员工A"
    "44.设备模块的封装和应用-员工B"
    "48.1220框架讲解-员工C"
    "49.BGA封装流程介绍-员工D"
    "52.EAP的软件安装过程和四大模块的应用-员工E"
    "53.视觉2新功能介绍和标定方式-员工B"
    "54.Memory工艺培训"
    "56.EAP模拟器和EAP代码的应用-员工E"
    "57. 视觉基础知识 及 镜头相机选型 - 员工F"
    "59.MIT视觉GP软件培训-Colleague G"
    "60.视觉GP软件培训-员工H"
    "61.FC1250时序分析-员工I"
)

TOTAL=${#TARGETS[@]}
COUNT=0
for t in "${TARGETS[@]}"; do
    COUNT=$((COUNT + 1))
    echo "" && echo "========================================" && echo "[$COUNT/$TOTAL] $t" && echo "========================================"
    python "$SCRIPT" "${BASE}/${t}"
    echo "Exit code: $?" && echo "$(date): $t -> exit $?" >> "$(dirname "$SCRIPT")/run_all.log"
done
echo "ALL DONE"
