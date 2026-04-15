const projectGatewayNode = document.getElementById("project-gateway");
const workspaceNode = document.getElementById("workspace");
const switchProjectBtn = document.getElementById("switch-project-btn");
const shareProjectBtn = document.getElementById("share-project-btn");
const helpBtn = document.getElementById("help-btn");
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
const workerSetupModalNode = document.getElementById("worker-setup-modal");
const workerSetupCloseBtn = document.getElementById("worker-setup-close-btn");
const workerSetupModalStatusNode = document.getElementById("worker-setup-modal-status");

const existingProjectSelectNode = document.getElementById("existing-project-select");
const recentProjectListNode = document.getElementById("recent-project-list");
const refreshProjectsBtn = document.getElementById("refresh-projects-btn");
const projectGatewayStatusNode = document.getElementById("project-gateway-status");

const audioDropzoneNode = document.getElementById("audio-dropzone");
const audioFileInputNode = document.getElementById("reference-audio-file");
const audioDropzoneTitleNode = document.getElementById("audio-dropzone-title");
const audioFileNameNode = document.getElementById("audio-file-name");
const voiceSourceReferenceNode = document.getElementById("voice-source-reference");
const voiceSourceBuiltinNode = document.getElementById("voice-source-builtin");
const referenceVoicePaneNode = document.getElementById("reference-voice-pane");
const builtinVoicePaneNode = document.getElementById("builtin-voice-pane");
const savedSampleSelectNode = document.getElementById("saved-sample-select");
const refreshSamplesBtn = document.getElementById("refresh-samples-btn");
const deleteSavedSampleBtn = document.getElementById("delete-saved-sample-btn");
const savedSampleStatusNode = document.getElementById("saved-sample-status");
const recordAudioBtn = document.getElementById("record-audio-btn");
const recordStatusNode = document.getElementById("record-status");
const referencePreviewLabelNode = document.getElementById("reference-preview-label");
const recordPreviewNode = document.getElementById("record-preview");
const referenceTrimModalNode = document.getElementById("reference-trim-modal");
const referenceTrimCloseBtn = document.getElementById("reference-trim-close-btn");
const referenceTrimModalStatusNode = document.getElementById("reference-trim-modal-status");
const referenceTrimSourceNameNode = document.getElementById("reference-trim-source-name");
const referenceTrimSourceDurationNode = document.getElementById("reference-trim-source-duration");
const referenceTrimPreviewNode = document.getElementById("reference-trim-preview");
const referenceTrimStartNode = document.getElementById("reference-trim-start");
const referenceTrimEndNode = document.getElementById("reference-trim-end");
const referenceTrimStartValueNode = document.getElementById("reference-trim-start-value");
const referenceTrimEndValueNode = document.getElementById("reference-trim-end-value");
const referenceTrimSelectionSummaryNode = document.getElementById("reference-trim-selection-summary");
const referenceTrimPlayBtn = document.getElementById("reference-trim-play-btn");
const referenceTrimApplyBtn = document.getElementById("reference-trim-apply-btn");
const referenceTrimSkipBtn = document.getElementById("reference-trim-skip-btn");
const shareProjectModalNode = document.getElementById("share-project-modal");
const shareProjectCloseBtn = document.getElementById("share-project-close-btn");
const shareProjectUserSelectNode = document.getElementById("share-project-user-select");
const shareProjectGrantBtn = document.getElementById("share-project-grant-btn");
const shareProjectStatusNode = document.getElementById("share-project-status");
const shareProjectOwnerNode = document.getElementById("share-project-owner");
const shareProjectMembersNode = document.getElementById("share-project-members");
const helpModalNode = document.getElementById("help-modal");
const helpModalCloseBtn = document.getElementById("help-close-btn");
const helpModalTabsNode = helpModalNode ? helpModalNode.querySelector(".help-modal-tabs") : null;
const builtinVoiceSelectNode = document.getElementById("builtin-voice-select");
const builtinVoiceStatusNode = document.getElementById("builtin-voice-status");
const previewBuiltinVoiceBtn = document.getElementById("preview-builtin-voice-btn");
const builtinVoicePreviewNode = document.getElementById("builtin-voice-preview");

const scriptTextNode = document.getElementById("script-text");
const scriptFileInputNode = document.getElementById("script-file");
const scriptFileStatusNode = document.getElementById("script-file-status");
const scriptVersionSelectNode = document.getElementById("script-version-select");
const restoreScriptVersionBtn = document.getElementById("restore-script-version-btn");
const deleteScriptVersionBtn = document.getElementById("delete-script-version-btn");
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
  worker_running: 28,
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
  queued: 4,
  queued_remote: 40,
  worker_running: 18,
  fallback_local: 24,
  model_load: 26,
  generation: 210,
  stitching: 22,
  captioning: 55,
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
  referencePreviewObjectUrl: null,
  pendingReferenceFile: null,
  pendingReferenceOriginLabel: "",
  pendingReferenceDurationSeconds: null,
  referenceTrimPreviewObjectUrl: null,
  referenceTrimStopTimer: null,
  referenceSamples: [],
  voiceSource: "reference",
  builtinVoices: [],
  selectedBuiltInSpeaker: "",
  builtinVoicePreviewUrl: null,
  expectedRemoteWorker: false,
  computeMode: "idle",
  lastAnnouncedComputeMode: "idle",
  etaSeconds: null,
  etaUpdatedAtMs: null,
  etaStage: null,
  workerFallbackTimeoutSeconds: 0,
  queuedRemoteSinceMs: null,
  lastRunningStatusKey: null,
  workerLiveCount: null,
  workerRecentCount: null,
  workerRegisteredCount: null,
  workerStaleCount: null,
  workerLastLiveSeenAt: null,
  workerLastRecentSeenAt: null,
  workerOnlineCount: null,
  workerTotalCount: null,
  workerOnlineWindowSeconds: null,
  workerRecentWindowSeconds: null,
  generateTranscriptRequested: false,
  outputFormatRequested: "mp3",
  stageProgressSamples: [],
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
  currentJobLogs: [],
  completedOutputs: [],
  currentRunProfile: null,
  pollFailureCount: 0,
  pollFailureStartedAtMs: null,
  shareProjectUsers: [],
  shareProjectCollaborators: [],
  shareProjectOwner: null,
  projectSettings: null,
  projectSettingsSaveTimer: null,
};

const HELP_STORAGE_KEY = "radtts-help-last-tab";
const HELP_TAB_ORDER = [
  "overview",
  "generate-audio",
  "use-custom-voice",
  "prepare-reference-audio",
  "manage-versions-and-outputs",
  "use-helper-processing",
  "troubleshooting",
];
const HELP_FIRST_TAB_KEY = HELP_TAB_ORDER[0];

let helpModalReturnFocusNode = null;

function cleanOptional(value) {
  const trimmed = (value ?? "").trim();
  return trimmed.length ? trimmed : null;
}

function defaultProjectSettings() {
  return {
    selected_audio_hash: null,
    voice_source: "reference",
    built_in_speaker: null,
    quality: "normal",
    add_ums: false,
    add_ahs: false,
    generate_transcript: false,
    output_format: "mp3",
    average_gap_seconds: 0.8,
  };
}

function normalizeProjectSettings(payload) {
  const data = payload && typeof payload === "object" ? payload : {};
  const selectedAudioHash = cleanOptional(data.selected_audio_hash);
  const voiceSource = String(cleanOptional(data.voice_source) || "").toLowerCase() === "builtin"
    ? "builtin"
    : "reference";
  const quality = String(cleanOptional(data.quality) || "").toLowerCase() === "high" ? "high" : "normal";
  const outputFormat = String(cleanOptional(data.output_format) || "").toLowerCase() === "wav" ? "wav" : "mp3";
  const builtInSpeaker = cleanOptional(data.built_in_speaker);
  const gap = Number(data.average_gap_seconds);

  return {
    selected_audio_hash: selectedAudioHash && selectedAudioHash.length >= 16 ? selectedAudioHash : null,
    voice_source: voiceSource,
    built_in_speaker: builtInSpeaker,
    quality,
    add_ums: Boolean(data.add_ums),
    add_ahs: Boolean(data.add_ahs),
    generate_transcript: Boolean(data.generate_transcript),
    output_format: outputFormat,
    average_gap_seconds: Number.isFinite(gap) ? Math.max(0.15, Math.min(2.5, gap)) : 0.8,
  };
}

function updateGapValueDisplay() {
  if (!gapSliderNode || !gapValueNode) return;
  gapValueNode.textContent = Number(gapSliderNode.value || 0.8).toFixed(2);
}

function applyProjectSettingsToControls(settings) {
  const normalized = normalizeProjectSettings(settings);
  state.projectSettings = normalized;
  state.selectedAudioHash = normalized.selected_audio_hash;
  state.selectedBuiltInSpeaker = normalized.built_in_speaker || "";

  if (qualityNode) {
    qualityNode.value = normalized.quality;
  }
  if (outputFormatNode) {
    outputFormatNode.value = normalized.output_format;
  }
  if (umsToggleNode) {
    umsToggleNode.checked = normalized.add_ums;
  }
  if (ahsToggleNode) {
    ahsToggleNode.checked = normalized.add_ahs;
  }
  if (transcriptToggleNode) {
    transcriptToggleNode.checked = normalized.generate_transcript;
  }
  if (gapSliderNode) {
    gapSliderNode.value = Number(normalized.average_gap_seconds).toFixed(2);
  }
  updateGapValueDisplay();
  setVoiceSourceUi(normalized.voice_source);

  if (builtinVoiceSelectNode) {
    builtinVoiceSelectNode.value = state.selectedBuiltInSpeaker || "";
  }
}

function resetProjectSettingsControls() {
  applyProjectSettingsToControls(defaultProjectSettings());
}

function currentProjectSettingsPayload() {
  return normalizeProjectSettings({
    selected_audio_hash: state.selectedAudioHash,
    voice_source: state.voiceSource,
    built_in_speaker: state.selectedBuiltInSpeaker,
    quality: qualityNode?.value || "normal",
    add_ums: Boolean(umsToggleNode?.checked),
    add_ahs: Boolean(ahsToggleNode?.checked),
    generate_transcript: Boolean(transcriptToggleNode?.checked),
    output_format: outputFormatNode?.value || "mp3",
    average_gap_seconds: gapSliderNode?.value ?? 0.8,
  });
}

function clearProjectSettingsSaveTimer() {
  if (state.projectSettingsSaveTimer) {
    clearTimeout(state.projectSettingsSaveTimer);
    state.projectSettingsSaveTimer = null;
  }
}

async function saveProjectSettings(projectRef, settings) {
  if (!projectRef) return;
  const normalized = normalizeProjectSettings(settings);
  try {
    const data = await requestJSON(`/projects/${encodeURIComponent(projectRef)}/settings`, "PUT", normalized);
    if (state.activeProjectRef === projectRef) {
      state.projectSettings = normalizeProjectSettings(data?.settings);
    }
  } catch (err) {
    console.warn("Could not save project settings", err);
  }
}

function queueProjectSettingsSave() {
  const projectRef = state.activeProjectRef;
  if (!projectRef) return;
  const settings = currentProjectSettingsPayload();
  state.projectSettings = settings;
  clearProjectSettingsSaveTimer();
  state.projectSettingsSaveTimer = setTimeout(() => {
    state.projectSettingsSaveTimer = null;
    void saveProjectSettings(projectRef, settings);
  }, 250);
}

async function loadProjectSettings(projectRef) {
  if (!projectRef) return defaultProjectSettings();
  try {
    const data = await requestJSON(`/projects/${encodeURIComponent(projectRef)}/settings`, "GET");
    return normalizeProjectSettings(data?.settings);
  } catch (err) {
    console.warn("Could not load project settings", err);
    return defaultProjectSettings();
  }
}

