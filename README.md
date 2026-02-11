# Garvis

## Quickstart

### Google Cloud

Since Garvis uses services provided by the Google Cloud, you need to authenticate ourself to it and set a billing project. [Install the `gcloud`](https://docs.cloud.google.com/sdk/docs/install-sdk?hl=de) CLI in your system.

### Login

```
gcloud auth application-default login
```

a window will prompt you to login. Afterwards, set a billing project (if you have no project yet, create one in the [Google Cloud Console Web interface](https://console.cloud.google.com/welcome?hl=de&project=kaggle-medgemma-hackathon-2026))

```
gcloud auth application-default set-quota-project [YOUR_PROJECT_NAME]
```

You have now created a `application_default_credentials.json` file which is stored, by default, under `%APPDATA%\gcloud\application_default_credentials.json` for Windows and `~/.config/gcloud/application_default_credentials.json` for Linux.

### API Keys

Navigate to the `garvis-backend` project, create an `.env` file in there by copying the content of `.env-example` and filling in your personal API keys. This env file will be copied into the docker image.

### Final Parameters

Finally, create a `.env` file in this root folder to set the following parameters:

```
GOOGLE_CLOUD_QUOTA_PROJECT=[YOUR_BILLING_PROJECT]
ADC_PATH="/path/to/your/application_default_credentials.json"

VITE_BACKEND_WS_URL=ws://localhost:8000/ws/audio
VITE_API_BASE=http://localhost:8000/api
```

### Docker

Once you've setup your cloud, api keys and env parameters, run the docker compose command:

```
 docker-compose up --build
```
