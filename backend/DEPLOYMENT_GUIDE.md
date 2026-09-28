# Cloud Run Deployment Guide

This guide is for the person managing the Google Cloud Platform (GCP) side of the project.
**Project ID:** `teachable-voice-automation`

The codebase is completely ready. Your job is to deploy it to Google Cloud Run so the Android app can talk to it from anywhere.

## Prerequisites (Do this in Google Cloud Console)
1. Ensure billing is enabled for `teachable-voice-automation`.
2. Enable these APIs:
   - **Cloud Run API**
   - **Cloud Build API**
   - **Secret Manager API**

## Step 1: Store the Gemini API Key
Never put the API key in the code. We use GCP Secret Manager.
1. Go to **Secret Manager** in GCP Console.
2. Click **Create Secret**.
3. Name it: `GEMINI_API_KEY`
4. Paste the API key into the "Secret value" field.
5. Save it.

## Step 2: Deploy to Cloud Run
Open the **Google Cloud Shell** (the terminal icon `>_` in the top right of the GCP console) and run these exact commands:

```bash
# 1. Clone this repository (replace with your actual GitHub URL once pushed)
git clone <YOUR_GITHUB_REPO_URL>
cd <REPO_FOLDER>/backend

# 2. Deploy directly to Cloud Run
gcloud run deploy teachable-voice-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

*Note: If it asks to enable any APIs during the deploy command, press `y` to accept.*

## Step 3: Get the Live URL
Once the command finishes, it will print a Service URL that looks like:
`https://teachable-voice-backend-xxxxxxxx-uc.a.run.app`

Copy this URL and give it to the Android developer! All API endpoints (e.g., `/v1/teach`, `/v1/replay/plan`) will be available there.

## Note about Storage
Right now, the backend saves flows as JSON files in a `flows/` directory. Cloud Run is **stateless**, meaning if the container scales down, those files might be lost. 
This is perfectly fine for the hackathon demo/testing. For production later, the `storage.py` file should be updated to save to Google Cloud Firestore instead.
