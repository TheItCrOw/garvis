# Garvis PWA Client

## Prerequisite

Setup a .env file in the root folder of the `garvis-client` (this folder):

```
VITE_BACKEND_WS_URL=ws://localhost:8000/ws/audio
VITE_API_BASE=http://localhost:8000/api
```

If you plan to run or already ran the `garvis-backend` in a non-standard localhost, then adjust these appropriately.

## Setup

You need [NodeJS and npm installed](https://nodejs.org/en/download) (v24 would be best). Then, install the modules once and run it:

```
npm install
npm run dev
```

## Docker

If you want to run the client via Docker, first build:

```
docker build -t garvis-client .
```

Then run the container with the right parameters:

### Windows

```
docker run -p 5173:5173 ^
  -e VITE_BACKEND_WS_URL=ws://localhost:8000/ws/audio ^
  -e VITE_API_BASE=http://localhost:8000/api ^
  garvis-client
```

### Linux

```
docker run -p 5173:5173 \
  -e VITE_BACKEND_WS_URL=ws://localhost:8000/ws/audio \
  -e VITE_API_BASE=http://localhost:8000/api \
  garvis-client
```
