#!/bin/bash
# 演示脚本 - 用 QuickTime 录制终端运行此脚本
# 使用方法: 
#   1. 打开 QuickTime Player -> 文件 -> 新建屏幕录制
#   2. 打开终端，cd 到大作业目录
#   3. 运行: bash demo_script.sh
#   4. 录制完成后停止 QuickTime

DEMO_INPUTS=(
# 场景1: 五子棋 - 五子连珠获胜
"1" "1" "" "D4" "D1" "E4" "E1" "F4" "F1" "G4" "G1" "H4"
# 场景2: 围棋 - 提子/悔棋/存档/pass
"1" "2" "9" "E5" "E6" "D5" "F5" "E4" "D6" "F4" "undo" "save demo" "list" "help" "pass" "pass"
# 场景3: 加载存档 & 投子认负
"1" "2" "9" "load demo" "resign"
# 退出
"3"
)

# Build input string
INPUT=""
for item in "${DEMO_INPUTS[@]}"; do
    INPUT="${INPUT}${item}"$'\n'
done

echo "=============================================="
echo "  棋类对战平台 - 功能演示"
echo "  作者: liugangjian"
echo "=============================================="
echo ""
sleep 1

echo "$INPUT" | python3 game_platform.py