async function restoreProjectSettings(projectRef) {
  resetProjectSettingsControls();
  const settings = await loadProjectSettings(projectRef);
  if (state.activeProjectRef !== projectRef) return;

  applyProjectSettingsToControls(settings);
  await loadReferenceSamples(settings.selected_audio_hash);
  if (state.activeProjectRef !== projectRef) return;
  await loadBuiltinVoices();
  if (state.activeProjectRef !== projectRef) return;
  state.projectSettings = currentProjectSettingsPayload();
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

function formatGenerationErrorMessage(message) {
  const raw = String(message || "").trim();
  if (!raw) return "Unknown error";
  const lower = raw.toLowerCase();
  const timeoutMatch = raw.match(/timed out after (\d+)s/i);
  if (state.voiceSource === "reference" && lower.includes("worker_generation") && lower.includes("timed out")) {
    const timeoutLabel = timeoutMatch ? ` after ${timeoutMatch[1]}s` : "";
    return (
      `Reference-voice generation timed out on the local helper${timeoutLabel}. ` +
      "Try a 6 to 15 second sample with one clear speaker, no background noise or long pauses, " +
      "and retry with Normal quality first."
    );
  }
  return raw;
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

function setBuiltinVoiceStatus(message, isError = false) {
  if (!builtinVoiceStatusNode) return;
  builtinVoiceStatusNode.textContent = message || "";
  builtinVoiceStatusNode.style.color = isError ? "#a73527" : "#555";
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

function setWorkerSetupModalStatus(message, isError = false) {
  if (!workerSetupModalStatusNode) return;
  workerSetupModalStatusNode.textContent = message || "";
  workerSetupModalStatusNode.style.color = isError ? "#a73527" : "#555";
}

function hideWorkerSetupLinks() {
  if (workerSetupLinksNode) {
    workerSetupLinksNode.hidden = true;
  }
}

function syncModalOpenState() {
  const anyModalOpen = [workerSetupModalNode, referenceTrimModalNode, shareProjectModalNode, helpModalNode]
    .some((node) => node && !node.hidden);
  document.body.classList.toggle("modal-open", anyModalOpen);
}

function getHelpTabButtonNodes() {
  if (!helpModalNode) return [];
  return Array.from(helpModalNode.querySelectorAll("[data-help-tab]")).filter((node) => node instanceof HTMLButtonElement);
}

function getHelpPanelNodes() {
  if (!helpModalNode) return [];
  return Array.from(helpModalNode.querySelectorAll("[data-help-panel]")).filter((node) => node instanceof HTMLElement);
}

function normalizeHelpTabKey(tabKey) {
  const normalized = String(tabKey || "").trim();
  return HELP_TAB_ORDER.includes(normalized) ? normalized : HELP_FIRST_TAB_KEY;
}

function readHelpTabFromStorage() {
  try {
    return normalizeHelpTabKey(localStorage.getItem(HELP_STORAGE_KEY));
  } catch {
    return HELP_FIRST_TAB_KEY;
  }
}

function persistHelpTab(tabKey) {
  try {
    localStorage.setItem(HELP_STORAGE_KEY, normalizeHelpTabKey(tabKey));
  } catch {
    // localStorage is optional in the Node behavior harness.
  }
}

function getHelpTabButton(tabKey) {
  return helpModalNode ? helpModalNode.querySelector(`[data-help-tab="${tabKey}"]`) : null;
}

function getHelpPanel(tabKey) {
  return helpModalNode ? helpModalNode.querySelector(`[data-help-panel="${tabKey}"]`) : null;
}

function selectHelpTab(tabKey, { focusTab = false, persist = true } = {}) {
  if (!helpModalNode) return;

  const activeTabKey = normalizeHelpTabKey(tabKey);
  const tabButtons = getHelpTabButtonNodes();
  const panels = getHelpPanelNodes();

  for (const tabButton of tabButtons) {
    const buttonKey = normalizeHelpTabKey(tabButton.dataset.helpTab);
    const isActive = buttonKey === activeTabKey;
    tabButton.classList.toggle("is-active", isActive);
    tabButton.setAttribute("aria-selected", isActive ? "true" : "false");
    tabButton.tabIndex = isActive ? 0 : -1;
  }

  for (const panel of panels) {
    const panelKey = normalizeHelpTabKey(panel.dataset.helpPanel);
    const isActive = panelKey === activeTabKey;
    panel.classList.toggle("is-active", isActive);
    panel.hidden = !isActive;
    if (isActive) {
      panel.scrollTop = 0;
    }
  }

  if (persist) {
    persistHelpTab(activeTabKey);
  }

  if (focusTab) {
    const activeButton = getHelpTabButton(activeTabKey);
    if (activeButton instanceof HTMLElement) {
      activeButton.focus();
    }
  }
}

function restoreHelpTab(options = {}) {
  selectHelpTab(readHelpTabFromStorage(), options);
}

function focusHelpReturnTarget() {
  if (helpModalReturnFocusNode instanceof HTMLElement && typeof helpModalReturnFocusNode.focus === "function") {
    helpModalReturnFocusNode.focus();
    return;
  }
  if (helpBtn instanceof HTMLElement && typeof helpBtn.focus === "function") {
    helpBtn.focus();
  }
}

function openHelpModal() {
  if (!helpModalNode) return;
  helpModalReturnFocusNode = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  helpModalNode.hidden = false;
  syncModalOpenState();
  restoreHelpTab({ focusTab: true });
}

function closeHelpModal() {
  if (!helpModalNode) return;
  helpModalNode.hidden = true;
  syncModalOpenState();
  focusHelpReturnTarget();
  helpModalReturnFocusNode = null;
}

function moveHelpTabFocus(currentKey, direction) {
  const currentIndex = HELP_TAB_ORDER.indexOf(normalizeHelpTabKey(currentKey));
  if (currentIndex < 0) return;
  const nextIndex = (currentIndex + direction + HELP_TAB_ORDER.length) % HELP_TAB_ORDER.length;
  selectHelpTab(HELP_TAB_ORDER[nextIndex], { focusTab: true });
}

function handleHelpTabKeydown(event) {
  if (!(event.target instanceof HTMLElement)) return;
  const tabButton = event.target.closest("[data-help-tab]");
  if (!(tabButton instanceof HTMLButtonElement)) return;

  const currentTabKey = normalizeHelpTabKey(tabButton.dataset.helpTab);
  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    event.preventDefault();
    moveHelpTabFocus(currentTabKey, 1);
    return;
  }

  if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    event.preventDefault();
    moveHelpTabFocus(currentTabKey, -1);
    return;
  }

  if (event.key === "Home") {
    event.preventDefault();
    selectHelpTab(HELP_FIRST_TAB_KEY, { focusTab: true });
    return;
  }

  if (event.key === "End") {
    event.preventDefault();
    selectHelpTab(HELP_TAB_ORDER[HELP_TAB_ORDER.length - 1], { focusTab: true });
    return;
  }

  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    selectHelpTab(currentTabKey, { focusTab: true });
  }
}

function helpModalElementHidden(node) {
  let currentNode = node;
  while (currentNode instanceof HTMLElement && currentNode !== helpModalNode) {
    if (currentNode.hidden) return true;
    if (typeof currentNode.getAttribute === "function" && currentNode.getAttribute("aria-hidden") === "true") return true;
    currentNode = currentNode.parentNode;
  }
  return false;
}

function isHelpModalFocusable(node) {
  if (!(node instanceof HTMLElement)) return false;
  if (helpModalElementHidden(node)) return false;
  if ("disabled" in node && node.disabled) return false;
  if (node.tabIndex < 0) return false;
  const tagName = String(node.tagName || "").toLowerCase();
  if (tagName === "button" || tagName === "input" || tagName === "select" || tagName === "textarea" || tagName === "summary") {
    return true;
  }
  if (tagName === "a") {
    return typeof node.getAttribute === "function" && node.getAttribute("href") !== null;
  }
  return typeof node.getAttribute === "function" && node.getAttribute("tabindex") !== null;
}

function getHelpModalFocusableNodes() {
  if (!(helpModalNode instanceof HTMLElement)) return [];
  const focusableNodes = [];
  const stack = Array.from(helpModalNode.children || []);
  while (stack.length) {
    const node = stack.shift();
    if (!(node instanceof HTMLElement)) continue;
    if (isHelpModalFocusable(node)) {
      focusableNodes.push(node);
    }
    stack.unshift(...Array.from(node.children || []));
  }
  return focusableNodes;
}

function handleHelpModalKeydown(event) {
  if (event.key !== "Tab" || !helpModalNode || helpModalNode.hidden) return;
  const focusableNodes = getHelpModalFocusableNodes();
  if (focusableNodes.length < 2) return;
  const firstNode = focusableNodes[0];
  const lastNode = focusableNodes[focusableNodes.length - 1];
  const activeNode = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  if (event.shiftKey) {
    if (activeNode !== firstNode) return;
    event.preventDefault();
    lastNode.focus();
    return;
  }
  if (activeNode !== lastNode) return;
  event.preventDefault();
  firstNode.focus();
}

function openWorkerSetupModal() {
  if (!workerSetupModalNode) return;
  workerSetupModalNode.hidden = false;
  syncModalOpenState();
  setWorkerSetupModalStatus("Preparing setup options...");
}

function closeWorkerSetupModal() {
  if (!workerSetupModalNode) return;
  workerSetupModalNode.hidden = true;
  syncModalOpenState();
}

function setShareProjectStatus(message, isError = false) {
  if (!shareProjectStatusNode) return;
  shareProjectStatusNode.textContent = message || "";
  shareProjectStatusNode.style.color = isError ? "#a73527" : "#555";
}

function formatShareProjectUserLabel(user) {
  const email = cleanOptional(user?.email) || "";
  const displayName = cleanOptional(user?.display_name) || email || "User";
  const username = cleanOptional(user?.username);
  const details = [];
  if (username) details.push(`@${username}`);
  if (email && displayName.toLowerCase() !== email.toLowerCase()) details.push(email);
  return details.length ? `${displayName} (${details.join(" · ")})` : displayName;
}

function renderShareProjectOwner(owner) {
  if (!shareProjectOwnerNode) return;
  const label = formatShareProjectUserLabel(owner || {});
  shareProjectOwnerNode.textContent = label === "User" ? "Unknown owner" : label;
}

function renderShareableUserOptions(users, collaborators) {
  if (!shareProjectUserSelectNode) return;
  const collaboratorEmails = new Set(
    (Array.isArray(collaborators) ? collaborators : [])
      .map((row) => cleanOptional(row?.email)?.toLowerCase())
      .filter(Boolean)
  );
  const availableUsers = (Array.isArray(users) ? users : []).filter((candidate) => {
    const email = cleanOptional(candidate?.email)?.toLowerCase();
    return Boolean(email) && !collaboratorEmails.has(email);
  });

  state.shareProjectUsers = availableUsers;
  shareProjectUserSelectNode.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = availableUsers.length ? "Select a user..." : "No additional users available";
  placeholder.disabled = true;
  placeholder.selected = true;
  shareProjectUserSelectNode.appendChild(placeholder);

  for (const candidate of availableUsers) {
    const option = document.createElement("option");
    option.value = String(candidate.email || "");
    option.textContent = formatShareProjectUserLabel(candidate);
    shareProjectUserSelectNode.appendChild(option);
  }

  shareProjectUserSelectNode.disabled = !availableUsers.length;
  if (shareProjectGrantBtn) {
    shareProjectGrantBtn.disabled = !availableUsers.length;
  }
}

function renderShareProjectMembers(collaborators) {
  if (!shareProjectMembersNode) return;
  const rows = Array.isArray(collaborators) ? collaborators : [];
  state.shareProjectCollaborators = rows;

  if (!rows.length) {
    shareProjectMembersNode.innerHTML = '<p class="share-project-empty">No collaborators yet.</p>';
    return;
  }

  shareProjectMembersNode.innerHTML = rows
    .map((row) => {
      const email = cleanOptional(row?.email) || "";
      const grantedAt = cleanOptional(row?.granted_at);
      const grantedBy = cleanOptional(row?.granted_by);
      const details = [];
      if (grantedAt) details.push(`Granted ${new Date(grantedAt).toLocaleString()}`);
      if (grantedBy) details.push(`by ${grantedBy}`);
      return `
        <div class="share-project-member-row">
          <div class="share-project-member-meta">
            <div class="share-project-member-name">${escapeHtml(email)}</div>
            <div class="share-project-member-detail">${escapeHtml(details.join(" · ") || "Collaborator")}</div>
          </div>
          <button type="button" class="worker-mini-btn share-project-remove-btn" data-email="${escapeHtml(email)}">Remove</button>
        </div>
      `;
    })
    .join("");
}

async function refreshShareProjectModal({ successMessage = "" } = {}) {
  if (!state.activeProjectRef) return;
  setShareProjectStatus("Loading sharing options...");
  if (shareProjectGrantBtn) shareProjectGrantBtn.disabled = true;
  if (shareProjectUserSelectNode) shareProjectUserSelectNode.disabled = true;

  try {
    const [accessData, usersData] = await Promise.all([
      requestJSON(`/projects/${encodeURIComponent(state.activeProjectRef)}/access`, "GET"),
      requestJSON(`/projects/${encodeURIComponent(state.activeProjectRef)}/shareable-users`, "GET"),
    ]);
    state.canManageActiveProject = Boolean(accessData.can_manage);
    if (shareProjectBtn) shareProjectBtn.hidden = !state.canManageActiveProject;
    state.shareProjectOwner = accessData.owner && typeof accessData.owner === "object" ? accessData.owner : {};
    renderShareProjectOwner(state.shareProjectOwner);
    renderShareProjectMembers(accessData.collaborators);
    renderShareableUserOptions(usersData.users, accessData.collaborators);
    setShareProjectStatus(successMessage);
  } catch (err) {
    if (shareProjectBtn) shareProjectBtn.hidden = true;
    renderShareProjectOwner({});
    renderShareProjectMembers([]);
    renderShareableUserOptions([], []);
    setShareProjectStatus(`Could not load sharing options: ${String(err)}`, true);
  }
}

