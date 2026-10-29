#!/usr/bin/env bash
# ==============================================================================
# OmniBlog: Deploy Agent to Google Cloud Vertex AI Agent Engine
# ==============================================================================
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-${GCP_PROJECT:-msk-fde}}"
REGION="${GOOGLE_CLOUD_LOCATION:-${GCP_REGION:-us-central1}}"
DISPLAY_NAME="omniblog_editorial_engine"

echo "=== Deploying OmniBlog to Vertex AI Agent Engine ==="
echo "Project ID:   ${PROJECT_ID}"
echo "Region:       ${REGION}"
echo "Display Name: ${DISPLAY_NAME}"

# Deploy using canonical Google ADK deployment CLI
adk deploy agent_engine \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --display_name="${DISPLAY_NAME}" \
    --description="Autonomous Multi-Agent Enterprise Blog & Content Publication Engine" \
    --otel_to_cloud \
    .

echo "=== Vertex AI Agent Engine Deployment Initiated Successfully ==="
