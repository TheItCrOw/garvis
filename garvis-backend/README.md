# Garvis Backend

## Setup

We use Python 3.12, navigate into the garvis-backend folder with your shell (current folder). On Windows, do:

```
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[dev]"
```

once you've done this

```
uv run main.py
#or 
python run main.py
```

To see current endponts

```
http://127.0.0.1:8000/docs
```


To run potential tests:

```
pytest
```
