#!/usr/bin/env bash
set -Eeuo pipefail
export EXPECTED_REVISION=147ab55c38939f3754ced42576c1b82c0b2d60f0
export RUN_ROOT=/home/wangly/hdd-store/outputs/sirui/published/open5m-depth-match/20260908T100452Z-full-history-i01-147ab55
export SCRATCH_ROOT=/home/wangly/hdd-store/scratch/sirui/open5m-depth-match/20260908T100452Z-full-history-i01-147ab55
export HOT_ROOT=/tmp/sirui-wangly/open5m-depth-match/20260908T100452Z-full-history-i01-147ab55
export CONFIG='/home/wangly/src/sirui-quant-research/因子/algobench/configs/open5m_depth_match_2024_2026q2_v1.yaml'
export MODE=full-history
export GATE=/home/wangly/hdd-store/outputs/sirui/published/open5m-depth-match/20260908T095616Z-single-day-i05-147ab55/PERFORMANCE_GATE.json
export APPROVAL_RECORD=/tmp/sirui-wangly/open5m-depth-match/approvals/20260908T100452Z-full-history-i01-147ab55/approval_record.json
export PREVIOUS_RUN=''
cd /home/wangly/src/sirui-quant-research
exec bash scripts/run_open5m_depth_match_server_task.sh