function openShareProjectModal() {
  if (!shareProjectModalNode) return;
  shareProjectModalNode.hidden = false;
  syncModalOpenState();
  void refreshShareProjectModal();
}

function closeShareProjectModal() {
  if (!shareProjectModalNode) return;
  shareProjectModalNode.hidden = true;
  syncModalOpenState();
}

async function handleShareProjectGrant() {
  if (!state.activeProjectRef || !shareProjectUserSelectNode) return;
  const email = cleanOptional(shareProjectUserSelectNode.value)?.toLowerCase();
  if (!email) {
    setShareProjectStatus("Select a user to share with.", true);
    return;
  }

  if (shareProjectGrantBtn) shareProjectGrantBtn.disabled = true;
  try {
    await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/access/grant`,
      "POST",
      { email }
    );
    const message = `Access granted to ${email}.`;
    setGenerateStatus(message);
    await refreshShareProjectModal({ successMessage: message });
  } catch (err) {
    setShareProjectStatus(`Share failed: ${String(err)}`, true);
  } finally {
    if (shareProjectGrantBtn && state.shareProjectUsers.length) {
      shareProjectGrantBtn.disabled = false;
    }
  }
}

async function handleShareProjectRemove(email) {
  if (!state.activeProjectRef || !email) return;
  try {
    await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/access/revoke`,
      "POST",
      { email }
    );
    const message = `Access removed for ${email}.`;
    setGenerateStatus(message);
    await refreshShareProjectModal({ successMessage: message });
  } catch (err) {
    setShareProjectStatus(`Remove failed: ${String(err)}`, true);
  }
}

function clearWorkerSetupLinks() {
  state.workerSetupLinuxCommand = "";
  state.workerSetupMacosCommand = "";
  state.workerSetupWindowsUrl = "";
  state.workerSetupMacosUrl = "";
  if (workerSetupWindowsLinkNode) workerSetupWindowsLinkNode.href = "#";
  if (workerSetupMacosLinkNode) workerSetupMacosLinkNode.href = "#";
  setWorkerSetupModalStatus("Preparing setup options...");
  hideWorkerSetupLinks();
}

function resetWorkerStatusUi() {
  setWorkerStatusUi("unknown", "Select a project to check helper availability.");
  if (workerSetupBtn) workerSetupBtn.hidden = false;
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
  if (!visible) {
    closeWorkerSetupModal();
    closeShareProjectModal();
  }
}

function setVoiceSourceUi(source) {
  state.voiceSource = source === "builtin" ? "builtin" : "reference";
  if (voiceSourceReferenceNode) {
    voiceSourceReferenceNode.checked = state.voiceSource === "reference";
  }
  if (voiceSourceBuiltinNode) {
    voiceSourceBuiltinNode.checked = state.voiceSource === "builtin";
  }
  if (referenceVoicePaneNode) {
    referenceVoicePaneNode.hidden = state.voiceSource !== "reference";
  }
  if (builtinVoicePaneNode) {
    builtinVoicePaneNode.hidden = state.voiceSource !== "builtin";
  }
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
  state.currentRunProfile = null;
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
  state.etaStage = null;
  state.workerFallbackTimeoutSeconds = 0;
  state.queuedRemoteSinceMs = null;
  state.lastRunningStatusKey = null;
  state.workerLiveCount = null;
  state.workerRecentCount = null;
  state.workerRegisteredCount = null;
  state.workerStaleCount = null;
  state.workerLastLiveSeenAt = null;
  state.workerLastRecentSeenAt = null;
  state.workerOnlineCount = null;
  state.workerTotalCount = null;
  state.workerOnlineWindowSeconds = null;
  state.workerRecentWindowSeconds = null;
  state.generateTranscriptRequested = false;
  state.outputFormatRequested = "mp3";
  state.stageProgressSamples = [];
  state.currentRunProfile = null;
  state.pollFailureCount = 0;
  state.pollFailureStartedAtMs = null;

  if (progressWrapNode) progressWrapNode.hidden = true;
  if (progressFillNode) progressFillNode.style.width = "0%";
  if (progressPercentNode) progressPercentNode.textContent = "0%";
  if (progressStageNode) progressStageNode.textContent = "Queued";
  if (progressComputeNode) progressComputeNode.textContent = "Processing on: --";
  if (progressEtaNode) progressEtaNode.textContent = "Time left to process: --:--";
  if (progressDetailNode) progressDetailNode.textContent = "Preparing generation...";
}

const stageActualProgressEnds = {
  queued: 8,
  queued_remote: 18,
  worker_running: 100,
  fallback_local: 35,
  model_load: 35,
  generation: 72,
  stitching: 85,
  captioning: 100,
  completed: 100,
  failed: 100,
  cancelled: 0,
};

function currentRunEtaOrder(stage) {
  const currentStage = String(stage || state.currentStage || "queued");

  if (state.computeMode === "worker") {
    const workerOrder = ["queued_remote", "worker_running", "model_load", "generation", "stitching"];
    if (state.generateTranscriptRequested) {
      workerOrder.push("captioning");
    }
    workerOrder.push("completed");
    return workerOrder;
  }

  if (currentStage === "queued_remote" && state.computeMode === "waiting_worker") {
    if (Number.isFinite(state.workerOnlineCount) && state.workerOnlineCount > 0) {
      return ["queued_remote", "worker_running", "completed"];
    }

    const waitingOrder = ["queued_remote"];
    if (state.workerFallbackTimeoutSeconds > 0) {
      waitingOrder.push("fallback_local");
    }
    waitingOrder.push("model_load", "generation", "stitching");
    if (state.generateTranscriptRequested) {
      waitingOrder.push("captioning");
    }
    waitingOrder.push("completed");
    return waitingOrder;
  }

  const localOrder = ["queued"];
  if (state.expectedRemoteWorker) {
    localOrder.push("queued_remote", "fallback_local");
  }
  localOrder.push("model_load", "generation", "stitching");
  if (state.generateTranscriptRequested) {
    localOrder.push("captioning");
  }
  localOrder.push("completed");
  return localOrder;
}

function expectedStageSecondsForCurrentMode(stage) {
  const key = String(stage || "");
  const base = estimatedStageSeconds(key);
  if (!Number.isFinite(base) || base <= 0) {
    return 90;
  }

  if (key === "queued_remote" && state.workerFallbackTimeoutSeconds > 0) {
    return Math.max(base, state.workerFallbackTimeoutSeconds);
  }

  if (key === "stitching" && state.outputFormatRequested === "wav") {
    return Math.max(12, Math.round(base * 0.55));
  }

  if (state.computeMode === "server") {
    if (["model_load", "generation", "captioning"].includes(key)) {
      return Math.round(base * 1.04);
    }
    return Math.round(base * 1.02);
  }

  if (state.computeMode === "worker") {
    return Math.round(base * 0.92);
  }

  return Math.round(base);
}

function expectedFutureStageSeconds(stage) {
  let remainingFuture = 0;
  const order = currentRunEtaOrder(stage);
  const idx = order.indexOf(stage);
  if (idx < 0) return remainingFuture;

  for (const nextStage of order.slice(idx + 1)) {
    if (nextStage === "completed") continue;
    remainingFuture += expectedStageSecondsForCurrentMode(nextStage);
  }
  return remainingFuture;
}

function estimateEtaFromObservedVelocity(progressPercent, stage) {
  if (!Array.isArray(state.stageProgressSamples) || state.stageProgressSamples.length < 2) {
    return null;
  }

  const stageStart = stageProgressFloors[stage];
  const stageEnd = stageActualProgressEnds[stage];
  if (!Number.isFinite(stageStart) || !Number.isFinite(stageEnd) || stageEnd <= stageStart) {
    return null;
  }

  const first = state.stageProgressSamples[0];
  const last = state.stageProgressSamples[state.stageProgressSamples.length - 1];
  const deltaProgress = last.progress - first.progress;
  const deltaSeconds = (last.atMs - first.atMs) / 1000;
  if (deltaProgress < 0.75 || deltaSeconds < 2) {
    return null;
  }

  const speed = deltaProgress / deltaSeconds;
  if (!Number.isFinite(speed) || speed <= 0) {
    return null;
  }

  const currentProgress = Math.max(stageStart, Math.min(stageEnd, progressPercent));
  const remainingCurrentStage = Math.max(0, stageEnd - currentProgress) / speed;
  return remainingCurrentStage + expectedFutureStageSeconds(stage);
}

function estimateEtaSeconds(progressPercent, stage) {
  if (state.currentStatus !== "running") return null;
  const nowMs = Date.now();
  const clamped = Math.max(0, Math.min(100, progressPercent));
  const waitingForFirstChunk = isEarlyGenerationWithoutChunkProgress(state.currentJobLogs, stage);
  if (waitingForFirstChunk) return null;
  const observedBased = waitingForFirstChunk ? null : estimateEtaFromObservedVelocity(clamped, stage);

  let progressBased = null;
  if (state.jobStartedAtMs && clamped > 1 && clamped < 100 && !waitingForFirstChunk) {
    const elapsedSec = (nowMs - state.jobStartedAtMs) / 1000;
    const candidate = elapsedSec * ((100 - clamped) / clamped);
    if (Number.isFinite(candidate) && candidate >= 0) {
      progressBased = candidate;
    }
  }

  const stageExpected = expectedStageSecondsForCurrentMode(stage);
  let stageBased = null;
  if (stageExpected > 0 && state.stageStartedAtMs) {
    const elapsedStageSec = Math.max(0, (nowMs - state.stageStartedAtMs) / 1000);
    let remainingStage = stageExpected - elapsedStageSec;
    if (remainingStage < 0) {
      // Keep ETA moving even if a stage runs longer than expected.
      remainingStage = Math.min(900, 45 + Math.abs(remainingStage) * 0.85);
    }

    const remainingFuture = expectedFutureStageSeconds(stage);
    stageBased = Math.max(0, remainingStage + remainingFuture);
  }

  if (observedBased !== null && stageBased !== null) {
    return (observedBased * 0.84) + (stageBased * 0.16);
  }
  if (observedBased !== null) return observedBased;
  if (progressBased === null) return stageBased;
  if (stageBased === null) return progressBased;

  // Keep queue/fallback stages conservative, but avoid large ETA jumps once actively processing.
  if (["queued", "queued_remote", "fallback_local"].includes(stage)) {
    return Math.max(progressBased, stageBased * 0.8);
  }

  // Early progress is still somewhat noisy, but the current defaults were too pessimistic.
  if (clamped < 45) {
    return (progressBased * 0.45) + (stageBased * 0.55);
  }
  if (clamped < 70) {
    return (progressBased * 0.65) + (stageBased * 0.35);
  }
  return (progressBased * 0.82) + (stageBased * 0.18);
}

function smoothEtaDisplay(etaSeconds, stage) {
  if (!Number.isFinite(etaSeconds) || etaSeconds <= 0) {
    state.etaSeconds = null;
    state.etaUpdatedAtMs = null;
    state.etaStage = null;
    return null;
  }

  const nowMs = Date.now();
  if (state.etaSeconds === null || state.etaUpdatedAtMs === null) {
    state.etaSeconds = Math.max(1, etaSeconds);
    state.etaUpdatedAtMs = nowMs;
    state.etaStage = stage;
    return state.etaSeconds;
  }

  const elapsedSec = Math.max(0, (nowMs - state.etaUpdatedAtMs) / 1000);
  const decayed = Math.max(1, state.etaSeconds - elapsedSec);
  const stageChanged = state.etaStage !== null && state.etaStage !== stage;
  const severeUnderestimate = (
    (decayed <= 10 && etaSeconds >= 30)
    || (etaSeconds - decayed >= 60 && etaSeconds >= decayed * 2.5)
  );
  let nextEta = decayed;

  // Recover from obvious underestimates so long jobs do not get stuck at 00:01.
  if (severeUnderestimate) {
    nextEta = Math.max(1, etaSeconds);
  } else if (stageChanged || etaSeconds < decayed - 0.75) {
    nextEta = Math.max(1, etaSeconds);
  }

  state.etaSeconds = Math.max(1, nextEta);
  state.etaUpdatedAtMs = nowMs;
  state.etaStage = stage;
  return state.etaSeconds;
}

