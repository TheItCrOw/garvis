# Garvis Backend

## Prerequisite

Since Garvis use services provided by the Google Cloud, you need to authenticate ourself to it and set a billing project. [Install the `gcloud`](https://docs.cloud.google.com/sdk/docs/install-sdk?hl=de) CLI in your system.

### Login

```
gcloud auth application-default login
```

a window will prompt you to login. Afterwards, set a billing project (if you have no project yet, create one in the [Google Cloud Console Web interface](https://console.cloud.google.com/welcome?hl=de&project=kaggle-medgemma-hackathon-2026))

```
gcloud auth application-default set-quota-project [YOUR_PROJECT_NAME]
```

You have now created a `application_default_credentials.json` file which is stored, by default, under `%APPDATA%\gcloud\application_default_credentials.json` for Windows and `~/.config/gcloud/application_default_credentials.json` for Linux.

### Environment Variables

Create a `.env` file in this folder by copying the content from `.env.example` and filling in your personal **api keys**.

---

## Setup

Only proceed if you've finished the prerequisites. We use Python 3.12. Clone the repo and navigate into the garvis-backend folder with your shell (current folder). On Windows, do:

```
cd garvis-backend
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[dev]"
```

# once you've done this

```
uv run main.py
#or
python main.py
```

## MedGemma Models & Ollama

If you want to utilize the domain experts of Google's MedGemma models, you need to [install ollama](https://ollama.com/download). Then, pull and run the following models:

```
ollama pull MedAIBase/MedGemma1.5:4b
ollama run MedAIBase/MedGemma1.5:4b

ollama pull thiagomoraes/medgemma-1.5-4b-it:Q4_K_M
ollama run thiagomoraes/medgemma-1.5-4b-it:Q4_K_M
```

## Docker

If you want to run the Garvis backend via docker, do:

```
docker build -t garvis-backend .
```

Then start the container and pass in the relevant `gcloud` parameters which you setup earlier.

### Windows

```
docker run -p 8000:8000 ^
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/adc.json ^
  -e GOOGLE_CLOUD_QUOTA_PROJECT=YOUR_PROJECT_NAME ^
  -v %APPDATA%\gcloud\application_default_credentials.json:/secrets/adc.json:ro ^
  garvis-backend
```

### Linux

```
docker run -p 8000:8000 \
 -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/adc.json \
 -e GOOGLE_CLOUD_QUOTA_PROJECT=YOUR_PROJECT_NAME \
 -v ~/.config/gcloud/application_default_credentials.json:/secrets/adc.json:ro \
 garvis-backend
```

# Live

To see current backend documentation

```
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

## Development

To run debug using visual-studio code

hit CTRL+SHIFT+D and configure this from within your IDE

```
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI (uvicorn module)",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.app:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
      "cwd": "${workspaceFolder}/garvis-backend",
      "console": "integratedTerminal",
      "justMyCode": false,
      "subProcess": true
    }
  ]
}
```
