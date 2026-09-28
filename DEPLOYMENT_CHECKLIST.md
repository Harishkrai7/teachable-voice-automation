# Deployment Checklist

**DO NOT EXECUTE TODAY. THIS IS FOR TOMORROW.**

## 1. Prerequisites
- [ ] Ensure Google Cloud SDK (`gcloud`) is installed.
- [ ] Ensure Docker is installed and running.

## 2. Google Cloud Setup
- [ ] Authenticate with `gcloud auth login`.
- [ ] Set your Google Cloud Project ID: `gcloud config set project [YOUR_PROJECT_ID]`.
- [ ] Enable required APIs:
  ```bash
  gcloud services enable run.googleapis.com
  gcloud services enable artifactregistry.googleapis.com
  gcloud services enable secretmanager.googleapis.com
  ```

## 3. Secret Management
- [ ] Create a Secret for the Gemini API Key. Do NOT commit the key anywhere.
  ```bash
  gcloud secrets create gemini-api-key --replication-policy="automatic"
  echo -n "[REAL_API_KEY]" | gcloud secrets versions add gemini-api-key --data-file=-
  ```

## 4. Docker Build & Push
- [ ] Verify the `Dockerfile` inside the `backend/` directory is correct.
- [ ] Build the Docker image locally to ensure it compiles without errors:
  ```bash
  docker build -t teachable-voice-backend:test .
  ```
- [ ] Tag and push the image to Google Artifact Registry:
  ```bash
  docker tag teachable-voice-backend:test [REGION]-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/teachable-voice-backend:latest
  docker push [REGION]-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/teachable-voice-backend:latest
  ```

## 5. Cloud Run Deployment
- [ ] Deploy the image to Cloud Run, attaching the Secret Manager key:
  ```bash
  gcloud run deploy teachable-voice-backend \
      --image [REGION]-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/teachable-voice-backend:latest \
      --platform managed \
      --region [REGION] \
      --allow-unauthenticated \
      --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
  ```
- [ ] Obtain the HTTPS URL returned by Cloud Run (e.g., `https://teachable-voice-backend-xxx.run.app`).

## 6. Android Configuration Update
- [ ] Open `app/build.gradle.kts` in the Android project.
- [ ] Update the Release `BASE_URL` with the newly obtained Cloud Run HTTPS URL:
  ```kotlin
  buildConfigField("String", "BASE_URL", "\"https://teachable-voice-backend-xxx.run.app/\"")
  ```
- [ ] Sync Gradle.

## 7. End-to-End Test
- [ ] Run the Android app in Release mode (or change the Debug `BASE_URL`).
- [ ] Verify that the app successfully communicates with the Cloud Run instance.
- [ ] Test the full pipeline: Voice Request -> Cloud Run -> Intent Extraction -> Flow Matching -> Replay Engine.
