#!/bin/bash

# ----------------------------
# Configuration
# ----------------------------
PROJECT_ID="morning-weather-1"
REGION="us-central1"
FUNCTION_NAME="demo_notification"
SCHEDULER_JOB_NAME="demo_scheduler"
SCHEDULE="30 5 * * 1-5"                 # 5:30 AM Mon-Fri
TIME_ZONE="America/Chicago"
HTTP_METHOD="GET"
SERVICE_ACCOUNT="cloud-scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# ----------------------------
# Get the Cloud Run URL behind the Gen 2 Function
# ----------------------------
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
  --region="$REGION" \
  --gen2 \
  --format="value(serviceConfig.uri)")

if [ -z "$FUNCTION_URL" ]; then
  echo "❌ Failed to retrieve function URL. Is the function name correct?"
  exit 1
fi

echo "✅ Using Function URL: $FUNCTION_URL"

# ----------------------------
# Create or Update Cloud Scheduler Job
# ----------------------------
if gcloud scheduler jobs describe "$SCHEDULER_JOB_NAME" --location="$REGION" >/dev/null 2>&1; then
  echo "🔄 Updating existing Cloud Scheduler job: $SCHEDULER_JOB_NAME"
  gcloud scheduler jobs update http "$SCHEDULER_JOB_NAME" \
    --location="$REGION" \
    --uri="$FUNCTION_URL" \
    --http-method="$HTTP_METHOD" \
    --oidc-service-account-email="$SERVICE_ACCOUNT" \
    --oidc-token-audience="$FUNCTION_URL" \
    --schedule="$SCHEDULE" \
    --time-zone="$TIME_ZONE"
else
  echo "🆕 Creating new Cloud Scheduler job: $SCHEDULER_JOB_NAME"
  gcloud scheduler jobs create http "$SCHEDULER_JOB_NAME" \
    --location="$REGION" \
    --uri="$FUNCTION_URL" \
    --http-method="$HTTP_METHOD" \
    --oidc-service-account-email="$SERVICE_ACCOUNT" \
    --oidc-token-audience="$FUNCTION_URL" \
    --schedule="$SCHEDULE" \
    --time-zone="$TIME_ZONE"
fi
