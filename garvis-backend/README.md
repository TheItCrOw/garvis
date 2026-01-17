# Garvis Backend

## Setup

We use Python 3.12, navigate into the garvis-backend folder with your shell (current folder). On Windows, do:

```
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[dev]"
```

once you've done this, you can run the backend server:

```
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

To run potential tests:

```
pytest
```
