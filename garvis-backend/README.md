# Garvis Backend

## Setup

We use Python 3.12, navigate into the garvis-backend folder with your shell (current folder). On Windows, do:

```
cd garvis-backend
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[dev]"
```

once you've done this

```
[FOR BACKEND]
uv run main.py
#or 
python main.py
```

To see current backend documentation

```
[BACKEND]
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```


To run potential tests:

```
pytest
```
