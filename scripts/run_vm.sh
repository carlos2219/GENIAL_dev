#!/usr/bin/env bash
# scripts/run_vm.sh — Lanza el pipeline GENIAL en background (GCP Compute Engine)
#
# Uso:
#   ./scripts/run_vm.sh [opciones de main.py]
#
# Ejemplos:
#   ./scripts/run_vm.sh --all-universities --resume
#   ./scripts/run_vm.sh --phase3-only --skip-ai
#   ./scripts/run_vm.sh --max-universities 10 --verbose
#
# Requiere: python en PATH, .env cargado o variables de entorno exportadas

set -euo pipefail

LOG_FILE="logs/nohup.out"
PID_FILE="logs/pipeline.pid"

mkdir -p logs

echo "Iniciando pipeline GENIAL..."
echo "Argumentos: $*"

nohup python main.py "$@" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Pipeline iniciado (PID $(cat "$PID_FILE"))"
echo "Ver log en tiempo real: tail -f $LOG_FILE"
echo "Detener pipeline: kill \$(cat $PID_FILE)"
