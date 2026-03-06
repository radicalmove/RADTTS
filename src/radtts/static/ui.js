const projectGatewayNode = document.getElementById("project-gateway");
const workspaceNode = document.getElementById("workspace");
const switchProjectBtn = document.getElementById("switch-project-btn");
const shareProjectBtn = document.getElementById("share-project-btn");
const activeProjectChip = document.getElementById("active-project-chip");
const activeProjectLabelNode = document.getElementById("active-project-label");
const workerStatusPillNode = document.getElementById("worker-status-pill");
const workerStatusDetailNode = document.getElementById("worker-status-detail");
const workerRefreshBtn = document.getElementById("worker-refresh-btn");
const workerSetupBtn = document.getElementById("worker-setup-btn");
const workerSetupLinksNode = document.getElementById("worker-setup-links");
const workerSetupWindowsLinkNode = document.getElementById("worker-setup-windows-link");
const workerSetupMacosLinkNode = document.getElementById("worker-setup-macos-link");
const workerCopyMacosBtn = document.getElementById("worker-copy-macos-btn");
const workerCopyLinuxBtn = document.getElementById("worker-copy-linux-btn");

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
const scriptVersionSelectNode = document.getElementById("script-version-select");
const restoreScriptVersionBtn = document.getElementById("restore-script-version-btn");
const scriptSaveStatusNode = document.getElementById("script-save-status");

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
const progressComputeNode = document.getElementById("progress-compute");
const progressEtaNode = document.getElementById("progress-eta");
const progressPercentNode = document.getElementById("progress-percent");
const progressFillNode = document.getElementById("progress-fill");
const progressDetailNode = document.getElementById("progress-detail");

const outputListNode = document.getElementById("output-list");