function detectComputeMode(job) {
  const stage = String(job.stage || state.currentStage || "");
  const logs = Array.isArray(job.logs) ? job.logs : [];
  const joinedLogs = logs.join("\n").toLowerCase();

  if (
    stage === "fallback_local" ||
    joinedLogs.includes("switching to local server fallback")
  ) {
    return "server";
  }

  if (
    stage === "worker_running" ||
    hasWorkerHeartbeatLog(logs) ||
    (joinedLogs.includes("worker ") && joinedLogs.includes("started processing")) ||
    (joinedLogs.includes("worker ") && joinedLogs.includes("completed job"))
  ) {
    return "worker";
  }

  if (["model_load", "generation", "stitching", "captioning"].includes(stage)) {
    if (
      state.computeMode === "worker" ||
      joinedLogs.includes("worker ") ||
      joinedLogs.includes("helper ")
    ) {
      return "worker";
    }
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
  if (!Number.isFinite(state.workerLiveCount) && !Number.isFinite(state.workerRecentCount)) {
    return "";
  }
  const live = Math.max(0, Number(state.workerLiveCount));
  const recent = Number.isFinite(state.workerRecentCount)
    ? Math.max(live, Number(state.workerRecentCount))
    : live;
  const stale = Number.isFinite(state.workerStaleCount) ? Math.max(0, Number(state.workerStaleCount)) : 0;
  const lastLiveSeen = state.workerLastLiveSeenAt ? formatIso(state.workerLastLiveSeenAt) : "";
  const lastRecentSeen = state.workerLastRecentSeenAt ? formatIso(state.workerLastRecentSeenAt) : lastLiveSeen;
  const parts = [];
  if (live > 0) {
    parts.push(`${live} live helper device${live === 1 ? "" : "s"}`);
  } else if (recent > 0) {
    parts.push(`${recent} recently seen helper device${recent === 1 ? "" : "s"}`);
  } else {
    parts.push("0 live helper devices");
  }
  if (stale > 0) {
    parts.push(`${stale} stale registration${stale === 1 ? "" : "s"}`);
  }
  if (lastLiveSeen) {
    parts.push(`last live seen ${lastLiveSeen}`);
  } else if (recent > 0 && lastRecentSeen) {
    parts.push(`last helper seen ${lastRecentSeen}`);
  }
  return parts.join(", ");
}

function latestWorkerFallbackReason() {
  const logs = Array.isArray(state.currentJobLogs) ? state.currentJobLogs : [];
  for (let idx = logs.length - 1; idx >= 0; idx -= 1) {
    const cleaned = stripLogTimestamp(logs[idx]).trim();
    const lower = cleaned.toLowerCase();
    if (lower.includes("stopped reporting progress")) {
      return "Helper device stopped reporting progress, so this job is running on the RADTTS server (Mac mini).";
    }
    if (lower.includes("no worker accepted this job after")) {
      return cleaned.replace(
        /No worker accepted this job after \d+s\./i,
        `No helper pulled this job within ${Math.round(state.workerFallbackTimeoutSeconds || 0)}s.`
      );
    }
    if (lower.includes("switching to local server fallback")) {
      return "Switching to the RADTTS server (Mac mini) after helper fallback.";
    }
  }
  return "";
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
        const fallbackReason = latestWorkerFallbackReason();
        const availability = workerAvailabilitySummary();
        const hasRecentHelper = Number(state.workerRecentCount || 0) > 0;
        if (fallbackReason) {
          setGenerateStatus(fallbackReason);
        } else if (Number(state.workerLiveCount || 0) <= 0 && !hasRecentHelper) {
          setGenerateStatus("No active helper was connected, so this job is running on the RADTTS server (Mac mini).");
        } else if (allRecentHelpersBusy()) {
          setGenerateStatus(
            `The local helper stayed busy with another run for ${Math.round(state.workerFallbackTimeoutSeconds || 0)}s, so this job is running on the RADTTS server (Mac mini).`
          );
        } else if (availability) {
          setGenerateStatus(
            `No helper pulled this job within ${Math.round(state.workerFallbackTimeoutSeconds || 0)}s (${availability}). Running on the RADTTS server (Mac mini).`
          );
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
    const hasRecentHelper = Number(state.workerRecentCount || 0) > 0;
    const noWorkersKnown = Number(state.workerLiveCount || 0) <= 0 && !hasRecentHelper;
    if (remaining === null) {
      if (state.lastRunningStatusKey !== "waiting_worker") {
        if (noWorkersKnown) {
          setGenerateStatus("No active helper is connected yet. Waiting for a helper device.");
        } else if (availability) {
          setGenerateStatus(`Waiting up to ${Math.round(state.workerFallbackTimeoutSeconds || 0)}s for a helper to pull this job (${availability}).`);
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
        } else if (allRecentHelpersBusy()) {
          setGenerateStatus(`The local helper is busy with another run. Waiting up to ${remainingLabel} for it to become free.`);
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

function parseIsoDate(isoValue) {
  if (!isoValue) return null;
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function formatOutputDate(isoValue) {
  const date = parseIsoDate(isoValue);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatOutputTime(isoValue) {
  const date = parseIsoDate(isoValue);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date).replace(/\s+/g, "").toLowerCase();
}

function formatDurationSeconds(seconds) {
  const totalSeconds = Math.max(0, Math.round(Number(seconds || 0)));
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function median(values) {
  const numbers = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  if (!numbers.length) return null;
  const mid = Math.floor(numbers.length / 2);
  if (numbers.length % 2 === 1) return numbers[mid];
  return (numbers[mid - 1] + numbers[mid]) / 2;
}

function estimateSentenceCount(text) {
  const normalized = String(text || "").replace(/\r/g, "").trim();
  if (!normalized) return 0;
  const chunks = normalized
    .split(/(?:[.!?]+[\s]+|[.!?]+$|\n+)/)
    .map((part) => part.trim())
    .filter(Boolean);
  return Math.max(1, chunks.length);
}

function buildRunTimingProfile({ text, averageGapSeconds, addFillers, voiceSource }) {
  const normalized = String(text || "").trim();
  const wordCount = normalized ? normalized.split(/\s+/).length : 0;
  const sentenceCount = estimateSentenceCount(text);
  const gapSeconds = Math.max(0.15, Number(averageGapSeconds || 0.8));
  const fillerFactor = addFillers ? 1.04 : 1.0;
  const speechSeconds = wordCount > 0 ? (wordCount / 2.45) * fillerFactor : 0;
  const pauseSeconds = Math.max(0, sentenceCount - 1) * gapSeconds;
  return {
    wordCount,
    sentenceCount,
    estimatedClipSeconds: Math.max(6, speechSeconds + pauseSeconds),
    gapSeconds,
    addFillers: Boolean(addFillers),
    voiceSource: String(voiceSource || "reference"),
  };
}

function normalizeOutputHistoryRow(item) {
  const stageDurationsRaw = item && typeof item.stage_durations_seconds === "object"
    ? item.stage_durations_seconds
    : {};
  const stageDurations = {};
  for (const [stage, value] of Object.entries(stageDurationsRaw || {})) {
    const seconds = toFiniteNumber(value);
    if (seconds !== null && seconds > 0) {
      stageDurations[stage] = seconds;
    }
  }
  return {
    ...item,
    duration_seconds: toFiniteNumber(item?.duration_seconds),
    version_number: toFiniteNumber(item?.version_number),
    stage_durations_seconds: stageDurations,
  };
}

function historicalStageSeconds(stage, profile) {
  const outputs = Array.isArray(state.completedOutputs) ? state.completedOutputs : [];
  if (!outputs.length) return null;

  if (stage === "model_load") {
    return median(outputs.map((item) => toFiniteNumber(item?.stage_durations_seconds?.model_load)).filter((value) => value && value > 0));
  }

  if (!profile || !Number.isFinite(profile.estimatedClipSeconds) || profile.estimatedClipSeconds <= 0) {
    return null;
  }

  const ratios = outputs
    .map((item) => {
      const durationSeconds = toFiniteNumber(item?.duration_seconds);
      const stageSeconds = toFiniteNumber(item?.stage_durations_seconds?.[stage]);
      if (durationSeconds === null || stageSeconds === null || durationSeconds <= 0 || stageSeconds <= 0) {
        return null;
      }
      return stageSeconds / durationSeconds;
    })
    .filter((value) => value !== null && value > 0);
  const ratio = median(ratios);
  return ratio === null ? null : profile.estimatedClipSeconds * ratio;
}

function heuristicStageSeconds(stage, profile) {
  const key = String(stage || "");
  if (!profile) {
    return stageExpectedSeconds[key];
  }

  const clipSeconds = Math.max(6, Number(profile.estimatedClipSeconds || 0));
  const sentenceCount = Math.max(1, Number(profile.sentenceCount || 1));
  switch (key) {
    case "model_load":
      return profile.voiceSource === "builtin" ? 18 : 24;
    case "generation":
      return 18 + (clipSeconds * 2.55) + (sentenceCount * 1.5);
    case "stitching":
      return state.outputFormatRequested === "wav"
        ? Math.max(6, 3 + (clipSeconds * 0.05))
        : Math.max(8, 5 + (clipSeconds * 0.12));
    case "captioning":
      return 10 + (clipSeconds * 0.72);
    default:
      return stageExpectedSeconds[key];
  }
}

function estimatedStageSeconds(stage) {
  const key = String(stage || "");
  const historical = historicalStageSeconds(key, state.currentRunProfile);
  let base = historical;
  if (!Number.isFinite(base) || base <= 0) {
    base = heuristicStageSeconds(key, state.currentRunProfile);
  }
  if (!Number.isFinite(base) || base <= 0) {
    base = stageExpectedSeconds[key];
  }
  if (!Number.isFinite(base) || base <= 0) {
    return 90;
  }
  return base;
}

function formatOutputSummary(item) {
  const parts = [];
  const durationSeconds = toFiniteNumber(item?.duration_seconds);
  if (durationSeconds !== null && durationSeconds > 0) {
    parts.push(formatDurationSeconds(durationSeconds));
  }
  const dateText = formatOutputDate(item?.created_at);
  if (dateText) {
    parts.push(dateText);
  }
  const timeText = formatOutputTime(item?.created_at);
  if (timeText) {
    parts.push(timeText);
  }
  return parts.join(" | ");
}

function formatSampleOptionLabel(sample) {
  const name = sample.source_filename || "sample";
  const duration = Number(sample.duration_seconds || 0);
  const durationLabel = Number.isFinite(duration) && duration > 0
    ? formatDurationSeconds(duration)
    : null;
  const updated = sample.updated_at ? formatIso(sample.updated_at) : "Saved";
  const sourceTag = sample.scope === "library" ? `My library (${sample.project_id || "other project"})` : "Project";
  return durationLabel
    ? `${name} (${durationLabel}) - ${sourceTag} - ${updated}`
    : `${name} - ${sourceTag} - ${updated}`;
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
  if (!scriptVersionSelectNode) return;
  const selectedVersion = String(scriptVersionSelectNode.value || "");
  const hasSelection = Boolean(selectedVersion);
  const selectedIsCurrent = selectedVersion === state.currentScriptVersionId;
  if (restoreScriptVersionBtn) {
    restoreScriptVersionBtn.disabled = !hasSelection || selectedIsCurrent;
  }
  if (deleteScriptVersionBtn) {
    deleteScriptVersionBtn.disabled = !hasSelection;
  }
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

async function handleDeleteScriptVersion() {
  if (!state.activeProjectRef || !scriptVersionSelectNode) return;

  const versionId = String(scriptVersionSelectNode.value || "");
  if (!versionId) return;

  const version = state.scriptVersions.find((row) => String(row.version_id || "") === versionId) || null;
  const versionLabel = formatScriptVersionLabel(version || { version_id: versionId });
  const confirmed = window.confirm(`Delete this saved script version?\n\n${versionLabel}`);
  if (!confirmed) return;

  clearScriptSaveTimer();
  state.pendingScriptSaveSource = null;
  setScriptSaveStatus("Deleting selected version...");
  if (restoreScriptVersionBtn) restoreScriptVersionBtn.disabled = true;
  if (deleteScriptVersionBtn) deleteScriptVersionBtn.disabled = true;

  try {
    const data = await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/script/delete`,
      "POST",
      { version_id: versionId }
    );
    applyScriptPayload(data, { replaceText: true });
    setScriptSaveStatus("Deleted selected script version.");
  } catch (err) {
    setScriptSaveStatus(`Could not delete script version: ${String(err)}`, true);
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
  const chunkMatch = lower.match(/^generation chunk (\d+)\/(\d+)$/);

  if (lower.startsWith("heartbeat:")) {
    const stageMatch = lower.match(/stage=([a-z_]+)/);
    const stage = stageMatch?.[1] || currentStage;
    if (stage === "generation") return "Generating first chunk. This can take a while.";
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

  if (lower.includes("stopped reporting progress")) {
    return "Helper device stalled. Switching to the RADTTS server.";
  }

  if (chunkMatch) {
    return `Generating speech (${chunkMatch[1]}/${chunkMatch[2]} chunks complete)`;
  }

  if (lower === "stitching chunks") {
    return "Combining generated chunks.";
  }

  if (lower === "reference transcription started") {
    return "Analyzing reference sample.";
  }

  if (lower === "reference transcription complete") {
    return "Reference sample analysis complete.";
  }

  if (lower === "preparing reference audio") {
    return "Preparing reference sample.";
  }

  if (lower === "reference sample check complete") {
    return "Reference sample looks usable.";
  }

  if (lower.startsWith("reference validation warning:")) {
    return cleaned.slice("reference validation warning:".length).trim();
  }

  if (lower.includes("cache=warm")) {
    return "Reusing warmed voice model.";
  }

  if (lower.includes("cache=fresh")) {
    return "Voice model loaded.";
  }

  if (lower === "stitching encoding mp3") {
    return "Encoding MP3 output.";
  }

  if (lower === "captioning started") {
    return "Creating transcript.";
  }

  if (lower === "captioning complete") {
    return "Transcript complete.";
  }

  if (lower === "uploading completed audio") {
    return "Uploading completed audio from helper device.";
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
  const total = Math.max(0, Math.ceil(seconds));
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function hasChunkProgressLog(logs) {
  return (Array.isArray(logs) ? logs : []).some((line) => /generation chunk \d+\/\d+/i.test(String(line || "")));
}

function hasWorkerHeartbeatLog(logs) {
  return (Array.isArray(logs) ? logs : []).some((line) => String(line || "").toLowerCase().includes("heartbeat: stage="));
}

function isEarlyGenerationWithoutChunkProgress(logs, stage) {
  return String(stage || "") === "generation" && !hasChunkProgressLog(logs);
}

function isTransientPollError(err) {
  const text = String(err || "").toLowerCase();
  return (
    /\b(502|503|504|524)\b/.test(text) ||
    text.includes("server returned non-json response") ||
    text.includes("networkerror") ||
    text.includes("failed to fetch") ||
    text.includes("timeout")
  );
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

function describeWorkerAvailability(live, registered, stale, lastSeenAt, recent, lastRecentSeenAt) {
  const liveCount = Math.max(0, Number(live || 0));
  const recentCount = Math.max(liveCount, Number(recent || 0));
  const registeredCount = Math.max(liveCount, Number(registered || 0));
  const staleCount = Math.max(0, Number(stale || Math.max(0, registeredCount - liveCount)));
  const lastSeen = lastSeenAt ? formatIso(lastSeenAt) : "";
  const lastRecentSeen = lastRecentSeenAt ? formatIso(lastRecentSeenAt) : lastSeen;
  if (liveCount > 0) {
    const parts = [`${liveCount} live helper device${liveCount === 1 ? "" : "s"}`];
    if (staleCount > 0) {
      parts.push(`${staleCount} stale registration${staleCount === 1 ? "" : "s"}`);
    } else if (registeredCount > liveCount) {
      parts.push(`${registeredCount - liveCount} stale registration${registeredCount - liveCount === 1 ? "" : "s"}`);
    }
    if (lastSeen) {
      parts.push(`last live helper seen ${lastSeen}`);
    }
    return `${parts.join(", ")}. Jobs will use server fallback if no live helper pulls the job in time.`;
  }
  if (recentCount > 0) {
    const parts = [`${recentCount} recently seen helper device${recentCount === 1 ? "" : "s"}`, "0 live right now"];
    if (staleCount > 0) {
      parts.push(`${staleCount} stale registration${staleCount === 1 ? "" : "s"}`);
    }
    if (lastRecentSeen) {
      parts.push(`last helper seen ${lastRecentSeen}`);
    }
    return `${parts.join(", ")}. Jobs will wait longer for a recently seen helper before server fallback.`;
  }
  if (registeredCount > 0) {
    return `${registeredCount} helper registration${registeredCount === 1 ? "" : "s"}, 0 live. Jobs will use server fallback when needed.`;
  }
  return "No helper app connected yet. Jobs will use server fallback when needed.";
}

function helperBusyCount() {
  return Math.max(0, Number(state.workerRunningJobCount || 0));
}

function allRecentHelpersBusy() {
  const recent = Math.max(0, Number(state.workerRecentCount || 0));
  return recent > 0 && helperBusyCount() >= recent;
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
    const live = Math.max(0, Number(data.worker_live_count || online));
    const recent = Math.max(live, Number(data.worker_recent_count || live));
    const registered = Math.max(live, Number(data.worker_registered_count || total));
    const stale = Math.max(0, Number(data.worker_stale_count || Math.max(0, registered - live)));
    const lastSeenAt = String(data.worker_last_live_seen_at || "").trim() || null;
    const lastRecentSeenAt = String(data.worker_last_recent_seen_at || "").trim() || lastSeenAt;
    state.workerLiveCount = live;
    state.workerRecentCount = recent;
    state.workerRegisteredCount = registered;
    state.workerStaleCount = stale;
    state.workerLastLiveSeenAt = lastSeenAt;
    state.workerLastRecentSeenAt = lastRecentSeenAt;
    state.workerOnlineCount = online;
    state.workerTotalCount = total;
    state.workerRunningJobCount = Math.max(0, Number(data.worker_running_job_count || 0));
    state.workerQueuedJobCount = Math.max(0, Number(data.worker_queued_job_count || 0));
    state.workerOnlineWindowSeconds = Math.max(0, Number(data.worker_online_window_seconds || 0));
    state.workerRecentWindowSeconds = Math.max(0, Number(data.worker_recent_window_seconds || 0));

    const detail = describeWorkerAvailability(live, registered, stale, lastSeenAt, recent, lastRecentSeenAt);
    if (live > 0) {
      setWorkerStatusUi("online", detail);
    } else {
      setWorkerStatusUi("offline", detail);
    }
    if (workerSetupBtn) workerSetupBtn.hidden = false;
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
    state.workerSetupWindowsUrl ||
    state.workerSetupMacosUrl ||
    state.workerSetupMacosCommand ||
    state.workerSetupLinuxCommand
  ) {
    if (workerSetupLinksNode) workerSetupLinksNode.hidden = false;
    setWorkerSetupModalStatus("Setup options are ready. Install once on each helper computer.");
    return;
  }
  if (workerSetupBtn) workerSetupBtn.disabled = true;
  setWorkerSetupModalStatus("Generating secure setup options...");
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
    setWorkerSetupModalStatus("Setup options are ready. Install once on each helper computer.");
  } catch (err) {
    setWorkerSetupModalStatus(`Could not generate setup options: ${String(err)}`, true);
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

async function measureAudioDuration(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      const duration = Number(audio.duration || 0);
      URL.revokeObjectURL(url);
      if (!Number.isFinite(duration) || duration <= 0) {
        reject(new Error("Could not read audio duration"));
        return;
      }
      resolve(duration);
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read audio metadata"));
    };
    audio.src = url;
  });
}

function encodeWavFromFloat32(samples, sampleRate) {
  const frameCount = samples.length;
  const buffer = new ArrayBuffer(44 + frameCount * 2);
  const view = new DataView(buffer);

  function writeString(offset, value) {
    for (let idx = 0; idx < value.length; idx += 1) {
      view.setUint8(offset + idx, value.charCodeAt(idx));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + frameCount * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, frameCount * 2, true);

  let offset = 44;
  for (let idx = 0; idx < frameCount; idx += 1) {
    const value = Math.max(-1, Math.min(1, samples[idx]));
    view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

async function trimAudioFile(file, startSeconds, endSeconds) {
  const buffer = await file.arrayBuffer();
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error("Audio trimming is not supported in this browser.");
  }

  const audioContext = new AudioContextClass();
  try {
    const audioBuffer = await audioContext.decodeAudioData(buffer.slice(0));
    const sampleRate = audioBuffer.sampleRate;
    const startFrame = Math.max(0, Math.floor(startSeconds * sampleRate));
    const endFrame = Math.min(audioBuffer.length, Math.ceil(endSeconds * sampleRate));
    if (endFrame <= startFrame) {
      throw new Error("Invalid trim range.");
    }

    const merged = new Float32Array(endFrame - startFrame);
    for (let channel = 0; channel < audioBuffer.numberOfChannels; channel += 1) {
      const channelData = audioBuffer.getChannelData(channel).subarray(startFrame, endFrame);
      for (let idx = 0; idx < channelData.length; idx += 1) {
        merged[idx] += channelData[idx] / audioBuffer.numberOfChannels;
      }
    }

    const wavBlob = encodeWavFromFloat32(merged, sampleRate);
    const baseName = file.name.replace(/\.[^.]+$/, "") || "reference";
    return new File([wavBlob], `${baseName}-trimmed.wav`, { type: "audio/wav" });
  } finally {
    await audioContext.close();
  }
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
    if (!state.canManageActiveProject) closeShareProjectModal();
  } catch {
    state.canManageActiveProject = false;
    shareProjectBtn.hidden = true;
    closeShareProjectModal();
  }
}

function applyActiveProject(projectRef, projectLabel = projectRef) {
  state.activeProjectRef = projectRef;
  state.activeProjectLabel = projectLabel;
  state.canManageActiveProject = false;
  state.completedOutputs = [];
  state.voiceSource = "reference";
  state.selectedAudioHash = null;
  state.referenceSamples = [];
  state.builtinVoices = [];
  state.selectedBuiltInSpeaker = "";
  clearBuiltinVoicePreview();
  setVoiceSourceUi("reference");
  clearReferencePreview();
  setSelectedAudioFile(null);
  if (shareProjectBtn) shareProjectBtn.hidden = true;
  if (savedSampleSelectNode) savedSampleSelectNode.innerHTML = '<option value="">Loading saved samples...</option>';
  setSavedSampleStatus("Loading saved samples...");
  if (activeProjectLabelNode) activeProjectLabelNode.textContent = projectLabel;
  setWorkspaceVisible(true);
  setGenerateStatus("");
  resetProgressUi();
  clearJobTracking();
  resetScriptEditorState();
  resetProjectSettingsControls();
  setGenerateEnabled(true);
  setCancelVisible(false);
  clearWorkerSetupLinks();
  void loadOutputs();
  void restoreProjectSettings(projectRef);
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
  updateSavedSampleDeleteButtonState();
  if (!audioFileNameNode || !audioDropzoneTitleNode) return;

  if (!state.selectedAudioFile) {
    audioDropzoneTitleNode.textContent = "Drop audio here or click to choose";
    audioFileNameNode.textContent = "No file selected.";
    clearReferencePreview();
    return;
  }

  audioDropzoneTitleNode.textContent = "Voice sample selected";
  const mb = (state.selectedAudioFile.size / (1024 * 1024)).toFixed(2);
  audioFileNameNode.textContent = `${state.selectedAudioFile.name} (${mb} MB)`;
  showReferencePreviewFromFile(state.selectedAudioFile);
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

function updateSavedSampleDeleteButtonState() {
  if (!deleteSavedSampleBtn || !savedSampleSelectNode) return;
  deleteSavedSampleBtn.disabled = !String(savedSampleSelectNode.value || "");
}

function applySavedSampleSelection(audioHash, { persist = false } = {}) {
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
    const duration = Number(sample.duration_seconds || 0);
    const durationHint = Number.isFinite(duration) && duration > 0 ? `, ${formatDurationSeconds(duration)}` : "";
    audioFileNameNode.textContent = `${sample.source_filename || "saved-sample"} (${stamped}${projectHint}${durationHint})`;
  }
  const ownerHint = sample.owner_label ? ` by ${sample.owner_label}` : "";
  const duration = Number(sample.duration_seconds || 0);
  const durationHint = Number.isFinite(duration) && duration > 0 ? `, ${formatDurationSeconds(duration)}` : "";
  setSavedSampleStatus(
    `Using saved sample: ${sample.source_filename || sample.audio_hash.slice(0, 8)}${durationHint}${ownerHint}.`
  );
  showReferencePreviewFromUrl(sample.artifact_url || "");
  updateSavedSampleDeleteButtonState();
  if (persist) {
    queueProjectSettingsSave();
  }
}

async function loadReferenceSamples(preferredHash = null) {
  const projectId = state.activeProjectRef;
  if (!projectId || !savedSampleSelectNode) return;

  savedSampleSelectNode.innerHTML = '<option value="">Loading saved samples...</option>';
  savedSampleSelectNode.disabled = true;
  if (refreshSamplesBtn) refreshSamplesBtn.disabled = true;
  if (deleteSavedSampleBtn) deleteSavedSampleBtn.disabled = true;

  try {
    const data = await requestJSON(`/projects/${encodeURIComponent(projectId)}/reference-audio`, "GET");
    const samples = Array.isArray(data.samples) ? data.samples : [];
    state.referenceSamples = samples;

    savedSampleSelectNode.innerHTML = "";
    if (!samples.length) {
      savedSampleSelectNode.innerHTML = '<option value="">No saved samples yet</option>';
      savedSampleSelectNode.value = "";
      setSavedSampleStatus("No saved samples in this project yet.");
      updateSavedSampleDeleteButtonState();
      return;
    }

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose saved sample";
    savedSampleSelectNode.appendChild(placeholder);

    for (const sample of samples) {
      const option = document.createElement("option");
      option.value = sample.audio_hash;
      option.textContent = formatSampleOptionLabel(sample);
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
    updateSavedSampleDeleteButtonState();
  } catch (err) {
    savedSampleSelectNode.innerHTML = '<option value="">Unable to load samples</option>';
    setSavedSampleStatus(`Could not load saved samples: ${String(err)}`, true);
  } finally {
    savedSampleSelectNode.disabled = false;
    if (refreshSamplesBtn) refreshSamplesBtn.disabled = false;
    updateSavedSampleDeleteButtonState();
  }
}

async function handleDeleteSavedSample() {
  if (!state.activeProjectRef || !savedSampleSelectNode) return;

  const selectedHash = String(savedSampleSelectNode.value || "");
  if (!selectedHash) return;
  const sample = findReferenceSampleByHash(selectedHash);
  if (!sample) {
    setSavedSampleStatus("Saved sample not found. Refresh and try again.", true);
    updateSavedSampleDeleteButtonState();
    return;
  }

  const sampleLabel = sample.source_filename || sample.audio_hash?.slice(0, 8) || "selected sample";
  const confirmed = window.confirm(`Delete this saved sample?\n\n${sampleLabel}`);
  if (!confirmed) return;

  if (deleteSavedSampleBtn) deleteSavedSampleBtn.disabled = true;
  setSavedSampleStatus("Deleting saved sample...");

  try {
    await requestJSON(
      `/projects/${encodeURIComponent(state.activeProjectRef)}/reference-audio/delete`,
      "POST",
      {
        audio_hash: sample.audio_hash,
        source_project_id: sample.project_id || state.activeProjectRef,
      }
    );

    if (state.selectedAudioHash === sample.audio_hash) {
      state.selectedAudioHash = null;
      if (!state.selectedAudioFile) {
        if (audioDropzoneTitleNode) {
          audioDropzoneTitleNode.textContent = "Drop audio here or click to choose";
        }
        if (audioFileNameNode) {
          audioFileNameNode.textContent = "No file selected.";
        }
        clearReferencePreview();
      }
    }

    await loadReferenceSamples();
    queueProjectSettingsSave();
    setSavedSampleStatus("Saved sample deleted.");
  } catch (err) {
    setSavedSampleStatus(`Could not delete saved sample: ${String(err)}`, true);
    updateSavedSampleDeleteButtonState();
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
    queueProjectSettingsSave();
  } catch (err) {
    setRecordStatus(`${originLabel} selected, but could not be saved yet: ${String(err)}`, true);
    setSavedSampleStatus(`Saved sample refresh failed: ${String(err)}`, true);
  }
}

function clearReferencePreview() {
  if (referencePreviewLabelNode) {
    referencePreviewLabelNode.hidden = true;
  }
  if (!recordPreviewNode) return;
  recordPreviewNode.hidden = true;
  recordPreviewNode.pause();
  recordPreviewNode.removeAttribute("src");
  recordPreviewNode.load();
  if (state.referencePreviewObjectUrl) {
    URL.revokeObjectURL(state.referencePreviewObjectUrl);
    state.referencePreviewObjectUrl = null;
  }
}

function showReferencePreviewFromUrl(url) {
  if (referencePreviewLabelNode) {
    referencePreviewLabelNode.hidden = false;
  }
  if (!recordPreviewNode) return;
  clearReferencePreview();
  if (!url) return;
  if (referencePreviewLabelNode) {
    referencePreviewLabelNode.hidden = false;
  }
  recordPreviewNode.src = url;
  recordPreviewNode.hidden = false;
}

function showReferencePreviewFromFile(file) {
  if (referencePreviewLabelNode) {
    referencePreviewLabelNode.hidden = false;
  }
  if (!recordPreviewNode) return;
  clearReferencePreview();
  if (!file) return;
  if (referencePreviewLabelNode) {
    referencePreviewLabelNode.hidden = false;
  }
  state.referencePreviewObjectUrl = URL.createObjectURL(file);
  recordPreviewNode.src = state.referencePreviewObjectUrl;
  recordPreviewNode.hidden = false;
}

function clearBuiltinVoicePreview() {
  if (builtinVoicePreviewNode) {
    builtinVoicePreviewNode.pause();
    builtinVoicePreviewNode.hidden = true;
    builtinVoicePreviewNode.removeAttribute("src");
    builtinVoicePreviewNode.load();
  }
  if (state.builtinVoicePreviewUrl) {
    URL.revokeObjectURL(state.builtinVoicePreviewUrl);
    state.builtinVoicePreviewUrl = null;
  }
}

function getSelectedBuiltInVoice() {
  return state.builtinVoices.find((voice) => String(voice.id || "") === String(state.selectedBuiltInSpeaker || "")) || null;
}

function inferBuiltInTextLanguage(text) {
  const sample = String(text || "").trim();
  if (!sample) return "English";
  if (/[\u4E00-\u9FFF]/.test(sample)) return "Chinese";
  if (/[\u3040-\u30FF]/.test(sample)) return "Japanese";
  if (/[\uAC00-\uD7AF]/.test(sample)) return "Korean";
  return "English";
}

function builtinVoiceSelectionMessage(voice) {
  if (!voice) {
    return "Choose a built-in Qwen voice, then preview or generate.";
  }
  const nativeLanguage = String(voice.native_language || "").trim();
  if (!nativeLanguage) {
    return `Selected built-in voice: ${state.selectedBuiltInSpeaker}.`;
  }
  const scriptLanguage = inferBuiltInTextLanguage(scriptTextNode?.value || "");
  if (scriptLanguage !== nativeLanguage) {
    return `${voice.label || voice.id} is native to ${nativeLanguage}. Your script looks ${scriptLanguage}; for best English results, Ryan or Aiden are safer.`;
  }
  return `Selected built-in voice: ${voice.label || voice.id} (${nativeLanguage}-native).`;
}

async function loadBuiltinVoices() {
  if (!builtinVoiceSelectNode) return;
  builtinVoiceSelectNode.innerHTML = '<option value="">Loading built-in voices...</option>';
  builtinVoiceSelectNode.disabled = true;
  if (previewBuiltinVoiceBtn) {
    previewBuiltinVoiceBtn.disabled = true;
  }
  try {
    const quality = qualityNode?.value === "high" ? "high" : "normal";
    const data = await requestJSON(`/voices/builtin?quality=${encodeURIComponent(quality)}`, "GET");
    const voices = Array.isArray(data.voices) ? data.voices : [];
    state.builtinVoices = voices;

    builtinVoiceSelectNode.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose built-in voice";
    builtinVoiceSelectNode.appendChild(placeholder);

    for (const voice of voices) {
      const option = document.createElement("option");
      option.value = String(voice.id || "");
      option.textContent = String(voice.label || voice.id || "");
      builtinVoiceSelectNode.appendChild(option);
    }

    builtinVoiceSelectNode.value = state.selectedBuiltInSpeaker || "";
    setBuiltinVoiceStatus(builtinVoiceSelectionMessage(getSelectedBuiltInVoice()));
  } catch (err) {
    builtinVoiceSelectNode.innerHTML = '<option value="">Unable to load built-in voices</option>';
    setBuiltinVoiceStatus(`Could not load built-in voices: ${String(err)}`, true);
  } finally {
    builtinVoiceSelectNode.disabled = false;
    if (previewBuiltinVoiceBtn) {
      previewBuiltinVoiceBtn.disabled = false;
    }
  }
}

function closeReferenceTrimModal() {
  if (state.referenceTrimStopTimer) {
    clearTimeout(state.referenceTrimStopTimer);
    state.referenceTrimStopTimer = null;
  }
  if (referenceTrimPreviewNode) {
    referenceTrimPreviewNode.pause();
  }
  if (state.referenceTrimPreviewObjectUrl) {
    URL.revokeObjectURL(state.referenceTrimPreviewObjectUrl);
    state.referenceTrimPreviewObjectUrl = null;
  }
  if (referenceTrimModalNode) {
    referenceTrimModalNode.hidden = true;
  }
  syncModalOpenState();
}

function updateReferenceTrimSelectionUi() {
  const maxSeconds = Number(state.pendingReferenceDurationSeconds || 0);
  if (!referenceTrimStartNode || !referenceTrimEndNode) return;
  let start = Math.max(0, Number(referenceTrimStartNode.value || 0));
  let end = Math.max(start, Number(referenceTrimEndNode.value || 0));

  if (end - start > 30) {
    end = Math.min(maxSeconds, start + 30);
    referenceTrimEndNode.value = String(end);
  }
  if (end <= start) {
    end = Math.min(maxSeconds, start + 0.1);
    referenceTrimEndNode.value = String(end);
  }

  if (referenceTrimStartValueNode) {
    referenceTrimStartValueNode.textContent = formatDurationSeconds(start);
  }
  if (referenceTrimEndValueNode) {
    referenceTrimEndValueNode.textContent = formatDurationSeconds(end);
  }
  if (referenceTrimSelectionSummaryNode) {
    referenceTrimSelectionSummaryNode.textContent = `Selected clip length: ${formatDurationSeconds(end - start)}`;
  }
}

function openReferenceTrimModal(file, durationSeconds, originLabel) {
  state.pendingReferenceFile = file;
  state.pendingReferenceOriginLabel = originLabel;
  state.pendingReferenceDurationSeconds = durationSeconds;

  const maxSeconds = Math.max(0.1, Number(durationSeconds || 0));
  const defaultEnd = Math.min(30, maxSeconds);

  if (referenceTrimSourceNameNode) {
    referenceTrimSourceNameNode.textContent = file?.name || "Selected sample";
  }
  if (referenceTrimSourceDurationNode) {
    referenceTrimSourceDurationNode.textContent = `${formatDurationSeconds(maxSeconds)} total`;
  }
  if (referenceTrimModalStatusNode) {
    referenceTrimModalStatusNode.textContent = `${originLabel} is ${formatDurationSeconds(maxSeconds)} long. Choose up to 30 seconds to use as the reference sample.`;
    referenceTrimModalStatusNode.style.color = "#555";
  }
  if (referenceTrimStartNode) {
    referenceTrimStartNode.min = "0";
    referenceTrimStartNode.max = String(maxSeconds);
    referenceTrimStartNode.value = "0";
  }
  if (referenceTrimEndNode) {
    referenceTrimEndNode.min = "0";
    referenceTrimEndNode.max = String(maxSeconds);
    referenceTrimEndNode.value = String(defaultEnd);
  }

  if (state.referenceTrimPreviewObjectUrl) {
    URL.revokeObjectURL(state.referenceTrimPreviewObjectUrl);
    state.referenceTrimPreviewObjectUrl = null;
  }
  if (referenceTrimPreviewNode) {
    state.referenceTrimPreviewObjectUrl = URL.createObjectURL(file);
    referenceTrimPreviewNode.src = state.referenceTrimPreviewObjectUrl;
  }
  updateReferenceTrimSelectionUi();
  if (referenceTrimModalNode) {
    referenceTrimModalNode.hidden = false;
  }
  syncModalOpenState();
}

async function handleSelectedReferenceFile(file, originLabel) {
  setSelectedAudioFile(file);
  const durationSeconds = await measureAudioDuration(file);
  if (durationSeconds > 30) {
    setRecordStatus(
      `${originLabel} is ${formatDurationSeconds(durationSeconds)} long. Trim it to 30 seconds or less for faster cloning.`
    );
    openReferenceTrimModal(file, durationSeconds, originLabel);
    return;
  }
  setRecordStatus(`${originLabel} ready. Duration: ${formatDurationSeconds(durationSeconds)}.`);
  await attachAudioFileToProject(file, originLabel);
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
  if (recentProjectListNode) {
    recentProjectListNode.innerHTML = '<p class="recent-project-empty">Loading recent projects...</p>';
  }

  try {
    const data = await requestJSON("/projects", "GET");
    const projects = Array.isArray(data.projects) ? data.projects : [];
    existingProjectSelectNode.innerHTML = "";
    renderRecentProjects(projects);

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
    if (recentProjectListNode) {
      recentProjectListNode.innerHTML = '<p class="recent-project-empty">Could not load recent projects.</p>';
    }
    setGatewayStatus(`Could not load projects: ${String(err)}`, true);
  }
}

function openProject(projectRef, projectLabel = projectRef) {
  if (!projectRef) return;
  if (existingProjectSelectNode) {
    existingProjectSelectNode.value = projectRef;
  }
  applyActiveProject(projectRef, projectLabel);
  setGatewayStatus("");
}

function renderRecentProjects(projects) {
  if (!recentProjectListNode) return;
  const items = Array.isArray(projects) ? projects.slice(0, 5) : [];

  if (!items.length) {
    recentProjectListNode.innerHTML = '<p class="recent-project-empty">No recent projects yet.</p>';
    return;
  }

  recentProjectListNode.innerHTML = "";

  for (const project of items) {
    const projectRef = String(project.project_ref || project.project_id || "");
    const projectLabel = String(project.project_id || projectRef);
    const shared = Boolean(project.shared);
    const ownerLabel = String(project.owner_label || "").trim();
    const updatedAt = String(project.updated_at || "").trim();

    const button = document.createElement("button");
    button.type = "button";
    button.className = "recent-project-btn";
    button.dataset.projectRef = projectRef;
    button.dataset.projectLabel = projectLabel;

    const title = document.createElement("span");
    title.className = "recent-project-title";
    title.textContent = projectLabel;
    button.appendChild(title);

    const metaParts = [];
    if (shared) {
      metaParts.push(`shared${ownerLabel ? ` from ${ownerLabel}` : ""}`);
    }
    if (updatedAt) {
      metaParts.push(`updated ${formatIso(updatedAt)}`);
    }
    if (metaParts.length) {
      const meta = document.createElement("span");
      meta.className = "recent-project-meta";
      meta.textContent = metaParts.join(" | ");
      button.appendChild(meta);
    }

    button.addEventListener("click", () => {
      openProject(projectRef, projectLabel);
    });
    recentProjectListNode.appendChild(button);
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
    const versionNumber = toFiniteNumber(item.version_number);
    const summaryLabel = formatOutputSummary(item);
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
          <div class="output-meta-main">
            <span class="output-name">${escapeHtml(item.output_name || "audio output")}</span>
            ${versionNumber !== null && versionNumber > 0 ? `<span class="output-version-badge">Version ${escapeHtml(versionNumber)}</span>` : ""}
          </div>
          ${summaryLabel ? `<span class="output-summary">${escapeHtml(summaryLabel)}</span>` : ""}
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
    state.completedOutputs = outputs.map((item) => normalizeOutputHistoryRow(item));
    renderOutputs(outputs);
  } catch (err) {
    state.completedOutputs = [];
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
      const etaProgress = state.actualProgress > 0 ? state.actualProgress : clamped;
      const eta = smoothEtaDisplay(estimateEtaSeconds(etaProgress, stage), stage);
      progressEtaNode.textContent = eta === null
        ? "Time left to process: estimating..."
        : `Time left to process: ${formatEta(eta)}`;
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
  const expectedSec = expectedStageSecondsForCurrentMode(stage);
  const stageStart = state.stageStartedAtMs || Date.now();
  const elapsedSec = Math.max(0, (Date.now() - stageStart) / 1000);
  const ratio = Math.min(1, elapsedSec / expectedSec);
  const synthetic = floor + (cap - floor) * ratio;
  let target = Math.max(state.actualProgress, synthetic);

  if (state.actualProgress > 0 && ["model_load", "generation", "stitching", "captioning"].includes(stage)) {
    const maxLead = stage === "generation" ? 4 : 3;
    target = Math.min(target, state.actualProgress + maxLead);
  }

  return Math.max(state.actualProgress, Math.min(cap, target));
}

function progressAnimationTick() {
  const target = calculateSyntheticTarget();
  const delta = target - state.displayProgress;

  if (delta > 0) {
    const stage = state.currentStage || "queued";
    let maxRisePerTick = 0.32;
    if (stage === "queued" || stage === "queued_remote") {
      maxRisePerTick = 0.22;
    } else if (stage === "generation") {
      maxRisePerTick = 0.28;
    }
    if (state.computeMode === "waiting_worker") {
      maxRisePerTick = Math.min(maxRisePerTick, 0.2);
    }
    state.displayProgress += Math.min(delta, maxRisePerTick);
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
  const stageChanged = state.currentStage !== stage;

  state.currentStatus = status;

  if (!state.jobStartedAtMs) {
    state.jobStartedAtMs = Date.now();
  }

  if (stageChanged) {
    state.currentStage = stage;
    state.stageStartedAtMs = Date.now();
    state.stageProgressSamples = [];
  }

  let progressIncreased = false;
  if (Number.isFinite(Number(job.progress))) {
    const nextProgress = Math.max(state.actualProgress, Number(job.progress) * 100);
    progressIncreased = nextProgress > state.actualProgress + 0.05;
    state.actualProgress = nextProgress;
  }

  if (stageChanged || progressIncreased) {
    state.stageProgressSamples.push({
      progress: Math.max(0, Math.min(100, state.actualProgress)),
      atMs: Date.now(),
    });
    if (state.stageProgressSamples.length > 8) {
      state.stageProgressSamples.shift();
    }
  }

  const logs = Array.isArray(job.logs) ? job.logs : [];
  state.currentJobLogs = logs;
  state.pollFailureCount = 0;
  state.pollFailureStartedAtMs = null;
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

  if (isEarlyGenerationWithoutChunkProgress(logs, stage) && !hasChunkProgressLog(logs)) {
    state.latestDetail = "Generating first chunk. This can take a while.";
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
      setGenerateStatus(`Generation failed: ${formatGenerationErrorMessage(data.error || "Unknown error")}`, true);
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
    if (state.activeJobId && state.currentStatus === "running" && isTransientPollError(err)) {
      state.pollFailureCount += 1;
      if (!state.pollFailureStartedAtMs) {
        state.pollFailureStartedAtMs = Date.now();
      }
      const failureAgeMs = Date.now() - state.pollFailureStartedAtMs;
      if (state.pollFailureCount < 6 && failureAgeMs < 60000) {
        setGenerateStatus("Progress check is timing out. Retrying automatically...", true);
        return;
      }
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
  state.generateTranscriptRequested = Boolean(options.generateTranscript);
  state.outputFormatRequested = String(options.outputFormat || "mp3").toLowerCase();
  state.stageProgressSamples = [{ progress: 0, atMs: state.stageStartedAtMs }];
  state.currentRunProfile = options.runProfile || null;

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
    const averageGapSeconds = Number(gapSliderNode?.value || 0.8);
    const addUms = Boolean(umsToggleNode?.checked);
    const addAhs = Boolean(ahsToggleNode?.checked);
    const addFillers = addUms || addAhs;

    if (state.voiceSource === "reference" && !state.selectedAudioFile && !state.selectedAudioHash) {
      throw new Error("Please select, record, or choose a saved audio sample.");
    }
    if (state.voiceSource === "builtin" && !state.selectedBuiltInSpeaker) {
      throw new Error("Please choose a built-in Qwen voice.");
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
      voice_source: state.voiceSource,
      quality: qualityNode?.value || "normal",
      add_ums: addUms,
      add_ahs: addAhs,
      average_gap_seconds: averageGapSeconds,
      output_format: outputFormatNode?.value || "mp3",
      voice_clone_authorized: true,
      generate_transcript: Boolean(transcriptToggleNode?.checked),
    };
    const runProfile = buildRunTimingProfile({
      text: scriptText,
      averageGapSeconds,
      addFillers,
      voiceSource: state.voiceSource,
    });

    if (state.voiceSource === "builtin") {
      payload.built_in_speaker = state.selectedBuiltInSpeaker;
    } else if (state.selectedAudioHash) {
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
    const workerLiveCount = Number.isFinite(Number(data.worker_live_count))
      ? Number(data.worker_live_count)
      : workerOnlineCount;
    const workerRecentCount = Number.isFinite(Number(data.worker_recent_count))
      ? Math.max(Number(data.worker_recent_count), Number(workerLiveCount || 0))
      : workerLiveCount;
    const workerRegisteredCount = Number.isFinite(Number(data.worker_registered_count))
      ? Number(data.worker_registered_count)
      : workerTotalCount;
    const workerStaleCount = Number.isFinite(Number(data.worker_stale_count))
      ? Number(data.worker_stale_count)
      : (
        Number.isFinite(workerRegisteredCount) && Number.isFinite(workerLiveCount)
          ? Math.max(0, Number(workerRegisteredCount) - Number(workerLiveCount))
          : null
      );
    const workerLastLiveSeenAt = String(data.worker_last_live_seen_at || "").trim() || null;
    const workerLastRecentSeenAt = String(data.worker_last_recent_seen_at || "").trim() || workerLastLiveSeenAt;
    const workerOnlineWindowSeconds = Number.isFinite(Number(data.worker_online_window_seconds))
      ? Number(data.worker_online_window_seconds)
      : null;
    const workerRecentWindowSeconds = Number.isFinite(Number(data.worker_recent_window_seconds))
      ? Number(data.worker_recent_window_seconds)
      : null;

    state.workerLiveCount = workerLiveCount;
    state.workerRecentCount = workerRecentCount;
    state.workerRegisteredCount = workerRegisteredCount;
    state.workerStaleCount = workerStaleCount;
    state.workerLastLiveSeenAt = workerLastLiveSeenAt;
    state.workerLastRecentSeenAt = workerLastRecentSeenAt;
    state.workerOnlineCount = workerOnlineCount;
    state.workerTotalCount = workerTotalCount;
    state.workerRunningJobCount = Math.max(0, Number(data.worker_running_job_count || 0));
    state.workerQueuedJobCount = Math.max(0, Number(data.worker_queued_job_count || 0));
    state.workerOnlineWindowSeconds = workerOnlineWindowSeconds;
    state.workerRecentWindowSeconds = workerRecentWindowSeconds;

    if (workerMode) {
      const hasRecentHelper = workerRecentCount !== null && workerRecentCount > 0;
      if (workerLiveCount !== null && workerLiveCount <= 0 && !hasRecentHelper) {
        setGenerateStatus("No active helper is connected right now. Waiting for helper assignment...");
      } else if ((workerRecentCount !== null && workerRecentCount > 0) && Math.max(0, Number(data.worker_running_job_count || 0)) >= workerRecentCount) {
        setGenerateStatus(
          `The local helper is busy with another run. Waiting up to ${Math.round(fallbackTimeout)}s for it to become free.`
        );
      } else {
        const availability = workerAvailabilitySummary();
        const helperLabel = workerLiveCount !== null && workerLiveCount > 0 ? "live helper" : "helper";
        setGenerateStatus(
          availability
            ? `Job queued for helper assignment. Waiting up to ${Math.round(fallbackTimeout)}s for a ${helperLabel} to pull it (${availability}).`
            : `Job queued for helper assignment. Waiting up to ${Math.round(fallbackTimeout)}s for a ${helperLabel} to pull it.`
        );
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
      generateTranscript: payload.generate_transcript,
      outputFormat: payload.output_format,
      runProfile,
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
      openProject(projectRef, projectLabel);
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
      state.builtinVoices = [];
      state.selectedBuiltInSpeaker = "";
      setSelectedAudioFile(null);
      clearBuiltinVoicePreview();
      setVoiceSourceUi("reference");
      clearReferencePreview();
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
  if (shareProjectBtn) {
    shareProjectBtn.addEventListener("click", () => {
      if (!state.activeProjectRef) return;
      if (!state.canManageActiveProject) {
        setGenerateStatus("Only project owners can share this project.", true);
        return;
      }
      openShareProjectModal();
    });
  }

  if (shareProjectCloseBtn) {
    shareProjectCloseBtn.addEventListener("click", () => {
      closeShareProjectModal();
    });
  }

  if (shareProjectModalNode) {
    shareProjectModalNode.addEventListener("click", (event) => {
      if (event.target === shareProjectModalNode) {
        closeShareProjectModal();
      }
    });
  }

  if (shareProjectGrantBtn) {
    shareProjectGrantBtn.addEventListener("click", () => {
      void handleShareProjectGrant();
    });
  }

  if (shareProjectMembersNode) {
    shareProjectMembersNode.addEventListener("click", (event) => {
      const removeButton = event.target instanceof Element
        ? event.target.closest(".share-project-remove-btn")
        : null;
      if (!(removeButton instanceof HTMLButtonElement)) return;
      const email = cleanOptional(removeButton.dataset.email)?.toLowerCase();
      if (!email) return;
      void handleShareProjectRemove(email);
    });
  }
}

function bindHelpModal() {
  if (helpBtn) {
    helpBtn.addEventListener("click", () => {
      openHelpModal();
    });
  }

  if (helpModalCloseBtn) {
    helpModalCloseBtn.addEventListener("click", () => {
      closeHelpModal();
    });
  }

  if (helpModalNode) {
    helpModalNode.addEventListener("click", (event) => {
      if (event.target === helpModalNode) {
        closeHelpModal();
      }
    });
    helpModalNode.addEventListener("keydown", handleHelpModalKeydown);
  }

  if (helpModalTabsNode) {
    helpModalTabsNode.addEventListener("click", (event) => {
      const target = event.target instanceof HTMLElement ? event.target.closest("[data-help-tab]") : null;
      if (!(target instanceof HTMLButtonElement)) return;
      selectHelpTab(target.dataset.helpTab, { focusTab: true });
    });

    helpModalTabsNode.addEventListener("keydown", handleHelpTabKeydown);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!helpModalNode || helpModalNode.hidden) return;
    closeHelpModal();
  });
}

function bindWorkerStatus() {
  if (workerRefreshBtn) {
    workerRefreshBtn.addEventListener("click", () => {
      void refreshWorkerStatus({ announceErrors: true });
    });
  }

  if (workerSetupCloseBtn) {
    workerSetupCloseBtn.addEventListener("click", () => {
      closeWorkerSetupModal();
    });
  }

  if (workerSetupModalNode) {
    workerSetupModalNode.addEventListener("click", (event) => {
      if (event.target === workerSetupModalNode) {
        closeWorkerSetupModal();
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!workerSetupModalNode || workerSetupModalNode.hidden) return;
    closeWorkerSetupModal();
  });

  if (workerSetupBtn) {
    workerSetupBtn.addEventListener("click", () => {
      openWorkerSetupModal();
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

function bindReferenceTrimModal() {
  if (referenceTrimCloseBtn) {
    referenceTrimCloseBtn.addEventListener("click", () => {
      closeReferenceTrimModal();
    });
  }

  if (referenceTrimModalNode) {
    referenceTrimModalNode.addEventListener("click", (event) => {
      if (event.target === referenceTrimModalNode) {
        closeReferenceTrimModal();
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!referenceTrimModalNode || referenceTrimModalNode.hidden) return;
    closeReferenceTrimModal();
  });

  const syncFromStart = () => {
    if (!referenceTrimStartNode || !referenceTrimEndNode) return;
    const start = Number(referenceTrimStartNode.value || 0);
    const currentEnd = Number(referenceTrimEndNode.value || 0);
    if (currentEnd < start) {
      referenceTrimEndNode.value = String(start);
    }
    if (currentEnd - start > 30) {
      referenceTrimEndNode.value = String(start + 30);
    }
    updateReferenceTrimSelectionUi();
  };

  const syncFromEnd = () => {
    if (!referenceTrimStartNode || !referenceTrimEndNode) return;
    const end = Number(referenceTrimEndNode.value || 0);
    const currentStart = Number(referenceTrimStartNode.value || 0);
    if (end < currentStart) {
      referenceTrimStartNode.value = String(Math.max(0, end - 0.1));
    }
    if (end - Number(referenceTrimStartNode.value || 0) > 30) {
      referenceTrimStartNode.value = String(Math.max(0, end - 30));
    }
    updateReferenceTrimSelectionUi();
  };

  if (referenceTrimStartNode) {
    referenceTrimStartNode.addEventListener("input", syncFromStart);
  }
  if (referenceTrimEndNode) {
    referenceTrimEndNode.addEventListener("input", syncFromEnd);
  }

  if (referenceTrimPlayBtn) {
    referenceTrimPlayBtn.addEventListener("click", () => {
      if (!referenceTrimPreviewNode || !referenceTrimStartNode || !referenceTrimEndNode) return;
      const start = Number(referenceTrimStartNode.value || 0);
      const end = Number(referenceTrimEndNode.value || 0);
      if (state.referenceTrimStopTimer) {
        clearTimeout(state.referenceTrimStopTimer);
      }
      referenceTrimPreviewNode.currentTime = start;
      const playPromise = referenceTrimPreviewNode.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(() => {});
      }
      state.referenceTrimStopTimer = setTimeout(() => {
        referenceTrimPreviewNode.pause();
      }, Math.max(0, (end - start) * 1000));
    });
  }

  if (referenceTrimApplyBtn) {
    referenceTrimApplyBtn.addEventListener("click", () => {
      void (async () => {
        if (!state.pendingReferenceFile || !referenceTrimStartNode || !referenceTrimEndNode) return;
        const start = Number(referenceTrimStartNode.value || 0);
        const end = Number(referenceTrimEndNode.value || 0);
        if (referenceTrimApplyBtn) referenceTrimApplyBtn.disabled = true;
        if (referenceTrimModalStatusNode) {
          referenceTrimModalStatusNode.textContent = "Trimming selected audio...";
        }
        try {
          const trimmedFile = await trimAudioFile(state.pendingReferenceFile, start, end);
          closeReferenceTrimModal();
          await handleSelectedReferenceFile(trimmedFile, "Trimmed audio");
        } catch (err) {
          if (referenceTrimModalStatusNode) {
            referenceTrimModalStatusNode.textContent = `Could not trim audio: ${String(err)}`;
            referenceTrimModalStatusNode.style.color = "#a73527";
          }
        } finally {
          if (referenceTrimApplyBtn) referenceTrimApplyBtn.disabled = false;
        }
      })();
    });
  }

  if (referenceTrimSkipBtn) {
    referenceTrimSkipBtn.addEventListener("click", () => {
      void (async () => {
        if (!state.pendingReferenceFile || !state.pendingReferenceOriginLabel) return;
        closeReferenceTrimModal();
        await attachAudioFileToProject(state.pendingReferenceFile, state.pendingReferenceOriginLabel);
        setRecordStatus(
          `${state.pendingReferenceOriginLabel} kept at full length (${formatDurationSeconds(state.pendingReferenceDurationSeconds)}).`
        );
      })();
    });
  }
}

function bindVoiceSource() {
  if (voiceSourceReferenceNode) {
    voiceSourceReferenceNode.addEventListener("change", () => {
      if (!voiceSourceReferenceNode.checked) return;
      setVoiceSourceUi("reference");
      setGenerateStatus("");
      queueProjectSettingsSave();
    });
  }

  if (voiceSourceBuiltinNode) {
    voiceSourceBuiltinNode.addEventListener("change", () => {
      if (!voiceSourceBuiltinNode.checked) return;
      setVoiceSourceUi("builtin");
      setGenerateStatus("");
      queueProjectSettingsSave();
      if (!state.builtinVoices.length) {
        void loadBuiltinVoices();
      }
    });
  }

  if (builtinVoiceSelectNode) {
    builtinVoiceSelectNode.addEventListener("change", () => {
      state.selectedBuiltInSpeaker = builtinVoiceSelectNode.value || "";
      clearBuiltinVoicePreview();
      setBuiltinVoiceStatus(builtinVoiceSelectionMessage(getSelectedBuiltInVoice()));
      queueProjectSettingsSave();
    });
  }

  if (previewBuiltinVoiceBtn) {
    previewBuiltinVoiceBtn.addEventListener("click", () => {
      void (async () => {
        if (!state.selectedBuiltInSpeaker) {
          setBuiltinVoiceStatus("Choose a built-in voice first.", true);
          return;
        }
        const selectedVoice = getSelectedBuiltInVoice();
        if (selectedVoice && selectedVoice.preview_url && builtinVoicePreviewNode) {
          clearBuiltinVoicePreview();
          builtinVoicePreviewNode.src = String(selectedVoice.preview_url);
          builtinVoicePreviewNode.hidden = false;
          try {
            await builtinVoicePreviewNode.play();
          } catch (err) {
            void err;
          }
          setBuiltinVoiceStatus(`Preview ready for ${state.selectedBuiltInSpeaker}.`);
          return;
        }
        previewBuiltinVoiceBtn.disabled = true;
        setBuiltinVoiceStatus(`Generating preview for ${state.selectedBuiltInSpeaker}...`);
        try {
          const quality = qualityNode?.value === "high" ? "high" : "normal";
          const data = await requestJSON("/voices/builtin/preview", "POST", {
            speaker: state.selectedBuiltInSpeaker,
            quality,
          });
          clearBuiltinVoicePreview();
          const bytes = Uint8Array.from(atob(String(data.audio_b64 || "")), (ch) => ch.charCodeAt(0));
          const blob = new Blob([bytes], { type: String(data.content_type || "audio/wav") });
          state.builtinVoicePreviewUrl = URL.createObjectURL(blob);
          if (builtinVoicePreviewNode) {
            builtinVoicePreviewNode.src = state.builtinVoicePreviewUrl;
            builtinVoicePreviewNode.hidden = false;
          }
          setBuiltinVoiceStatus(`Preview ready for ${state.selectedBuiltInSpeaker}.`);
        } catch (err) {
          setBuiltinVoiceStatus(`Preview failed: ${String(err)}`, true);
        } finally {
          previewBuiltinVoiceBtn.disabled = false;
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
        applySavedSampleSelection(selectedHash, { persist: true });
      } else if (!state.selectedAudioFile) {
        state.selectedAudioHash = null;
        if (audioDropzoneTitleNode) {
          audioDropzoneTitleNode.textContent = "Drop audio here or click to choose";
        }
        if (audioFileNameNode) {
          audioFileNameNode.textContent = "No file selected.";
        }
        clearReferencePreview();
        queueProjectSettingsSave();
      }
      updateSavedSampleDeleteButtonState();
    });
  }

  if (refreshSamplesBtn) {
    refreshSamplesBtn.addEventListener("click", () => {
      void loadReferenceSamples();
    });
  }

  if (deleteSavedSampleBtn) {
    deleteSavedSampleBtn.addEventListener("click", () => {
      void handleDeleteSavedSample();
    });
  }

  if (audioFileInputNode) {
    audioFileInputNode.addEventListener("change", async () => {
      const file = audioFileInputNode.files && audioFileInputNode.files[0];
      if (!file) {
        setSelectedAudioFile(null);
        return;
      }
      await handleSelectedReferenceFile(file, "Uploaded audio");
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
    void handleSelectedReferenceFile(file, "Dropped audio");
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

        await handleSelectedReferenceFile(file, "Recorded audio");
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

  if (deleteScriptVersionBtn) {
    deleteScriptVersionBtn.addEventListener("click", () => {
      void handleDeleteScriptVersion();
    });
  }
}

function bindGapSlider() {
  if (!gapSliderNode || !gapValueNode) return;

  const update = () => {
    updateGapValueDisplay();
    queueProjectSettingsSave();
  };

  gapSliderNode.addEventListener("input", update);
  if (qualityNode) {
    qualityNode.addEventListener("change", () => {
      queueProjectSettingsSave();
      if (state.voiceSource === "builtin") {
        void loadBuiltinVoices();
      }
    });
  }
  if (outputFormatNode) {
    outputFormatNode.addEventListener("change", () => {
      queueProjectSettingsSave();
    });
  }
  if (umsToggleNode) {
    umsToggleNode.addEventListener("change", () => {
      queueProjectSettingsSave();
    });
  }
  if (ahsToggleNode) {
    ahsToggleNode.addEventListener("change", () => {
      queueProjectSettingsSave();
    });
  }
  if (transcriptToggleNode) {
    transcriptToggleNode.addEventListener("change", () => {
      queueProjectSettingsSave();
    });
  }
  updateGapValueDisplay();
}

function setupThemeToggle() {
  const themeToggle = document.getElementById("themeToggle");
  if (!themeToggle) return;

  const icon = themeToggle.querySelector(".theme-icon");
  const storageKey = "radtts-theme";
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  let currentTheme = localStorage.getItem(storageKey) || (prefersDark ? "dark" : "light");

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
      themeToggle.setAttribute("aria-label", "Switch to light mode");
      themeToggle.setAttribute("aria-pressed", "true");
      themeToggle.dataset.icon = "light";
      if (icon) icon.dataset.iconState = "light";
    } else {
      document.documentElement.removeAttribute("data-theme");
      themeToggle.setAttribute("aria-label", "Switch to dark mode");
      themeToggle.setAttribute("aria-pressed", "false");
      themeToggle.dataset.icon = "dark";
      if (icon) icon.dataset.iconState = "dark";
    }
    localStorage.setItem(storageKey, theme);
  }

  applyTheme(currentTheme);
  themeToggle.addEventListener("click", () => {
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(currentTheme);
  });
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
bindHelpModal();
bindWorkerStatus();
bindReferenceTrimModal();
bindVoiceSource();
bindAudioSelection();
bindRecording();
bindScriptFileLoader();
bindScriptPersistence();
setupThemeToggle();
bindGapSlider();
bindGenerate();
bindOutputActions();
setVoiceSourceUi("reference");
setSelectedAudioFile(null);
resetScriptEditorState();
resetWorkerStatusUi();
setSavedSampleStatus("Saved samples are scoped to this project.");
setRecordStatus("Use Record audio to capture a sample from your microphone.");
setCancelVisible(false);
resetProgressUi();
