# Garvis Backend

## Prerequisite
https://docs.cloud.google.com/sdk/docs/install-sdk
1. we need to setup this on the local machine as we are utilizing Google STT and TSS

## Setup

We use Python 3.12, navigate into the garvis-backend folder with your shell (current folder). On Windows, do:

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

To see current backend documentation

```
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

To run potential tests:

```
pytest
```


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

We need to pull these ollama models

```
ollama pull MedAIBase/MedGemma1.5:4b
ollama run MedAIBase/MedGemma1.5:4b

ollama pull thiagomoraes/medgemma-1.5-4b-it:Q4_K_M
ollama run thiagomoraes/medgemma-1.5-4b-it:Q4_K_M
```