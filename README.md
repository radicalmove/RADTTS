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

## Distributed workers (offload TTS/ASR)

Use the server as control plane and run heavy synthesis on stronger worker machines.

Worker flow:
1. In web UI, generate worker invite (`Workers` panel).
2. On worker machine, install deps and run one-time setup:
   ```bash
   radtts-worker-install --server-url http://<server-host>:8080 --invite-token <token>
   ```
   This registers the worker and installs background auto-start for your OS:
   - Linux: `systemd --user` service
   - macOS: `LaunchAgent`
   - Windows: Scheduled Task (runs at user logon)
3. Submit synthesis jobs in `Worker execution` mode from the UI.

Windows colleague quick setup (single command, mostly automated):
```powershell
py -m pip install --upgrade pip; py -m pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple "git+https://github.com/radicalmove/RADTTS.git#egg=radtts[asr,tts]"; py -m radtts.worker_setup --server-url https://<server-host> --invite-token <token> --platform windows
```

No-terminal installer downloads (run once, then background autostart):
- Windows: `GET /workers/bootstrap/windows.cmd?invite_token=...` (download + run)
- macOS: `GET /workers/bootstrap/macos.command?invite_token=...` (download + run)

The invite API now returns OS-specific setup links and commands:
- `install_command_windows`
- `install_command_macos`
- `install_command_linux`
- `windows_installer_url`
- `macos_installer_url`

Manual worker start (if needed):
```bash
radtts-worker --server-url http://<server-host>:8080
```

Key worker endpoints:
- `POST /workers/invite`
- `POST /workers/register`
- `POST /workers/pull`
- `POST /workers/jobs/{id}/complete`
- `POST /workers/jobs/{id}/fail`
- `POST /synthesize/worker`

## Notes
- Voice cloning requires explicit authorization in your workflow.
- Qwen voice cloning is restricted to Base models in this app.
- Processing is local-first by design.
- TTS runtime defaults:
  - Apple Silicon uses `mps` with `float32` when available.
  - CUDA GPUs use `cuda:0` with `float16` when available.
  - Override with `RADTTS_TTS_DEVICE` and `RADTTS_TTS_DTYPE` if needed.
 - Audio cleanup defaults:
   - reference audio is lightly cleaned before cloning with `RADTTS_REFERENCE_AUDIO_FILTER`
   - final output is lightly de-essed with `RADTTS_OUTPUT_AUDIO_FILTER`
   - defaults:
     - `RADTTS_REFERENCE_AUDIO_FILTER=highpass=f=80,agate=threshold=0.015:ratio=1.15:attack=8:release=180:range=0.6:knee=3,equalizer=f=6200:t=q:w=1.2:g=-1.0`
     - `RADTTS_OUTPUT_AUDIO_FILTER=highpass=f=60,equalizer=f=6400:t=q:w=1.2:g=-1.2,deesser=i=0.08:m=0.35:f=0.5:s=o`

## Linux deployment
- Deployment guide: [`docs/MAC_MINI_LINUX_DEPLOYMENT.md`](docs/MAC_MINI_LINUX_DEPLOYMENT.md)
- systemd templates: `deploy/systemd/`
- nginx template: `deploy/nginx/radtts.conf`
