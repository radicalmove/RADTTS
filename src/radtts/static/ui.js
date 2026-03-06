const projectGatewayNode = document.getElementById("project-gateway");
const workspaceNode = document.getElementById("workspace");
const switchProjectBtn = document.getElementById("switch-project-btn");
const shareProjectBtn = document.getElementById("share-project-btn");
const activeProjectChip = document.getElementById("active-project-chip");
const activeProjectLabelNode = document.getElementById("active-project-label");

const existingProjectSelectNode = document.getElementById("existing-project-select");
const refreshProjectsBtn = document.getElementById("refresh-projects-btn");
const projectGatewayStatusNode = document.getElementById("project-gateway-status");

const audioDropzoneNode = document.getElementById("audio-dropzone");
const audioFileInputNode = document.getElementById("reference-audio-file");
const audioDropzoneTitleNode = document.getElementById("audio-dropzone-title");
const audioFileNameNode = document.getElementById("audio-file-name");
const savedSampleSelectNode = document.getElementById("saved-sample-select");
const refreshSamplesBtn = document.getElementById("refresh-samples-btn");
const savedSampleStatusNode = document.getElementById("saved-sample-status");
const recordAudioBtn = document.getElementById("record-audio-btn");
const recordStatusNode = document.getElementById("record-status");
const recordPreviewNode = document.getElementById("record-preview");

const scriptTextNode = document.getElementById("script-text");
const scriptFileInputNode = document.getElementById("script-file");
const scriptFileStatusNode = document.getElementById("script-file-status");

const qualityNode = document.getElementById("quality-level");
const outputFormatNode = document.getElementById("output-format");
const umsToggleNode = document.getElementById("ums-toggle");
const ahsToggleNode = document.getElementById("ahs-toggle");
const transcriptToggleNode = document.getElementById("transcript-toggle");
const gapSliderNode = document.getElementById("gap-slider");
const gapValueNode = document.getElementById("gap-value");

const generateBtn = document.getElementById("generate-btn");
const cancelBtn = document.getElementById("cancel-btn");
const generateStatusNode = document.getElementById("generate-status");
const progressWrapNode = document.getElementById("progress-wrap");
const progressStageNode = document.getElementById("progress-stage");
const progressEtaNode = document.getElementById("progress-eta");
const progressPercentNode = document.getElementById("progress-percent");
const progressFillNode = document.getElementById("progress-fill");
const progressDetailNode = document.getElementById("progress-detail");

const outputListNode = document.getElementById("output-list");