const stageLabels = {
  queued: "Queued",
  queued_remote: "Queued for helper device",
  worker_running: "Helper device processing",
  fallback_local: "Switching to server",
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
  workerFallbackTimeoutSeconds: 0,
  queuedRemoteSinceMs: null,
  lastRunningStatusKey: null,
  workerOnlineCount: null,
  workerTotalCount: null,
  workerOnlineWindowSeconds: null,
  scriptVersions: [],
  currentScriptVersionId: "",
  scriptSaveTimer: null,
  scriptSaveInFlight: false,
  pendingScriptSaveSource: null,
  suppressScriptAutosave: false,
  workerStatusPollTimer: null,
  workerSetupLinuxCommand: "",
  workerSetupMacosCommand: "",
  workerSetupWindowsUrl: "",
  workerSetupMacosUrl: "",
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

function setScriptSaveStatus(message, isError = false) {
  if (!scriptSaveStatusNode) return;
  scriptSaveStatusNode.textContent = message || "";
  scriptSaveStatusNode.style.color = isError ? "#a73527" : "#555";
}

function setWorkerStatusUi(mode, detailText) {
  if (workerStatusPillNode) {
    workerStatusPillNode.classList.remove("worker-pill-online", "worker-pill-offline", "worker-pill-unknown");
    if (mode === "online") {
      workerStatusPillNode.classList.add("worker-pill-online");
      workerStatusPillNode.textContent = "Helper status: connected";
    } else if (mode === "offline") {
      workerStatusPillNode.classList.add("worker-pill-offline");
      workerStatusPillNode.textContent = "Helper status: not connected";
    } else {
      workerStatusPillNode.classList.add("worker-pill-unknown");
      workerStatusPillNode.textContent = "Helper status: checking";
    }
  }
  if (workerStatusDetailNode) {
    workerStatusDetailNode.textContent = detailText || "";
  }
}

function hideWorkerSetupLinks() {
  if (workerSetupLinksNode) {
    workerSetupLinksNode.hidden = true;
  }
}

function clearWorkerSetupLinks() {
  state.workerSetupLinuxCommand = "";
  state.workerSetupMacosCommand = "";
  state.workerSetupWindowsUrl = "";
  state.workerSetupMacosUrl = "";
  if (workerSetupWindowsLinkNode) workerSetupWindowsLinkNode.href = "#";
  if (workerSetupMacosLinkNode) workerSetupMacosLinkNode.href = "#";
  hideWorkerSetupLinks();
}

function resetWorkerStatusUi() {
  setWorkerStatusUi("unknown", "Select a project to check helper availability.");
  if (workerSetupBtn) workerSetupBtn.hidden = true;
  clearWorkerSetupLinks();
}

function stopWorkerStatusPolling() {
  if (state.workerStatusPollTimer) {
    clearInterval(state.workerStatusPollTimer);
    state.workerStatusPollTimer = null;
  }
}

function startWorkerStatusPolling() {
  stopWorkerStatusPolling();
  void refreshWorkerStatus({ announceErrors: false });
  state.workerStatusPollTimer = setInterval(() => {
    if (!state.activeProjectRef) return;
    void refreshWorkerStatus({ announceErrors: false });
  }, 25000);
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
  state.workerFallbackTimeoutSeconds = 0;
  state.queuedRemoteSinceMs = null;
  state.lastRunningStatusKey = null;
  state.workerOnlineCount = null;
  state.workerTotalCount = null;
  state.workerOnlineWindowSeconds = null;

  if (progressWrapNode) progressWrapNode.hidden = true;
  if (progressFillNode) progressFillNode.style.width = "0%";
  if (progressPercentNode) progressPercentNode.textContent = "0%";
  if (progressStageNode) progressStageNode.textContent = "Queued";
  if (progressComputeNode) progressComputeNode.textContent = "Processing on: --";
  if (progressEtaNode) progressEtaNode.textContent = "Time left to process: --:--";
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

  // Keep queue/fallback stages conservative, but avoid large ETA jumps once actively processing.
  if (["queued", "queued_remote", "fallback_local"].includes(stage)) {
    return Math.max(progressBased, stageBased * 0.8);
  }
  return (progressBased * 0.82) + (stageBased * 0.18);
}

function smoothEtaDisplay(etaSeconds, stage) {
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
  const isWaitingStage = stage === "queued_remote" || state.computeMode === "waiting_worker";

  let nextEta;
  if (diff <= 4) {
    nextEta = decayed;
  } else {
    nextEta = (decayed * 0.7) + (etaSeconds * 0.3);
  }

  // Prevent visible spikes near stage boundaries (for example around ~79%).
  // Waiting-for-worker can still rise a bit as queue conditions change.
  const maxStepUp = isWaitingStage ? 12 : 2;
  if (nextEta > decayed + maxStepUp) {
    nextEta = decayed + maxStepUp;
  }

  state.etaSeconds = Math.max(0, nextEta);
  state.etaUpdatedAtMs = nowMs;
  return state.etaSeconds;
}

function detectComputeMode(job) {
  const stage = String(job.stage || state.currentStage || "");
  const logs = Array.isArray(job.logs) ? job.logs : [];
  const joinedLogs = logs.join("\n").toLowerCase();

  if (
    stage === "worker_running" ||
    (joinedLogs.includes("worker ") && joinedLogs.includes("started processing")) ||
    (joinedLogs.includes("worker ") && joinedLogs.includes("completed job"))
  ) {
    return "worker";
  }

  if (
    stage === "fallback_local" ||
    joinedLogs.includes("switching to local server fallback")
  ) {
    return "server";
  }

  if (["model_load", "generation", "stitching", "captioning"].includes(stage)) {
    // These stages are emitted by local server processing.
    return "server";
  }

  if (stage === "queued_remote") {
    return "waiting_worker";
  }

  if (!state.expectedRemoteWorker) {
    return "server";
  }

  if (state.computeMode === "worker" || state.computeMode === "server") {
    return state.computeMode;
  }
  return "waiting_worker";
}

function computeModeProgressLabel() {
  if (state.computeMode === "worker") {
    return "Processing on: local helper device";
  }
  if (state.computeMode === "server") {
    return "Processing on: RADTTS server (Mac mini)";
  }
  if (state.computeMode === "waiting_worker") {
    return "Processing on: waiting for helper device";
  }
  return "Processing on: --";
}

function workerAvailabilitySummary() {
  if (!Number.isFinite(state.workerOnlineCount)) {
    return "";
  }
  const online = Math.max(0, Number(state.workerOnlineCount));
  const total = Number.isFinite(state.workerTotalCount) ? Math.max(online, Number(state.workerTotalCount)) : null;
  if (total !== null) {
    return `${online}/${total} helper devices online`;
  }
  return `${online} helper device${online === 1 ? "" : "s"} online`;
}

function fallbackWaitRemainingSeconds() {
  if (
    !state.expectedRemoteWorker ||
    !state.workerFallbackTimeoutSeconds ||
    !state.queuedRemoteSinceMs
  ) {
    return null;
  }
  const elapsed = (Date.now() - state.queuedRemoteSinceMs) / 1000;
  return Math.max(0, state.workerFallbackTimeoutSeconds - elapsed);
}

function updateRunningStatusMessage() {
  if (state.currentStatus !== "running") return;

  if (state.computeMode === "worker") {
    if (state.lastRunningStatusKey !== "worker") {
      setGenerateStatus("Helper connected. Processing on your local helper device.");
      state.lastRunningStatusKey = "worker";
    }
    return;
  }

  if (state.computeMode === "server") {
    if (state.lastRunningStatusKey !== "server") {
      if (state.expectedRemoteWorker) {
        const availability = workerAvailabilitySummary();
        if (Number(state.workerOnlineCount || 0) <= 0) {
          setGenerateStatus("No active helper was connected, so this job is running on the RADTTS server (Mac mini).");
        } else if (availability) {
          setGenerateStatus(`No helper accepted this job (${availability}). Running on the RADTTS server (Mac mini).`);
        } else {
          setGenerateStatus("No helper accepted this job. Processing on the RADTTS server (Mac mini).");
        }
      } else {
        setGenerateStatus("Processing on the RADTTS server (Mac mini).");
      }
      state.lastRunningStatusKey = "server";
    }
    return;
  }

  if (state.computeMode === "waiting_worker") {
    const remaining = fallbackWaitRemainingSeconds();
    const availability = workerAvailabilitySummary();
    const noWorkersKnown = Number(state.workerOnlineCount || 0) <= 0;
    if (remaining === null) {
      if (state.lastRunningStatusKey !== "waiting_worker") {
        if (noWorkersKnown) {
          setGenerateStatus("No active helper is connected yet. Waiting for a helper device.");
        } else if (availability) {
          setGenerateStatus(`Waiting for a helper device (${availability}).`);
        } else {
          setGenerateStatus("Waiting for a helper device.");
        }
        state.lastRunningStatusKey = "waiting_worker";
      }
      return;
    }

    const remainingLabel = formatEta(remaining);
    const waitingKey = `waiting_${Math.ceil(remaining)}`;
    if (state.lastRunningStatusKey !== waitingKey) {
      if (remaining > 0) {
        if (noWorkersKnown) {
          setGenerateStatus(`No active helper is connected. Waiting up to ${remainingLabel} before server fallback.`);
        } else if (availability) {
          setGenerateStatus(`Waiting for a helper device (${availability}). Server fallback in ${remainingLabel}.`);
        } else {
          setGenerateStatus(`Waiting for a helper device. Server fallback in ${remainingLabel}.`);
        }
      } else {
        setGenerateStatus("No helper connected yet. Switching to server fallback...");
      }
      state.lastRunningStatusKey = waitingKey;
    }
  }
}

function formatIso(isoValue) {
  if (!isoValue) return "";
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return String(isoValue);
  return date.toLocaleString();
}

function clearScriptSaveTimer() {
  if (state.scriptSaveTimer) {
    clearTimeout(state.scriptSaveTimer);
    state.scriptSaveTimer = null;
  }
}

function formatScriptVersionLabel(version) {
  const savedAt = formatIso(version.saved_at) || "Saved";
  const source = String(version.source || "");
  const sourceLabel = source && source !== "autosave" ? ` (${source.replaceAll("_", " ")})` : "";
  const preview = String(version.preview || "").trim();
  if (preview) {
    return `${savedAt}${sourceLabel} - ${preview}`;
  }
  const words = Number(version.word_count || 0);
  return `${savedAt}${sourceLabel} - ${words} word${words === 1 ? "" : "s"}`;
}

function currentScriptVersionMeta() {
  const currentId = state.currentScriptVersionId;
  if (!currentId) return null;
  for (const version of state.scriptVersions) {
    if (String(version.version_id || "") === currentId) {
      return version;
    }
  }
  return null;
}

function updateRestoreScriptButtonState() {
  if (!restoreScriptVersionBtn || !scriptVersionSelectNode) return;
  const selectedVersion = String(scriptVersionSelectNode.value || "");
  const hasSelection = Boolean(selectedVersion);
  const selectedIsCurrent = selectedVersion === state.currentScriptVersionId;
  restoreScriptVersionBtn.disabled = !hasSelection || selectedIsCurrent;
}

function refreshScriptVersionSelect() {
  if (!scriptVersionSelectNode) return;

  const previousSelection = String(scriptVersionSelectNode.value || "");
  scriptVersionSelectNode.innerHTML = "";
  scriptVersionSelectNode.disabled = state.scriptVersions.length === 0;

  if (!state.scriptVersions.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No saved script versions yet";
    scriptVersionSelectNode.appendChild(option);
    scriptVersionSelectNode.value = "";
    updateRestoreScriptButtonState();
    return;
  }

  for (const version of state.scriptVersions) {
    const option = document.createElement("option");
    option.value = String(version.version_id || "");
    option.textContent = formatScriptVersionLabel(version);
    scriptVersionSelectNode.appendChild(option);
  }

  const fallbackSelection = state.currentScriptVersionId || String(state.scriptVersions[0].version_id || "");
  scriptVersionSelectNode.value = previousSelection || fallbackSelection;
  if (!scriptVersionSelectNode.value) {
    scriptVersionSelectNode.value = fallbackSelection;
  }
  updateRestoreScriptButtonState();
}

function applyScriptPayload(payload, { replaceText = true } = {}) {
  const versions = Array.isArray(payload?.versions) ? payload.versions : [];
  state.scriptVersions = versions.map((version) => ({
    version_id: String(version.version_id || ""),
    saved_at: String(version.saved_at || ""),
    source: String(version.source || ""),
    word_count: Number(version.word_count || 0),
    char_count: Number(version.char_count || 0),
    preview: String(version.preview || ""),
  }));
  state.currentScriptVersionId = String(payload?.current_version_id || "");

  if (replaceText && scriptTextNode) {
    state.suppressScriptAutosave = true;
    scriptTextNode.value = String(payload?.text || "");
    state.suppressScriptAutosave = false;
  }

  refreshScriptVersionSelect();
}

function resetScriptEditorState() {
  clearScriptSaveTimer();
  state.scriptVersions = [];
  state.currentScriptVersionId = "";
  state.scriptSaveInFlight = false;
  state.pendingScriptSaveSource = null;
  state.suppressScriptAutosave = false;

  if (scriptTextNode) {
    scriptTextNode.value = "";
  }
  if (scriptFileInputNode) {
    scriptFileInputNode.value = "";
  }
  if (scriptFileStatusNode) {
    scriptFileStatusNode.textContent = "No text file loaded.";
  }
  refreshScriptVersionSelect();
  setScriptSaveStatus("Script saves automatically in this project.");
}

async function loadProjectScript() {
  if (!state.activeProjectRef) return;
  setScriptSaveStatus("Loading saved script...");

  try {
    const data = await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/script`,
      "GET"
    );
    applyScriptPayload(data, { replaceText: true });
    if (state.scriptVersions.length) {
      setScriptSaveStatus("Loaded saved script for this project.");
    } else {
      setScriptSaveStatus("No saved script yet. Start typing to save automatically.");
    }
  } catch (err) {
    setScriptSaveStatus(`Could not load saved script: ${String(err)}`, true);
  }
}

function queueScriptSave(source = "autosave", delayMs = 1200) {
  if (!state.activeProjectRef || !scriptTextNode || state.suppressScriptAutosave) {
    return;
  }
  clearScriptSaveTimer();
  state.pendingScriptSaveSource = source;
  state.scriptSaveTimer = setTimeout(() => {
    void flushScriptSave();
  }, delayMs);
}

async function flushScriptSave(sourceOverride = null) {
  if (!state.activeProjectRef || !scriptTextNode || state.suppressScriptAutosave) {
    return false;
  }

  clearScriptSaveTimer();
  const source = sourceOverride || state.pendingScriptSaveSource || "autosave";
  state.pendingScriptSaveSource = null;

  if (state.scriptSaveInFlight) {
    state.pendingScriptSaveSource = source;
    return false;
  }

  state.scriptSaveInFlight = true;
  setScriptSaveStatus("Saving script...");

  try {
    const data = await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/script`,
      "POST",
      {
        text: scriptTextNode.value || "",
        source,
      }
    );
    applyScriptPayload(data, { replaceText: false });
    const currentVersion = currentScriptVersionMeta();
    if (data.saved) {
      const when = currentVersion?.saved_at ? formatIso(currentVersion.saved_at) : "";
      setScriptSaveStatus(when ? `Script saved at ${when}.` : "Script saved.");
    } else {
      setScriptSaveStatus("All changes saved.");
    }
    return true;
  } catch (err) {
    setScriptSaveStatus(`Could not save script: ${String(err)}`, true);
    return false;
  } finally {
    state.scriptSaveInFlight = false;
    if (state.pendingScriptSaveSource) {
      const queuedSource = state.pendingScriptSaveSource;
      state.pendingScriptSaveSource = null;
      void flushScriptSave(queuedSource);
    }
  }
}

