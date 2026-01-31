# Garvis PWA Client

## Setup

You need NodeJS and npm installed. Then, install the modules once and run it:

You may need to update your nodejs
https://nodejs.org/en/download
then you may need to use a specific version nvm use 24
```
npm install
npm run dev
```

If you haven't, create a `.env` file and enter the following parameters:

```
VITE_BACKEND_WS_URL=ws://localhost:8000/ws/audio
VITE_API_BASE=http://localhost:8000/api
```

If you run this client in a non-standard localhost, then adjust them appropriately.
