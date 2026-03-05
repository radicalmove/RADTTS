# RADTTS

Local-first voice synthesis pipeline for course production.

## Features
- Project and asset scaffolding
- ASR transcription (`txt`, `srt`, `segments.json`)
- Transcript-verified clip extraction
- Qwen3-TTS Base-model voice cloning
- Sentence-chunk synthesis with variable pauses
- Captions export (`txt`, `srt`, `vtt`)
- Metadata manifests for reproducibility
- Stage progress with retries/timeouts and heartbeat logs
- CLI + optional FastAPI service

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Linux CPU deployment (recommended for your Ubuntu server):

```bash
pip install -r requirements-linux-cpu.txt
```

If you only need CLI scaffolding/tests without heavy models and web runtime:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

## CLI quick start

```bash
radtts create-project --project-id crju150-m9 --course CRJU150 --module M9 --lesson L1

radtts transcribe \
  --project-id crju150-m9 \
  --audio-path /abs/path/lecture.mp3 \
  --name lecture1

radtts clip \
  --project-id crju150-m9 \
  --audio-path /abs/path/lecture.mp3 \
  --segments-json projects/crju150-m9/transcripts/lecture1.segments.json \
  --output-name bridge1 \
  --start-phrase "In this section" \
  --end-phrase "Let us move on"

radtts synthesize \
  --project-id crju150-m9 \
  --text-file /abs/path/script.txt \
  --reference-audio /abs/path/reference.mp3 \
  --mode quality \
  --chunk-mode sentence \
  --output-name intro_v2

radtts captions \
  --project-id crju150-m9 \
  --audio-path projects/crju150-m9/assets/generated_audio/intro_v2.mp3 \
  --name intro_v2
```

## API

```bash
export RADTTS_HOST=127.0.0.1
export RADTTS_PORT=8080
radtts-api
```

Key endpoints:
- `POST /projects`
- `POST /transcribe`
- `POST /clip`
- `POST /synthesize`
- `POST /captions`
- `GET /jobs/{id}`
- `POST /jobs/{id}/cancel`

Web UI:
- `GET /` (RADTTS Studio dashboard)

Shared login bridge (optional):
- `GET /auth/bridge?token=...` (accept PsyChek signed token)
- `GET /auth/logout`

Bridge/auth env vars:
- `RADTTS_AUTH_REQUIRED=true|false` (default `false`)
- `RADTTS_SESSION_SECRET=...`
- `RADTTS_BRIDGE_SECRET=...` (must match PsyChek `APP_BRIDGE_SECRET`)
- `PSYCHEK_LOGIN_URL=http://.../login`

## Notes
- Voice cloning requires explicit authorization in your workflow.
- Qwen voice cloning is restricted to Base models in this app.
- Processing is local-first by design.

## Linux deployment
- Deployment guide: [`docs/MAC_MINI_LINUX_DEPLOYMENT.md`](docs/MAC_MINI_LINUX_DEPLOYMENT.md)
- systemd templates: `deploy/systemd/`
- nginx template: `deploy/nginx/radtts.conf`