async function handleRestoreScriptVersion() {
  if (!state.activeProjectRef || !scriptVersionSelectNode) return;

  const versionId = String(scriptVersionSelectNode.value || "");
  if (!versionId) return;

  clearScriptSaveTimer();
  state.pendingScriptSaveSource = null;
  setScriptSaveStatus("Restoring selected version...");
  if (restoreScriptVersionBtn) restoreScriptVersionBtn.disabled = true;

  try {
    const data = await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/script/restore`,
      "POST",
      { version_id: versionId }
    );
    applyScriptPayload(data, { replaceText: true });
    const currentVersion = currentScriptVersionMeta();
    const when = currentVersion?.saved_at ? formatIso(currentVersion.saved_at) : "";
    setScriptSaveStatus(when ? `Restored script from ${when}.` : "Restored selected script version.");
  } catch (err) {
    setScriptSaveStatus(`Could not restore script version: ${String(err)}`, true);
  } finally {
    updateRestoreScriptButtonState();
  }
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

function humanizeWorkerTerms(text) {
  return String(text || "")
    .replace(/\bworker device\b/gi, "helper device")
    .replace(/\bworker app\b/gi, "helper app")
    .replace(/\bworkers\b/gi, "helper devices")
    .replace(/\bworker\b/gi, "helper");
}

function friendlyStageDetail(stage) {
  const key = String(stage || "").trim().toLowerCase();
  if (key === "queued") return "Preparing your job";
  if (key === "queued_remote") return "Checking for an available helper device";
  if (key === "worker_running") return "Processing on a helper device";
  if (key === "fallback_local") return "Switching to the RADTTS server";
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
    return "Looking for an available helper device...";
  }

  if (lower.includes("started processing") && lower.includes("worker")) {
    return "Helper device accepted the job.";
  }

  if (lower.includes("switching to local server fallback")) {
    return "No helper accepted in time. Starting on RADTTS server.";
  }

  const stageMatch = lower.match(/stage=([a-z_]+)/);
  if (stageMatch?.[1]) {
    const stageText = friendlyStageDetail(stageMatch[1]);
    if (lower.includes("starting")) return `${stageText}...`;
    if (lower.includes("complete")) return `${stageText} complete.`;
    return `${stageText}.`;
  }

  return humanizeWorkerTerms(cleaned);
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

function describeWorkerAvailability(online, total) {
  if (online > 0) {
    if (total > 0) {
      return `${online}/${total} helper device${total === 1 ? "" : "s"} online.`;
    }
    return `${online} helper device${online === 1 ? "" : "s"} online.`;
  }
  if (total > 0) {
    return `0/${total} helper devices online. Jobs will use server fallback when needed.`;
  }
  return "No helper app connected yet. Jobs will use server fallback when needed.";
}

async function refreshWorkerStatus({ announceErrors = false } = {}) {
  if (!state.activeProjectRef) {
    resetWorkerStatusUi();
    return;
  }
  if (workerRefreshBtn) workerRefreshBtn.disabled = true;
  try {
    const data = await requestJSON("/workers/status", "GET");
    const online = Math.max(0, Number(data.worker_online_count || 0));
    const total = Math.max(0, Number(data.worker_total_count || 0));
    state.workerOnlineCount = online;
    state.workerTotalCount = total;
    state.workerOnlineWindowSeconds = Math.max(0, Number(data.worker_online_window_seconds || 0));

    const detail = describeWorkerAvailability(online, total);
    if (online > 0) {
      setWorkerStatusUi("online", detail);
      if (workerSetupBtn) workerSetupBtn.hidden = true;
      hideWorkerSetupLinks();
    } else {
      setWorkerStatusUi("offline", detail);
      if (workerSetupBtn) workerSetupBtn.hidden = false;
    }
  } catch (err) {
    setWorkerStatusUi("unknown", "Could not check helper status.");
    if (workerSetupBtn) workerSetupBtn.hidden = false;
    if (announceErrors) {
      setGenerateStatus(`Could not check helper status: ${String(err)}`, true);
    }
  } finally {
    if (workerRefreshBtn) workerRefreshBtn.disabled = false;
  }
}

async function ensureWorkerSetupLinks() {
  if (
    state.workerSetupWindowsUrl &&
    state.workerSetupMacosUrl &&
    state.workerSetupMacosCommand &&
    state.workerSetupLinuxCommand
  ) {
    if (workerSetupLinksNode) workerSetupLinksNode.hidden = false;
    return;
  }
  if (workerSetupBtn) workerSetupBtn.disabled = true;
  try {
    const data = await requestJSON("/workers/invite", "POST", { capabilities: ["synthesize"] });
    state.workerSetupWindowsUrl = String(data.windows_installer_url || "").trim();
    state.workerSetupMacosUrl = String(data.macos_installer_url || "").trim();
    state.workerSetupMacosCommand = String(data.install_command_macos || data.install_command || "").trim();
    state.workerSetupLinuxCommand = String(data.install_command_linux || data.install_command || "").trim();

    if (workerSetupWindowsLinkNode && state.workerSetupWindowsUrl) {
      workerSetupWindowsLinkNode.href = state.workerSetupWindowsUrl;
    }
    if (workerSetupMacosLinkNode && state.workerSetupMacosUrl) {
      workerSetupMacosLinkNode.href = state.workerSetupMacosUrl;
    }
    if (workerSetupLinksNode) workerSetupLinksNode.hidden = false;
    setGenerateStatus("Helper setup links are ready. Run the installer once on each colleague device.");
  } catch (err) {
    setGenerateStatus(`Could not generate helper setup links: ${String(err)}`, true);
  } finally {
    if (workerSetupBtn) workerSetupBtn.disabled = false;
  }
}

async function copyTextToClipboard(text) {
  const value = String(text || "");
  if (!value) {
    throw new Error("Nothing to copy");
  }

  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.top = "-1000px";
  area.style.left = "-1000px";
  document.body.appendChild(area);
  area.focus();
  area.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(area);
  if (!copied) {
    throw new Error("Clipboard unavailable");
  }
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
  resetScriptEditorState();
  setGenerateEnabled(true);
  setCancelVisible(false);
  clearWorkerSetupLinks();
  void loadOutputs();
  void loadReferenceSamples();
  void loadProjectScript();
  void refreshProjectAccessInfo();
  startWorkerStatusPolling();
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

  const rows = outputs.map((item, index) => {
    const actions = [];
    const outputId = `output-${index}`;
    const audioPlayUrl = String(item.audio_play_url || item.audio_download_url || "");
    if (item.audio_download_url) {
      if (audioPlayUrl) {
        actions.push(
          `<button class="play-audio-btn" data-output-id="${escapeHtml(outputId)}" type="button" aria-expanded="false">Play audio</button>`
        );
      }
      actions.push(`<a href="${escapeHtml(item.audio_download_url)}" download>Save audio as</a>`);
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
        ${
          audioPlayUrl
            ? `<div class="output-audio-player" data-output-id="${escapeHtml(outputId)}" hidden>
                 <audio controls preload="metadata" src="${escapeHtml(audioPlayUrl)}"></audio>
               </div>`
            : ""
        }
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
  if (progressComputeNode) progressComputeNode.textContent = computeModeProgressLabel();

  if (progressEtaNode) {
    if (state.currentStatus === "running") {
      const eta = smoothEtaDisplay(estimateEtaSeconds(clamped, stage), stage);
      progressEtaNode.textContent = `Time left to process: ${formatEta(eta)}`;
    } else {
      state.etaSeconds = null;
      state.etaUpdatedAtMs = null;
      progressEtaNode.textContent = "Time left to process: --:--";
    }
  }

  if (progressDetailNode) {
    let detail = state.latestDetail || "Processing...";
    if (state.computeMode === "waiting_worker" && state.currentStage === "queued_remote") {
      detail = "Looking for a connected helper app. Server fallback is automatic if none responds.";
    }
    progressDetailNode.textContent = detail;
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
  updateRunningStatusMessage();
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

  updateRunningStatusMessage();
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
  const fallbackTimeoutSeconds = Number(options.fallbackTimeoutSeconds || 0);
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
  state.workerFallbackTimeoutSeconds = fallbackTimeoutSeconds > 0 ? fallbackTimeoutSeconds : 0;
  state.queuedRemoteSinceMs = state.expectedRemoteWorker ? Date.now() : null;
  state.lastRunningStatusKey = null;

  updateProgressVisuals(0, initialStage);
  updateRunningStatusMessage();
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

    await flushScriptSave("manual");

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
    const workerOnlineCount = Number.isFinite(Number(data.worker_online_count))
      ? Number(data.worker_online_count)
      : null;
    const workerTotalCount = Number.isFinite(Number(data.worker_total_count))
      ? Number(data.worker_total_count)
      : null;
    const workerOnlineWindowSeconds = Number.isFinite(Number(data.worker_online_window_seconds))
      ? Number(data.worker_online_window_seconds)
      : null;

    state.workerOnlineCount = workerOnlineCount;
    state.workerTotalCount = workerTotalCount;
    state.workerOnlineWindowSeconds = workerOnlineWindowSeconds;

    if (workerMode) {
      if (workerOnlineCount !== null && workerOnlineCount <= 0) {
        setGenerateStatus("No active helper is connected right now. Waiting for helper assignment...");
      } else {
        setGenerateStatus("Job queued for helper assignment...");
      }
    } else {
      setGenerateStatus("Generation started on this server.");
    }
    setCancelVisible(true);
    setCancelEnabled(true);
    startPolling(data.job_id, {
      initialStage: String(data.stage || (workerMode ? "queued_remote" : "queued")),
      initialDetail: workerMode
        ? "Checking for an available helper device..."
        : "Job queued. Preparing model...",
      expectedRemoteWorker: workerMode,
      fallbackTimeoutSeconds: workerMode && fallbackEnabled ? fallbackTimeout : 0,
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
      stopWorkerStatusPolling();
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
      resetWorkerStatusUi();
      resetScriptEditorState();
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

function bindWorkerStatus() {
  if (workerRefreshBtn) {
    workerRefreshBtn.addEventListener("click", () => {
      void refreshWorkerStatus({ announceErrors: true });
    });
  }

  if (workerSetupBtn) {
    workerSetupBtn.addEventListener("click", () => {
      void ensureWorkerSetupLinks();
    });
  }

  if (workerSetupWindowsLinkNode) {
    workerSetupWindowsLinkNode.addEventListener("click", (event) => {
      const href = String(workerSetupWindowsLinkNode.getAttribute("href") || "").trim();
      if (href && href !== "#") return;
      event.preventDefault();
      void (async () => {
        await ensureWorkerSetupLinks();
        const refreshed = String(workerSetupWindowsLinkNode.getAttribute("href") || "").trim();
        if (refreshed && refreshed !== "#") {
          window.open(refreshed, "_blank", "noopener");
        } else {
          setGenerateStatus("Windows installer link is not available yet.", true);
        }
      })();
    });
  }

  if (workerSetupMacosLinkNode) {
    workerSetupMacosLinkNode.addEventListener("click", (event) => {
      const href = String(workerSetupMacosLinkNode.getAttribute("href") || "").trim();
      if (href && href !== "#") return;
      event.preventDefault();
      void (async () => {
        await ensureWorkerSetupLinks();
        const refreshed = String(workerSetupMacosLinkNode.getAttribute("href") || "").trim();
        if (refreshed && refreshed !== "#") {
          window.open(refreshed, "_blank", "noopener");
        } else {
          setGenerateStatus("Mac installer link is not available yet.", true);
        }
      })();
    });
  }

  if (workerCopyLinuxBtn) {
    workerCopyLinuxBtn.addEventListener("click", () => {
      void (async () => {
        let command = state.workerSetupLinuxCommand;
        if (!command) {
          await ensureWorkerSetupLinks();
          command = state.workerSetupLinuxCommand;
        }
        if (!command) {
          setGenerateStatus("No Linux setup command available yet.", true);
          return;
        }
        try {
          await copyTextToClipboard(command);
          setGenerateStatus("Linux helper setup command copied.");
        } catch {
          window.prompt("Copy this Linux setup command:", command);
          setGenerateStatus("Could not auto-copy. A manual copy prompt is shown.", true);
        }
      })();
    });
  }

  if (workerCopyMacosBtn) {
    workerCopyMacosBtn.addEventListener("click", () => {
      void (async () => {
        let command = state.workerSetupMacosCommand;
        if (!command) {
          await ensureWorkerSetupLinks();
          command = state.workerSetupMacosCommand;
        }
        if (!command) {
          setGenerateStatus("No Mac setup command available yet.", true);
          return;
        }
        try {
          await copyTextToClipboard(command);
          setGenerateStatus("Mac helper setup command copied.");
        } catch {
          window.prompt("Copy this Mac setup command:", command);
          setGenerateStatus("Could not auto-copy. A manual copy prompt is shown.", true);
        }
      })();
    });
  }
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
        state.suppressScriptAutosave = true;
        scriptTextNode.value = text.trim();
        state.suppressScriptAutosave = false;
      }
      if (scriptFileStatusNode) {
        scriptFileStatusNode.textContent = `Loaded ${file.name}`;
      }
      await flushScriptSave("file_upload");
    } catch (err) {
      state.suppressScriptAutosave = false;
      if (scriptFileStatusNode) {
        scriptFileStatusNode.textContent = `Failed to load ${file.name}: ${String(err)}`;
      }
    }
  });
}

function bindScriptPersistence() {
  if (scriptTextNode) {
    scriptTextNode.addEventListener("input", () => {
      if (state.suppressScriptAutosave) return;
      queueScriptSave("autosave");
    });

    scriptTextNode.addEventListener("blur", () => {
      if (state.suppressScriptAutosave) return;
      if (!state.pendingScriptSaveSource) return;
      void flushScriptSave("autosave");
    });
  }

  if (scriptVersionSelectNode) {
    scriptVersionSelectNode.addEventListener("change", () => {
      updateRestoreScriptButtonState();
    });
  }

  if (restoreScriptVersionBtn) {
    restoreScriptVersionBtn.addEventListener("click", () => {
      void handleRestoreScriptVersion();
    });
  }
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

function toggleOutputAudioPlayer(button) {
  if (!outputListNode) return;
  const outputId = button.dataset.outputId || "";
  if (!outputId) return;

  const playerWrap = Array.from(outputListNode.querySelectorAll(".output-audio-player")).find((node) => {
    return node instanceof HTMLElement && node.dataset.outputId === outputId;
  });
  if (!(playerWrap instanceof HTMLElement)) return;
  const audio = playerWrap.querySelector("audio");
  if (!(audio instanceof HTMLAudioElement)) return;

  const isOpen = !playerWrap.hidden;
  if (isOpen) {
    audio.pause();
    playerWrap.hidden = true;
    button.textContent = "Play audio";
    button.setAttribute("aria-expanded", "false");
    return;
  }

  for (const wrapNode of outputListNode.querySelectorAll(".output-audio-player")) {
    if (!(wrapNode instanceof HTMLElement)) continue;
    if (wrapNode.dataset.outputId === outputId) continue;
    const otherAudio = wrapNode.querySelector("audio");
    if (otherAudio instanceof HTMLAudioElement) {
      otherAudio.pause();
    }
    wrapNode.hidden = true;
  }

  for (const otherBtn of outputListNode.querySelectorAll(".play-audio-btn")) {
    if (!(otherBtn instanceof HTMLButtonElement)) continue;
    if (otherBtn.dataset.outputId === outputId) continue;
    otherBtn.textContent = "Play audio";
    otherBtn.setAttribute("aria-expanded", "false");
  }

  playerWrap.hidden = false;
  button.textContent = "Hide player";
  button.setAttribute("aria-expanded", "true");
  const playPromise = audio.play();
  if (playPromise && typeof playPromise.catch === "function") {
    playPromise.catch(() => {});
  }
}

function bindOutputActions() {
  if (!outputListNode) return;

  outputListNode.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    const playButton = target.closest(".play-audio-btn");
    if (playButton instanceof HTMLButtonElement) {
      toggleOutputAudioPlayer(playButton);
      return;
    }

    const copyButton = target.closest(".copy-folder-btn");
    if (!(copyButton instanceof HTMLButtonElement)) return;

    const folderPath = copyButton.dataset.folder || "";
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
bindWorkerStatus();
bindAudioSelection();
bindRecording();
bindScriptFileLoader();
bindScriptPersistence();
bindGapSlider();
bindGenerate();
bindOutputActions();
setSelectedAudioFile(null);
resetScriptEditorState();
resetWorkerStatusUi();
setSavedSampleStatus("Saved samples are scoped to this project.");
setRecordStatus("Use Record audio to capture a sample from your microphone.");
setCancelVisible(false);
resetProgressUi();