const stageLabels = {
  queued: "Queued",
  queued_remote: "Waiting for worker device",
  worker_running: "Processing on worker device",
  fallback_local: "Worker unavailable, running on server",
  model_load: "Loading voice model",
  generation: "Generating speech",
  stitching: "Finalizing audio",
  captioning: "Creating transcript",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const stageProgressFloors = {
  queued: 0,
  queued_remote: 0,
  worker_running: 18,
  fallback_local: 8,
  model_load: 5,
  generation: 35,
  stitching: 72,
  captioning: 85,
  completed: 100,
  failed: 100,
  cancelled: 0,
};

const stageProgressCaps = {
  queued: 8,
  queued_remote: 18,
  worker_running: 82,
  fallback_local: 34,
  model_load: 34,
  generation: 79,
  stitching: 84,
  captioning: 98,
  completed: 100,
  failed: 100,
  cancelled: 0,
};

const stageExpectedSeconds = {
  queued: 6,
  queued_remote: 120,
  worker_running: 300,
  fallback_local: 40,
  model_load: 60,
  generation: 300,
  stitching: 45,
  captioning: 120,
};

const state = {
  activeProjectRef: null,
  activeProjectLabel: null,
  canManageActiveProject: false,
  selectedAudioFile: null,
  selectedAudioHash: null,
  activeJobId: null,
  pollTimer: null,
  progressAnimator: null,
  currentStatus: "idle",
  currentStage: "queued",
  jobStartedAtMs: null,
  stageStartedAtMs: null,
  actualProgress: 0,
  displayProgress: 0,
  latestDetail: "Preparing generation...",
  mediaRecorder: null,
  recordingStream: null,
  recordingChunks: [],
  recordingPreviewUrl: null,
  referenceSamples: [],
  expectedRemoteWorker: false,
  computeMode: "idle",
  lastAnnouncedComputeMode: "idle",
  etaSeconds: null,
  etaUpdatedAtMs: null,
};

function cleanOptional(value) {
  const trimmed = (value ?? "").trim();
  return trimmed.length ? trimmed : null;
}

function setGatewayStatus(message, isError = false) {
  if (!projectGatewayStatusNode) return;
  projectGatewayStatusNode.textContent = message || "";
  projectGatewayStatusNode.style.color = isError ? "#a73527" : "#555";
}

function setGenerateStatus(message, isError = false) {
  if (!generateStatusNode) return;
  generateStatusNode.textContent = message || "";
  generateStatusNode.style.color = isError ? "#a73527" : "#444";
}

function setRecordStatus(message, isError = false) {
  if (!recordStatusNode) return;
  recordStatusNode.textContent = message || "";
  recordStatusNode.style.color = isError ? "#a73527" : "#555";
}

function setSavedSampleStatus(message, isError = false) {
  if (!savedSampleStatusNode) return;
  savedSampleStatusNode.textContent = message || "";
  savedSampleStatusNode.style.color = isError ? "#a73527" : "#555";
}

function setWorkspaceVisible(visible) {
  if (projectGatewayNode) projectGatewayNode.hidden = visible;
  if (workspaceNode) workspaceNode.classList.toggle("workspace-hidden", !visible);
  if (switchProjectBtn) switchProjectBtn.hidden = !visible;
  if (activeProjectChip) activeProjectChip.hidden = !visible;
}

function setGenerateEnabled(enabled) {
  if (generateBtn) generateBtn.disabled = !enabled;
}

function setCancelVisible(visible) {
  if (!cancelBtn) return;
  cancelBtn.hidden = !visible;
}

function setCancelEnabled(enabled) {
  if (!cancelBtn) return;
  cancelBtn.disabled = !enabled;
}

function updateRecordButtonState(isRecording) {
  if (!recordAudioBtn) return;
  recordAudioBtn.classList.toggle("is-recording", isRecording);
  recordAudioBtn.textContent = isRecording ? "Stop recording" : "Record audio";
}

function stopProgressAnimator() {
  if (state.progressAnimator) {
    clearInterval(state.progressAnimator);
    state.progressAnimator = null;
  }
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function clearJobTracking() {
  stopPolling();
  stopProgressAnimator();
  state.activeJobId = null;
  state.currentStatus = "idle";
}

function resetProgressUi() {
  state.currentStage = "queued";
  state.actualProgress = 0;
  state.displayProgress = 0;
  state.jobStartedAtMs = null;
  state.stageStartedAtMs = null;
  state.latestDetail = "Preparing generation...";
  state.expectedRemoteWorker = false;
  state.computeMode = "idle";
  state.lastAnnouncedComputeMode = "idle";
  state.etaSeconds = null;
  state.etaUpdatedAtMs = null;

  if (progressWrapNode) progressWrapNode.hidden = true;
  if (progressFillNode) progressFillNode.style.width = "0%";
  if (progressPercentNode) progressPercentNode.textContent = "0%";
  if (progressStageNode) progressStageNode.textContent = "Queued";
  if (progressEtaNode) progressEtaNode.textContent = "ETA: --:--";
  if (progressDetailNode) progressDetailNode.textContent = "Preparing generation...";
}

const etaStageOrder = [
  "queued",
  "queued_remote",
  "fallback_local",
  "worker_running",
  "model_load",
  "generation",
  "stitching",
  "captioning",
  "completed",
];

function estimateEtaSeconds(progressPercent, stage) {
  if (state.currentStatus !== "running") return null;
  const nowMs = Date.now();
  const clamped = Math.max(0, Math.min(100, progressPercent));

  let progressBased = null;
  if (state.jobStartedAtMs && clamped > 1 && clamped < 100) {
    const elapsedSec = (nowMs - state.jobStartedAtMs) / 1000;
    const candidate = elapsedSec * ((100 - clamped) / clamped);
    if (Number.isFinite(candidate) && candidate >= 0) {
      progressBased = candidate;
    }
  }

  const stageExpected = stageExpectedSeconds[stage] ?? null;
  let stageBased = null;
  if (stageExpected && state.stageStartedAtMs) {
    const elapsedStageSec = Math.max(0, (nowMs - state.stageStartedAtMs) / 1000);
    let remainingStage = stageExpected - elapsedStageSec;
    if (remainingStage < 0) {
      // Keep ETA moving even if a stage runs longer than expected.
      remainingStage = Math.min(240, 20 + Math.abs(remainingStage) * 0.6);
    }

    let remainingFuture = 0;
    const idx = etaStageOrder.indexOf(stage);
    if (idx >= 0) {
      for (const nextStage of etaStageOrder.slice(idx + 1)) {
        if (nextStage === "completed") continue;
        remainingFuture += stageExpectedSeconds[nextStage] ?? 0;
      }
    }
    stageBased = Math.max(0, remainingStage + remainingFuture);
  }

  if (progressBased === null) return stageBased;
  if (stageBased === null) return progressBased;
  // Prefer the more conservative estimate to avoid overly optimistic ETAs.
  return Math.max(progressBased, stageBased * 0.75);
}

function smoothEtaDisplay(etaSeconds) {
  if (!Number.isFinite(etaSeconds) || etaSeconds <= 0) {
    state.etaSeconds = null;
    state.etaUpdatedAtMs = null;
    return null;
  }

  const nowMs = Date.now();
  if (state.etaSeconds === null || state.etaUpdatedAtMs === null) {
    state.etaSeconds = etaSeconds;
    state.etaUpdatedAtMs = nowMs;
    return state.etaSeconds;
  }

  const elapsedSec = Math.max(0, (nowMs - state.etaUpdatedAtMs) / 1000);
  const decayed = Math.max(0, state.etaSeconds - elapsedSec);
  const diff = Math.abs(etaSeconds - decayed);

  if (diff <= 4) {
    state.etaSeconds = decayed;
  } else {
    state.etaSeconds = (decayed * 0.65) + (etaSeconds * 0.35);
  }
  state.etaUpdatedAtMs = nowMs;
  return state.etaSeconds;
}

function detectComputeMode(job) {
  if (state.computeMode === "worker" || state.computeMode === "server") {
    return state.computeMode;
  }

  const stage = String(job.stage || state.currentStage || "");
  const logs = Array.isArray(job.logs) ? job.logs : [];
  const joinedLogs = logs.join("\n").toLowerCase();

  if (
    stage === "worker_running" ||
    joinedLogs.includes("worker ") && joinedLogs.includes("started processing")
  ) {
    return "worker";
  }

  if (
    stage === "fallback_local" ||
    joinedLogs.includes("switching to local server fallback")
  ) {
    return "server";
  }

  if (!state.expectedRemoteWorker) {
    return "server";
  }
  return "waiting_worker";
}

function computeModeLabel() {
  if (state.computeMode === "worker") {
    return "Compute: worker device (usually your local computer)";
  }
  if (state.computeMode === "server") {
    return "Compute: RADTTS server (Mac mini fallback)";
  }
  if (state.computeMode === "waiting_worker") {
    return "Compute: waiting for a worker device";
  }
  return "";
}

function formatIso(isoValue) {
  if (!isoValue) return "";
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return String(isoValue);
  return date.toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stripLogTimestamp(line) {
  return String(line || "").replace(/^\d{4}-\d{2}-\d{2}T[^\s]+\s+/, "").trim();
}

function friendlyStageDetail(stage) {
  const key = String(stage || "").trim().toLowerCase();
  if (key === "queued") return "Preparing your job";
  if (key === "queued_remote") return "Waiting for a worker device";
  if (key === "worker_running") return "Processing on a worker device";
  if (key === "fallback_local") return "Switching to server fallback";
  if (key === "model_load") return "Loading voice model";
  if (key === "generation") return "Generating speech";
  if (key === "stitching") return "Finalizing audio";
  if (key === "captioning") return "Creating transcript";
  if (key === "completed") return "Completed";
  if (key === "cancelled") return "Cancelled";
  if (key === "failed") return "Processing failed";
  return "Processing";
}

function detailFromLogLine(line, currentStage) {
  const cleaned = stripLogTimestamp(line);
  if (!cleaned) return "";
  const lower = cleaned.toLowerCase();

  if (lower.startsWith("heartbeat:")) {
    const stageMatch = lower.match(/stage=([a-z_]+)/);
    const stage = stageMatch?.[1] || currentStage;
    return `${friendlyStageDetail(stage)}...`;
  }

  if (lower.includes("queued for worker execution")) {
    return "Queued and waiting for a worker device.";
  }

  if (lower.includes("started processing") && lower.includes("worker")) {
    return "Worker device has started processing.";
  }

  if (lower.includes("switching to local server fallback")) {
    return "No worker responded, starting on server fallback.";
  }

  const stageMatch = lower.match(/stage=([a-z_]+)/);
  if (stageMatch?.[1]) {
    const stageText = friendlyStageDetail(stageMatch[1]);
    if (lower.includes("starting")) return `${stageText}...`;
    if (lower.includes("complete")) return `${stageText} complete.`;
    return `${stageText}.`;
  }

  return cleaned;
}

function formatEta(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "--:--";
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

async function requestJSON(url, method, payload) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : undefined,
  });

  let data;
  try {
    data = await res.json();
  } catch {
    data = { error: "Server returned non-JSON response" };
  }

  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
  }
  return data;
}

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result || "");
      const parts = value.split(",", 2);
      if (parts.length !== 2) {
        reject(new Error("Failed to read file as base64"));
        return;
      }
      resolve(parts[1]);
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

