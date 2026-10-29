#!/usr/bin/env bash
# ==============================================================================
# OmniBlog: Deploy Agent to Google Cloud Run
# ==============================================================================
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-${GCP_PROJECT:-msk-fde}}"
REGION="${GOOGLE_CLOUD_LOCATION:-${GCP_REGION:-us-central1}}"
SERVICE_NAME="omniblog-agent"
IMAGE_TAG="us-central1-docker.pkg.dev/${PROJECT_ID}/omniblog/${SERVICE_NAME}:latest"

echo "=== Deploying OmniBlog to Google Cloud Run ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region:     ${REGION}"
echo "Service:    ${SERVICE_NAME}"
echo "Image:      ${IMAGE_TAG}"

# Ensure Artifact Registry repository exists
gcloud artifacts repositories create omniblog \
    --repository-format=docker \
    --location="${REGION}" \
    --project="${PROJECT_ID}" 2>/dev/null || true

# Build and push container image using Cloud Build
echo "Submitting build to Google Cloud Build..."
gcloud builds submit --tag "${IMAGE_TAG}" --project="${PROJECT_ID}" .

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_TAG}" \
    --platform=managed \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=1 \
    --set-env-vars="GOOGLE_GENAI_USE_ENTERPRISE=1,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},ENABLE_CLOUD_TRACE=true"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform=managed --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')
echo "=== Deployment Succeeded! ==="
echo "Service URL: ${SERVICE_URL}"
echo "Swagger Docs: ${SERVICE_URL}/docs"