async function readScriptFile(file) {
  const lower = file.name.toLowerCase();

  if (lower.endsWith(".docx") || lower.endsWith(".doc")) {
    if (!window.mammoth || typeof window.mammoth.extractRawText !== "function") {
      throw new Error("DOCX parser not available. Use .txt or .md instead.");
    }
    const buffer = await file.arrayBuffer();
    const result = await window.mammoth.extractRawText({ arrayBuffer: buffer });
    return result.value || "";
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Failed to read text file"));
    reader.readAsText(file);
  });
}

async function refreshProjectAccessInfo() {
  if (!shareProjectBtn || !state.activeProjectRef) return;
  try {
    const data = await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/access`,
      "GET"
    );
    state.canManageActiveProject = Boolean(data.can_manage);
    shareProjectBtn.hidden = !state.canManageActiveProject;
  } catch {
    state.canManageActiveProject = false;
    shareProjectBtn.hidden = true;
  }
}

function applyActiveProject(projectRef, projectLabel = projectRef) {
  state.activeProjectRef = projectRef;
  state.activeProjectLabel = projectLabel;
  state.canManageActiveProject = false;
  state.selectedAudioHash = null;
  state.referenceSamples = [];
  clearRecordingPreview();
  setSelectedAudioFile(null);
  if (savedSampleSelectNode) savedSampleSelectNode.innerHTML = '<option value="">Loading saved samples...</option>';
  setSavedSampleStatus("Loading saved samples...");
  if (activeProjectLabelNode) activeProjectLabelNode.textContent = projectLabel;
  setWorkspaceVisible(true);
  setGenerateStatus("");
  resetProgressUi();
  clearJobTracking();
  setGenerateEnabled(true);
  setCancelVisible(false);
  void loadOutputs();
  void loadReferenceSamples();
  void refreshProjectAccessInfo();
}

function requireActiveProject() {
  if (!state.activeProjectRef) {
    throw new Error("Select or create a project first.");
  }
  return state.activeProjectRef;
}

function setSelectedAudioFile(file) {
  state.selectedAudioFile = file || null;
  state.selectedAudioHash = null;
  if (savedSampleSelectNode) {
    savedSampleSelectNode.value = "";
  }
  if (!audioFileNameNode || !audioDropzoneTitleNode) return;

  if (!state.selectedAudioFile) {
    audioDropzoneTitleNode.textContent = "Drop audio here or click to choose";
    audioFileNameNode.textContent = "No file selected.";
    return;
  }

  audioDropzoneTitleNode.textContent = "Voice sample selected";
  const mb = (state.selectedAudioFile.size / (1024 * 1024)).toFixed(2);
  audioFileNameNode.textContent = `${state.selectedAudioFile.name} (${mb} MB)`;
}

function findReferenceSampleByHash(audioHash) {
  if (!audioHash) return null;
  for (const sample of state.referenceSamples) {
    if (sample && sample.audio_hash === audioHash) {
      return sample;
    }
  }
  return null;
}

function applySavedSampleSelection(audioHash) {
  const sample = findReferenceSampleByHash(audioHash);
  if (!sample) {
    setSavedSampleStatus("Saved sample not found. Refresh and try again.", true);
    return;
  }

  state.selectedAudioFile = null;
  state.selectedAudioHash = sample.audio_hash;
  if (audioFileInputNode) {
    audioFileInputNode.value = "";
  }

  if (audioDropzoneTitleNode) {
    audioDropzoneTitleNode.textContent = "Saved sample selected";
  }
  if (audioFileNameNode) {
    const stamped = sample.updated_at ? `Saved ${formatIso(sample.updated_at)}` : "Saved in project";
    const projectHint = sample.project_id ? `, project ${sample.project_id}` : "";
    audioFileNameNode.textContent = `${sample.source_filename || "saved-sample"} (${stamped}${projectHint})`;
  }
  const ownerHint = sample.owner_label ? ` by ${sample.owner_label}` : "";
  setSavedSampleStatus(
    `Using saved sample: ${sample.source_filename || sample.audio_hash.slice(0, 8)}${ownerHint}.`
  );
}

async function loadReferenceSamples(preferredHash = null) {
  const projectId = state.activeProjectRef;
  if (!projectId || !savedSampleSelectNode) return;

  savedSampleSelectNode.innerHTML = '<option value="">Loading saved samples...</option>';
  savedSampleSelectNode.disabled = true;
  if (refreshSamplesBtn) refreshSamplesBtn.disabled = true;

  try {
    const data = await requestJSON(`/projects/${encodeURIComponent(projectId)}/reference-audio`, "GET");
    const samples = Array.isArray(data.samples) ? data.samples : [];
    state.referenceSamples = samples;

    savedSampleSelectNode.innerHTML = "";
    if (!samples.length) {
      savedSampleSelectNode.innerHTML = '<option value="">No saved samples yet</option>';
      savedSampleSelectNode.value = "";
      setSavedSampleStatus("No saved samples in this project yet.");
      return;
    }

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose saved sample";
    savedSampleSelectNode.appendChild(placeholder);

    for (const sample of samples) {
      const option = document.createElement("option");
      option.value = sample.audio_hash;
      const updated = sample.updated_at ? formatIso(sample.updated_at) : "Saved";
      const sourceTag = sample.scope === "library" ? `My library (${sample.project_id || "other project"})` : "Project";
      option.textContent = `${sample.source_filename || "sample"} - ${sourceTag} - ${updated}`;
      savedSampleSelectNode.appendChild(option);
    }

    const fallbackHash = preferredHash || state.selectedAudioHash;
    const selectedHash = findReferenceSampleByHash(fallbackHash)?.audio_hash || "";
    savedSampleSelectNode.value = selectedHash;

    if (selectedHash && !state.selectedAudioFile) {
      applySavedSampleSelection(selectedHash);
    } else {
      setSavedSampleStatus(`Loaded ${samples.length} saved sample${samples.length === 1 ? "" : "s"}.`);
    }
  } catch (err) {
    savedSampleSelectNode.innerHTML = '<option value="">Unable to load samples</option>';
    setSavedSampleStatus(`Could not load saved samples: ${String(err)}`, true);
  } finally {
    savedSampleSelectNode.disabled = false;
    if (refreshSamplesBtn) refreshSamplesBtn.disabled = false;
  }
}

async function attachAudioFileToProject(file, originLabel = "Audio") {
  try {
    const projectId = requireActiveProject();
    const audioB64 = await fileToBase64(file);
    const payload = { filename: file.name, audio_b64: audioB64 };
    const data = await requestJSON(
      `/projects/${encodeURIComponent(projectId)}/reference-audio`,
      "POST",
      payload
    );
    state.selectedAudioHash = data.audio_hash || null;
    setRecordStatus(`${originLabel} saved to project as ${data.filename}.`);
    setSavedSampleStatus(`${originLabel} saved. You can reuse it later from the saved sample list.`);
    await loadReferenceSamples(state.selectedAudioHash);
  } catch (err) {
    setRecordStatus(`${originLabel} selected, but could not be saved yet: ${String(err)}`, true);
    setSavedSampleStatus(`Saved sample refresh failed: ${String(err)}`, true);
  }
}

function clearRecordingPreview() {
  if (!recordPreviewNode) return;
  recordPreviewNode.hidden = true;
  recordPreviewNode.pause();
  recordPreviewNode.removeAttribute("src");
  recordPreviewNode.load();
  if (state.recordingPreviewUrl) {
    URL.revokeObjectURL(state.recordingPreviewUrl);
    state.recordingPreviewUrl = null;
  }
}

function stopRecordingStreamTracks() {
  if (!state.recordingStream) return;
  for (const track of state.recordingStream.getTracks()) {
    track.stop();
  }
  state.recordingStream = null;
}

function stopRecordingIfActive() {
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  } else {
    stopRecordingStreamTracks();
    updateRecordButtonState(false);
  }
}

function getRecorderMimeType() {
  if (typeof window.MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const value of candidates) {
    if (window.MediaRecorder.isTypeSupported(value)) {
      return value;
    }
  }
  return "";
}

function extensionForMimeType(mimeType) {
  const lowered = String(mimeType || "").toLowerCase();
  if (lowered.includes("ogg")) return "ogg";
  if (lowered.includes("mp4") || lowered.includes("mpeg")) return "m4a";
  if (lowered.includes("wav")) return "wav";
  return "webm";
}

async function loadProjects(preselectProjectId = null) {
  if (!existingProjectSelectNode) return;
  existingProjectSelectNode.innerHTML = '<option value="">Loading projects...</option>';

  try {
    const data = await requestJSON("/projects", "GET");
    const projects = Array.isArray(data.projects) ? data.projects : [];
    existingProjectSelectNode.innerHTML = "";

    if (!projects.length) {
      existingProjectSelectNode.innerHTML = '<option value="">No projects yet</option>';
      setGatewayStatus("No existing projects yet. Create one to continue.");
      return;
    }

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select a project";
    existingProjectSelectNode.appendChild(placeholder);

    for (const project of projects) {
      const projectRef = String(project.project_ref || project.project_id || "");
      const projectLabel = String(project.project_id || projectRef);
      const shared = Boolean(project.shared);
      const ownerLabel = String(project.owner_label || "").trim();
      const option = document.createElement("option");
      option.value = projectRef;
      option.dataset.projectLabel = projectLabel;
      const sharedSuffix = shared ? ` (shared${ownerLabel ? ` from ${ownerLabel}` : ""})` : "";
      option.textContent = `${projectLabel}${sharedSuffix}`;
      existingProjectSelectNode.appendChild(option);
    }

    if (preselectProjectId) {
      existingProjectSelectNode.value = preselectProjectId;
    }

    setGatewayStatus("");
  } catch (err) {
    existingProjectSelectNode.innerHTML = '<option value="">Unable to load projects</option>';
    setGatewayStatus(`Could not load projects: ${String(err)}`, true);
  }
}

function renderOutputs(outputs) {
  if (!outputListNode) return;

  if (!outputs.length) {
    outputListNode.innerHTML = '<li class="output-item">No generated files in this project yet.</li>';
    return;
  }

  const rows = outputs.map((item) => {
    const actions = [];
    if (item.audio_download_url) {
      actions.push(`<a href="${escapeHtml(item.audio_download_url)}" target="_blank" rel="noopener">Open audio</a>`);
    }
    if (item.srt_download_url) {
      actions.push(`<a href="${escapeHtml(item.srt_download_url)}" target="_blank" rel="noopener">Open transcript (.srt)</a>`);
    }
    if (item.folder_path) {
      actions.push(`<button class="copy-folder-btn" data-folder="${escapeHtml(item.folder_path)}" type="button">Copy folder path</button>`);
    }

    return `
      <li class="output-item">
        <div class="output-meta">
          <span class="output-name">${escapeHtml(item.output_name || "audio output")}</span>
          <span class="output-date">${escapeHtml(formatIso(item.created_at))}</span>
        </div>
        <div class="output-actions">${actions.join(" ")}</div>
        <div class="folder-line">${escapeHtml(item.folder_path || "")}</div>
      </li>
    `;
  });

  outputListNode.innerHTML = rows.join("");
}

async function loadOutputs() {
  const projectId = state.activeProjectRef;
  if (!projectId) return;

  try {
    const data = await requestJSON(`/projects/${encodeURIComponent(projectId)}/outputs`, "GET");
    const outputs = Array.isArray(data.outputs) ? data.outputs : [];
    renderOutputs(outputs);
  } catch (err) {
    renderOutputs([]);
    setGenerateStatus(`Could not load output history: ${String(err)}`, true);
  }
}

function updateProgressVisuals(progressPercent, stage) {
  const clamped = Math.max(0, Math.min(100, progressPercent));
  if (progressWrapNode) progressWrapNode.hidden = false;
  if (progressFillNode) progressFillNode.style.width = `${clamped}%`;
  if (progressPercentNode) progressPercentNode.textContent = `${Math.round(clamped)}%`;
  if (progressStageNode) progressStageNode.textContent = stageLabels[stage] || stage || "Processing";

  if (progressEtaNode) {
    if (state.currentStatus === "running") {
      const eta = smoothEtaDisplay(estimateEtaSeconds(clamped, stage));
      progressEtaNode.textContent = `ETA: ${formatEta(eta)}`;
    } else {
      state.etaSeconds = null;
      state.etaUpdatedAtMs = null;
      progressEtaNode.textContent = "ETA: --:--";
    }
  }

  if (progressDetailNode) {
    const compute = computeModeLabel();
    if (compute && state.latestDetail) {
      progressDetailNode.textContent = `${compute}. ${state.latestDetail}`;
    } else if (compute) {
      progressDetailNode.textContent = compute;
    } else {
      progressDetailNode.textContent = state.latestDetail || "Processing...";
    }
  }
}

function calculateSyntheticTarget() {
  if (state.currentStatus !== "running") {
    return state.actualProgress;
  }

  const stage = state.currentStage || "queued";
  const floor = stageProgressFloors[stage] ?? 0;
  const cap = stageProgressCaps[stage] ?? state.actualProgress;
  const expectedSec = stageExpectedSeconds[stage] ?? 90;
  const stageStart = state.stageStartedAtMs || Date.now();
  const elapsedSec = Math.max(0, (Date.now() - stageStart) / 1000);
  const ratio = Math.min(1, elapsedSec / expectedSec);
  const synthetic = floor + (cap - floor) * ratio;
  return Math.max(state.actualProgress, synthetic);
}

function progressAnimationTick() {
  const target = calculateSyntheticTarget();
  const delta = target - state.displayProgress;

  if (delta > 0) {
    state.displayProgress += Math.min(delta, 0.6);
  } else {
    state.displayProgress = target;
  }

  updateProgressVisuals(state.displayProgress, state.currentStage);
}

function startProgressAnimator() {
  stopProgressAnimator();
  state.progressAnimator = setInterval(progressAnimationTick, 120);
}

function applyJobSnapshot(job) {
  const status = String(job.status || "running");
  const stage = String(job.stage || state.currentStage || "queued");

  state.currentStatus = status;

  if (!state.jobStartedAtMs) {
    state.jobStartedAtMs = Date.now();
  }

  if (state.currentStage !== stage) {
    state.currentStage = stage;
    state.stageStartedAtMs = Date.now();
  }

  if (Number.isFinite(Number(job.progress))) {
    state.actualProgress = Math.max(state.actualProgress, Number(job.progress) * 100);
  }

  const logs = Array.isArray(job.logs) ? job.logs : [];
  const latestLog = logs.length ? detailFromLogLine(logs[logs.length - 1], stage) : "";
  const mode = detectComputeMode(job);
  if (mode) {
    state.computeMode = mode;
  }

  if (state.computeMode !== state.lastAnnouncedComputeMode) {
    if (state.computeMode === "worker") {
      setGenerateStatus("Worker picked up this job. It is running on a worker device.");
    } else if (state.computeMode === "server") {
      setGenerateStatus("No worker accepted this job. It is now running on the RADTTS server (Mac mini).");
    }
    state.lastAnnouncedComputeMode = state.computeMode;
  }

  if (latestLog) {
    state.latestDetail = latestLog;
  } else {
    state.latestDetail = stageLabels[stage] || "Processing...";
  }

  if (status === "completed") {
    state.actualProgress = 100;
    state.displayProgress = Math.max(state.displayProgress, 100);
    updateProgressVisuals(100, "completed");
  }

  if (status === "failed") {
    state.actualProgress = Math.max(state.actualProgress, 100);
    state.latestDetail = job.error ? `Error: ${job.error}` : "Generation failed.";
  }

  if (status === "cancelled") {
    state.latestDetail = "Cancellation complete.";
  }
}

async function pollJob() {
  if (!state.activeJobId || !state.activeProjectRef) return;

  try {
    const data = await requestJSON(
      `/jobs/${encodeURIComponent(state.activeJobId)}?project_id=${encodeURIComponent(state.activeProjectRef)}`,
      "GET"
    );

    applyJobSnapshot(data);

    if (data.status === "completed") {
      clearJobTracking();
      setGenerateEnabled(true);
      setCancelVisible(false);
      setGenerateStatus("Audio generation complete.");
      await loadOutputs();
      return;
    }

    if (data.status === "failed") {
      clearJobTracking();
      setGenerateEnabled(true);
      setCancelVisible(false);
      setGenerateStatus(`Generation failed: ${data.error || "Unknown error"}`, true);
      return;
    }

    if (data.status === "cancelled") {
      clearJobTracking();
      setGenerateEnabled(true);
      setCancelVisible(false);
      setGenerateStatus("Generation cancelled.", true);
      return;
    }
  } catch (err) {
    if (String(err).includes("404")) {
      return;
    }
    clearJobTracking();
    setGenerateEnabled(true);
    setCancelVisible(false);
    setGenerateStatus(`Progress check failed: ${String(err)}`, true);
  }
}

function startPolling(jobId, options = {}) {
  const initialStage = options.initialStage || "queued";
  const initialDetail = options.initialDetail || "Job queued. Preparing model...";
  clearJobTracking();
  state.activeJobId = jobId;
  state.currentStatus = "running";
  state.currentStage = initialStage;
  state.jobStartedAtMs = Date.now();
  state.stageStartedAtMs = Date.now();
  state.actualProgress = 0;
  state.displayProgress = 0;
  state.latestDetail = initialDetail;
  state.expectedRemoteWorker = Boolean(options.expectedRemoteWorker);
  state.computeMode = state.expectedRemoteWorker ? "waiting_worker" : "server";
  state.lastAnnouncedComputeMode = "idle";

  updateProgressVisuals(0, initialStage);
  startProgressAnimator();
  state.pollTimer = setInterval(pollJob, 2000);
  void pollJob();
}

async function handleGenerate() {
  try {
    const projectId = requireActiveProject();
    const scriptText = cleanOptional(scriptTextNode?.value || "");

    if (!state.selectedAudioFile && !state.selectedAudioHash) {
      throw new Error("Please select, record, or choose a saved audio sample.");
    }
    if (!scriptText) {
      throw new Error("Please provide script text.");
    }

    setGenerateEnabled(false);
    setCancelVisible(false);
    setGenerateStatus("Uploading files and starting generation...");
    resetProgressUi();

    const payload = {
      project_id: projectId,
      text: scriptText,
      quality: qualityNode?.value || "normal",
      add_ums: Boolean(umsToggleNode?.checked),
      add_ahs: Boolean(ahsToggleNode?.checked),
      average_gap_seconds: Number(gapSliderNode?.value || 0.8),
      output_format: outputFormatNode?.value || "mp3",
      voice_clone_authorized: true,
      generate_transcript: Boolean(transcriptToggleNode?.checked),
    };

    if (state.selectedAudioHash) {
      payload.reference_audio_hash = state.selectedAudioHash;
    } else if (state.selectedAudioFile) {
      payload.reference_audio_b64 = await fileToBase64(state.selectedAudioFile);
      payload.reference_audio_filename = state.selectedAudioFile.name;
    }

    const data = await requestJSON("/synthesize/simple", "POST", payload);
    const workerMode = Boolean(data.worker_mode);
    const fallbackEnabled = Boolean(data.fallback_enabled);
    const fallbackTimeout = Number(data.fallback_timeout_seconds || 0);

    if (workerMode) {
      if (fallbackEnabled && fallbackTimeout > 0) {
        setGenerateStatus(
          `Waiting for a worker device. If none starts within ${fallbackTimeout}s, this server will run it automatically.`
        );
      } else {
        setGenerateStatus("Waiting for a worker device to start processing.");
      }
    } else {
      setGenerateStatus("Generation started on this server.");
    }
    setCancelVisible(true);
    setCancelEnabled(true);
    startPolling(data.job_id, {
      initialStage: String(data.stage || (workerMode ? "queued_remote" : "queued")),
      initialDetail: workerMode
        ? "Job queued for worker processing."
        : "Job queued. Preparing model...",
      expectedRemoteWorker: workerMode,
    });
  } catch (err) {
    setGenerateEnabled(true);
    setCancelVisible(false);
    setGenerateStatus(String(err), true);
  }
}

async function handleCancel() {
  if (!state.activeJobId || !state.activeProjectRef) return;

  try {
    setCancelEnabled(false);
    setGenerateStatus("Cancelling generation...");
    state.latestDetail = "Cancellation requested. Waiting for current stage to stop...";
    await requestJSON(
      `/jobs/${encodeURIComponent(state.activeJobId)}/cancel?project_id=${encodeURIComponent(state.activeProjectRef)}`,
      "POST"
    );
  } catch (err) {
    setCancelEnabled(true);
    setGenerateStatus(`Cancel failed: ${String(err)}`, true);
  }
}

function bindProjectGateway() {
  const createForm = document.getElementById("create-form");
  if (createForm) {
    createForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const fd = new FormData(createForm);
      const projectId = (fd.get("project_id") || "").trim();

      if (!projectId) {
        setGatewayStatus("Project ID is required.", true);
        return;
      }

      const payload = {
        project_id: projectId,
        course: cleanOptional(fd.get("course")),
        module: cleanOptional(fd.get("module")),
        lesson: cleanOptional(fd.get("lesson")),
      };

      try {
        const created = await requestJSON("/projects", "POST", payload);
        const projectRef = String(created.project_ref || projectId);
        applyActiveProject(projectRef, projectId);
        setGatewayStatus("");
        await loadProjects(projectRef);
      } catch (err) {
        setGatewayStatus(`Project create failed: ${String(err)}`, true);
      }
    });
  }

  if (existingProjectSelectNode) {
    existingProjectSelectNode.addEventListener("change", () => {
      const projectRef = existingProjectSelectNode.value.trim();
      if (!projectRef) {
        setGatewayStatus("");
        return;
      }
      const selectedOption = existingProjectSelectNode.selectedOptions[0];
      const projectLabel = selectedOption?.dataset?.projectLabel || projectRef;
      applyActiveProject(projectRef, projectLabel);
      setGatewayStatus("");
    });
  }

  if (refreshProjectsBtn) {
    refreshProjectsBtn.addEventListener("click", async () => {
      await loadProjects(existingProjectSelectNode ? existingProjectSelectNode.value : null);
    });
  }

  if (switchProjectBtn) {
    switchProjectBtn.addEventListener("click", async () => {
      stopRecordingIfActive();
      clearJobTracking();
      state.activeProjectRef = null;
      state.activeProjectLabel = null;
      state.canManageActiveProject = false;
      state.selectedAudioHash = null;
      state.referenceSamples = [];
      if (activeProjectLabelNode) activeProjectLabelNode.textContent = "";
      if (shareProjectBtn) shareProjectBtn.hidden = true;
      setWorkspaceVisible(false);
      setGenerateEnabled(true);
      setCancelVisible(false);
      setGenerateStatus("");
      resetProgressUi();
      setSelectedAudioFile(null);
      clearRecordingPreview();
      if (savedSampleSelectNode) {
        savedSampleSelectNode.innerHTML = '<option value="">No project selected</option>';
      }
      setSavedSampleStatus("Saved samples are scoped to this project.");
      await loadProjects();
    });
  }

  setWorkspaceVisible(false);
  if (shareProjectBtn) shareProjectBtn.hidden = true;
  loadProjects();
}

function bindProjectSharing() {
  if (!shareProjectBtn) return;

  shareProjectBtn.addEventListener("click", async () => {
    if (!state.activeProjectRef) return;
    if (!state.canManageActiveProject) {
      setGenerateStatus("Only project owners can share this project.", true);
      return;
    }

    const emailInput = window.prompt("Share project with user email:");
    const email = String(emailInput || "").trim().toLowerCase();
    if (!email) return;

    try {
      const result = await requestJSON(
        `/projects/${encodeURIComponent(state.activeProjectRef)}/access/grant`,
        "POST",
        { email }
      );
      const count = Array.isArray(result.collaborators) ? result.collaborators.length : 0;
      setGenerateStatus(`Access granted to ${email}. Collaborators: ${count}.`);
      await loadProjects(state.activeProjectRef);
    } catch (err) {
      setGenerateStatus(`Share failed: ${String(err)}`, true);
    }
  });
}

function bindAudioSelection() {
  if (savedSampleSelectNode) {
    savedSampleSelectNode.addEventListener("change", () => {
      const selectedHash = savedSampleSelectNode.value;
      if (selectedHash) {
        applySavedSampleSelection(selectedHash);
      } else if (!state.selectedAudioFile) {
        state.selectedAudioHash = null;
        if (audioDropzoneTitleNode) {
          audioDropzoneTitleNode.textContent = "Drop audio here or click to choose";
        }
        if (audioFileNameNode) {
          audioFileNameNode.textContent = "No file selected.";
        }
      }
    });
  }

  if (refreshSamplesBtn) {
    refreshSamplesBtn.addEventListener("click", () => {
      void loadReferenceSamples();
    });
  }

  if (audioFileInputNode) {
    audioFileInputNode.addEventListener("change", async () => {
      const file = audioFileInputNode.files && audioFileInputNode.files[0];
      setSelectedAudioFile(file || null);
      if (file) {
        await attachAudioFileToProject(file, "Uploaded audio");
      }
    });
  }

  if (!audioDropzoneNode) return;

  ["dragenter", "dragover"].forEach((eventName) => {
    audioDropzoneNode.addEventListener(eventName, (event) => {
      event.preventDefault();
      audioDropzoneNode.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    audioDropzoneNode.addEventListener(eventName, (event) => {
      event.preventDefault();
      audioDropzoneNode.classList.remove("drag-over");
    });
  });

  audioDropzoneNode.addEventListener("drop", (event) => {
    const dt = event.dataTransfer;
    const file = dt && dt.files && dt.files[0];
    if (!file) return;
    setSelectedAudioFile(file);
    void attachAudioFileToProject(file, "Dropped audio");
  });
}

function bindRecording() {
  if (!recordAudioBtn) return;

  updateRecordButtonState(false);

  recordAudioBtn.addEventListener("click", async () => {
    const recorder = state.mediaRecorder;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
      return;
    }

    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
      setRecordStatus("Microphone recording is not supported in this browser.", true);
      return;
    }
    if (typeof window.MediaRecorder === "undefined") {
      setRecordStatus("MediaRecorder is not available in this browser.", true);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.recordingStream = stream;
      state.recordingChunks = [];

      const mimeType = getRecorderMimeType();
      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = options ? new MediaRecorder(stream, options) : new MediaRecorder(stream);
      state.mediaRecorder = mediaRecorder;

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data && event.data.size > 0) {
          state.recordingChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("stop", async () => {
        updateRecordButtonState(false);
        stopRecordingStreamTracks();

        if (!state.recordingChunks.length) {
          setRecordStatus("No audio captured. Try recording again.", true);
          state.mediaRecorder = null;
          return;
        }

        const recordedMimeType = mediaRecorder.mimeType || "audio/webm";
        const blob = new Blob(state.recordingChunks, { type: recordedMimeType });
        const stamp = new Date().toISOString().replace(/[:.]/g, "-");
        const extension = extensionForMimeType(recordedMimeType);
        const filename = `recorded-voice-${stamp}.${extension}`;
        const file = new File([blob], filename, { type: recordedMimeType });

        clearRecordingPreview();
        if (recordPreviewNode) {
          state.recordingPreviewUrl = URL.createObjectURL(blob);
          recordPreviewNode.src = state.recordingPreviewUrl;
          recordPreviewNode.hidden = false;
        }

        setSelectedAudioFile(file);
        await attachAudioFileToProject(file, "Recorded audio");
        state.recordingChunks = [];
        state.mediaRecorder = null;
      });

      mediaRecorder.addEventListener("error", () => {
        updateRecordButtonState(false);
        stopRecordingStreamTracks();
        setRecordStatus("Recording failed. Please try again.", true);
        state.mediaRecorder = null;
      });

      mediaRecorder.start();
      updateRecordButtonState(true);
      setRecordStatus("Recording... click Stop recording when finished.");
    } catch (err) {
      stopRecordingStreamTracks();
      updateRecordButtonState(false);
      setRecordStatus(`Could not access microphone: ${String(err)}`, true);
      state.mediaRecorder = null;
    }
  });
}

function bindScriptFileLoader() {
  if (!scriptFileInputNode) return;

  scriptFileInputNode.addEventListener("change", async () => {
    const file = scriptFileInputNode.files && scriptFileInputNode.files[0];
    if (!file) return;

    if (scriptFileStatusNode) scriptFileStatusNode.textContent = "Reading file...";

    try {
      const text = await readScriptFile(file);
      if (scriptTextNode) {
        scriptTextNode.value = text.trim();
      }
      if (scriptFileStatusNode) {
        scriptFileStatusNode.textContent = `Loaded ${file.name}`;
      }
    } catch (err) {
      if (scriptFileStatusNode) {
        scriptFileStatusNode.textContent = `Failed to load ${file.name}: ${String(err)}`;
      }
    }
  });
}

function bindGapSlider() {
  if (!gapSliderNode || !gapValueNode) return;

  const update = () => {
    gapValueNode.textContent = Number(gapSliderNode.value).toFixed(2);
  };

  gapSliderNode.addEventListener("input", update);
  update();
}

function bindGenerate() {
  if (generateBtn) generateBtn.addEventListener("click", handleGenerate);
  if (cancelBtn) cancelBtn.addEventListener("click", handleCancel);
}

function bindFolderCopy() {
  if (!outputListNode) return;

  outputListNode.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (!target.classList.contains("copy-folder-btn")) return;

    const folderPath = target.dataset.folder || "";
    if (!folderPath) return;

    navigator.clipboard
      .writeText(folderPath)
      .then(() => {
        setGenerateStatus("Folder path copied to clipboard.");
      })
      .catch(() => {
        setGenerateStatus("Could not copy folder path.", true);
      });
  });
}

bindProjectGateway();
bindProjectSharing();
bindAudioSelection();
bindRecording();
bindScriptFileLoader();
bindGapSlider();
bindGenerate();
bindFolderCopy();
setSelectedAudioFile(null);
setSavedSampleStatus("Saved samples are scoped to this project.");
setRecordStatus("Use Record audio to capture a sample from your microphone.");
setCancelVisible(false);
resetProgressUi();
