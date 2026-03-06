const projectGatewayNode = document.getElementById("project-gateway");
const workspaceNode = document.getElementById("workspace");
const switchProjectBtn = document.getElementById("switch-project-btn");
const activeProjectChip = document.getElementById("active-project-chip");
const activeProjectLabelNode = document.getElementById("active-project-label");

const existingProjectSelectNode = document.getElementById("existing-project-select");
const openProjectFormNode = document.getElementById("open-project-form");
const refreshProjectsBtn = document.getElementById("refresh-projects-btn");
const projectGatewayStatusNode = document.getElementById("project-gateway-status");

const audioDropzoneNode = document.getElementById("audio-dropzone");
const audioFileInputNode = document.getElementById("reference-audio-file");
const audioDropzoneTitleNode = document.getElementById("audio-dropzone-title");
const audioFileNameNode = document.getElementById("audio-file-name");
const recordAudioBtn = document.getElementById("record-audio-btn");
const recordStatusNode = document.getElementById("record-status");
const recordPreviewNode = document.getElementById("record-preview");

const scriptTextNode = document.getElementById("script-text");
const scriptFileInputNode = document.getElementById("script-file");
const scriptFileStatusNode = document.getElementById("script-file-status");

const qualityNode = document.getElementById("quality-level");
const outputFormatNode = document.getElementById("output-format");
const fillersToggleNode = document.getElementById("fillers-toggle");
const transcriptToggleNode = document.getElementById("transcript-toggle");
const gapSliderNode = document.getElementById("gap-slider");
const gapValueNode = document.getElementById("gap-value");

const generateBtn = document.getElementById("generate-btn");
const generateStatusNode = document.getElementById("generate-status");
const progressWrapNode = document.getElementById("progress-wrap");
const progressStageNode = document.getElementById("progress-stage");
const progressPercentNode = document.getElementById("progress-percent");
const progressFillNode = document.getElementById("progress-fill");

const latestOutputNode = document.getElementById("latest-output");
const latestOutputLinksNode = document.getElementById("latest-output-links");
const outputListNode = document.getElementById("output-list");

const stageLabels = {
  queued: "Queued",
  model_load: "Loading voice model",
  generation: "Generating audio",
  stitching: "Finalizing audio",
  captioning: "Creating transcript",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const stageFallbackProgress = {
  queued: 0,
  model_load: 10,
  generation: 45,
  stitching: 72,
  captioning: 85,
  completed: 100,
  failed: 100,
  cancelled: 0,
};

const state = {
  activeProjectId: null,
  selectedAudioFile: null,
  activeJobId: null,
  pollTimer: null,
  mediaRecorder: null,
  recordingStream: null,
  recordingChunks: [],
  recordingPreviewUrl: null,
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

function setWorkspaceVisible(visible) {
  if (projectGatewayNode) projectGatewayNode.hidden = visible;
  if (workspaceNode) workspaceNode.classList.toggle("workspace-hidden", !visible);
  if (switchProjectBtn) switchProjectBtn.hidden = !visible;
  if (activeProjectChip) activeProjectChip.hidden = !visible;
}

function setGenerateEnabled(enabled) {
  if (generateBtn) generateBtn.disabled = !enabled;
}

function updateRecordButtonState(isRecording) {
  if (!recordAudioBtn) return;
  recordAudioBtn.classList.toggle("is-recording", isRecording);
  recordAudioBtn.textContent = isRecording ? "Stop Recording" : "Record Audio";
}

function clearPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  state.activeJobId = null;
}

function resetRunUi() {
  if (progressWrapNode) progressWrapNode.hidden = true;
  if (progressFillNode) progressFillNode.style.width = "0%";
  if (progressPercentNode) progressPercentNode.textContent = "0%";
  if (progressStageNode) progressStageNode.textContent = "Queued";
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

function setProgress(progressPercent, stage) {
  const clamped = Math.max(0, Math.min(100, progressPercent));
  if (progressWrapNode) progressWrapNode.hidden = false;
  if (progressFillNode) progressFillNode.style.width = `${clamped}%`;
  if (progressPercentNode) progressPercentNode.textContent = `${clamped}%`;
  if (progressStageNode) progressStageNode.textContent = stageLabels[stage] || stage || "Processing";
}

function applyActiveProject(projectId) {
  state.activeProjectId = projectId;
  if (activeProjectLabelNode) activeProjectLabelNode.textContent = projectId;
  setWorkspaceVisible(true);
  setGenerateStatus("");
  resetRunUi();
  clearPolling();
  loadOutputs();
}

function requireActiveProject() {
  if (!state.activeProjectId) {
    throw new Error("Select or create a project first.");
  }
  return state.activeProjectId;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatIso(isoValue) {
  if (!isoValue) return "";
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return String(isoValue);
  return date.toLocaleString();
}

function updateOpenButtonState() {
  const hasSelection = Boolean(existingProjectSelectNode && existingProjectSelectNode.value);
  const openBtn = document.getElementById("open-project-btn");
  if (openBtn) openBtn.disabled = !hasSelection;
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
    setRecordStatus(`${originLabel} saved to project as ${data.filename}.`);
  } catch (err) {
    setRecordStatus(`${originLabel} selected, but could not be saved yet: ${String(err)}`, true);
  }
}

function setSelectedAudioFile(file) {
  state.selectedAudioFile = file || null;
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

async function loadProjects(preselectProjectId = null) {
  if (!existingProjectSelectNode) return;
  existingProjectSelectNode.innerHTML = '<option value="">Loading projects...</option>';
  updateOpenButtonState();

  try {
    const data = await requestJSON("/projects", "GET");
    const projects = Array.isArray(data.projects) ? data.projects : [];
    existingProjectSelectNode.innerHTML = "";

    if (!projects.length) {
      existingProjectSelectNode.innerHTML = '<option value="">No projects yet</option>';
      setGatewayStatus("No existing projects yet. Create one to continue.");
      updateOpenButtonState();
      return;
    }

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select a project";
    existingProjectSelectNode.appendChild(placeholder);

    for (const project of projects) {
      const option = document.createElement("option");
      option.value = project.project_id;
      option.textContent = project.project_id;
      existingProjectSelectNode.appendChild(option);
    }

    if (preselectProjectId) {
      existingProjectSelectNode.value = preselectProjectId;
    }
    setGatewayStatus("");
    updateOpenButtonState();
  } catch (err) {
    existingProjectSelectNode.innerHTML = '<option value="">Unable to load projects</option>';
    setGatewayStatus(`Could not load projects: ${String(err)}`, true);
    updateOpenButtonState();
  }
}

function renderLatestOutput(output) {
  if (!latestOutputNode || !latestOutputLinksNode) return;
  if (!output) {
    latestOutputNode.hidden = true;
    latestOutputLinksNode.innerHTML = "";
    return;
  }

  const links = [];
  if (output.audio_download_url) {
    links.push(`<a href="${escapeHtml(output.audio_download_url)}" target="_blank" rel="noopener">Open audio</a>`);
  }
  if (output.srt_download_url) {
    links.push(`<a href="${escapeHtml(output.srt_download_url)}" target="_blank" rel="noopener">Open transcript (.srt)</a>`);
  }
  if (output.folder_path) {
    links.push(`<button class="copy-folder-btn" data-folder="${escapeHtml(output.folder_path)}" type="button">Copy folder path</button>`);
  }

  latestOutputLinksNode.innerHTML = links.join(" ");
  latestOutputNode.hidden = false;
}

function renderOutputs(outputs) {
  if (!outputListNode) return;

  if (!outputs.length) {
    outputListNode.innerHTML = '<li class="output-item">No generated files in this project yet.</li>';
    renderLatestOutput(null);
    return;
  }

  renderLatestOutput(outputs[0]);

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
  const projectId = state.activeProjectId;
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

async function pollJob() {
  if (!state.activeJobId || !state.activeProjectId) return;

  try {
    const data = await requestJSON(
      `/jobs/${encodeURIComponent(state.activeJobId)}?project_id=${encodeURIComponent(state.activeProjectId)}`,
      "GET"
    );

    const stage = String(data.stage || "queued");
    const percentage = Number.isFinite(Number(data.progress))
      ? Math.round(Number(data.progress) * 100)
      : stageFallbackProgress[stage] || 0;

    setProgress(percentage, stage);

    if (data.status === "completed") {
      clearPolling();
      setGenerateEnabled(true);
      setProgress(100, "completed");
      setGenerateStatus("Audio generation complete.");
      await loadOutputs();
      return;
    }

    if (data.status === "failed") {
      clearPolling();
      setGenerateEnabled(true);
      setGenerateStatus(`Generation failed: ${data.error || "Unknown error"}`, true);
      return;
    }

    if (data.status === "cancelled") {
      clearPolling();
      setGenerateEnabled(true);
      setGenerateStatus("Generation was cancelled.", true);
    }
  } catch (err) {
    if (String(err).includes("404")) {
      return;
    }
    clearPolling();
    setGenerateEnabled(true);
    setGenerateStatus(`Progress check failed: ${String(err)}`, true);
  }
}

function startPolling(jobId) {
  clearPolling();
  state.activeJobId = jobId;
  setProgress(0, "queued");
  state.pollTimer = setInterval(pollJob, 2000);
  pollJob();
}

async function handleGenerate() {
  try {
    const projectId = requireActiveProject();
    const scriptText = cleanOptional(scriptTextNode?.value || "");

    if (!state.selectedAudioFile) {
      throw new Error("Please select an audio sample.");
    }
    if (!scriptText) {
      throw new Error("Please provide script text.");
    }

    setGenerateEnabled(false);
    setGenerateStatus("Uploading files and creating job...");
    resetRunUi();

    const referenceAudioB64 = await fileToBase64(state.selectedAudioFile);
    const payload = {
      project_id: projectId,
      text: scriptText,
      reference_audio_b64: referenceAudioB64,
      reference_audio_filename: state.selectedAudioFile.name,
      quality: qualityNode?.value || "normal",
      add_fillers: Boolean(fillersToggleNode?.checked),
      average_gap_seconds: Number(gapSliderNode?.value || 0.8),
      output_format: outputFormatNode?.value || "mp3",
      voice_clone_authorized: true,
      generate_transcript: Boolean(transcriptToggleNode?.checked),
    };

    const data = await requestJSON("/synthesize/simple", "POST", payload);
    setGenerateStatus("Generation job started.");
    startPolling(data.job_id);
  } catch (err) {
    setGenerateEnabled(true);
    setGenerateStatus(String(err), true);
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
        await requestJSON("/projects", "POST", payload);
        applyActiveProject(projectId);
        setGatewayStatus("");
        await loadProjects(projectId);
      } catch (err) {
        setGatewayStatus(`Project create failed: ${String(err)}`, true);
      }
    });
  }

  if (existingProjectSelectNode) {
    existingProjectSelectNode.addEventListener("change", updateOpenButtonState);
  }

  if (openProjectFormNode) {
    openProjectFormNode.addEventListener("submit", (event) => {
      event.preventDefault();
      const projectId = existingProjectSelectNode ? existingProjectSelectNode.value.trim() : "";
      if (!projectId) {
        setGatewayStatus("Select a project first.", true);
        return;
      }
      applyActiveProject(projectId);
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
      clearPolling();
      state.activeProjectId = null;
      if (activeProjectLabelNode) activeProjectLabelNode.textContent = "";
      setWorkspaceVisible(false);
      setGenerateStatus("");
      resetRunUi();
      await loadProjects();
    });
  }

  setWorkspaceVisible(false);
  loadProjects();
}

function bindAudioSelection() {
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
      setRecordStatus("Recording... click Stop Recording when finished.");
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
  if (!generateBtn) return;
  generateBtn.addEventListener("click", handleGenerate);
}

function bindFolderCopy() {
  const delegate = (event) => {
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
  };

  if (outputListNode) outputListNode.addEventListener("click", delegate);
  if (latestOutputLinksNode) latestOutputLinksNode.addEventListener("click", delegate);
}

bindProjectGateway();
bindAudioSelection();
bindRecording();
bindScriptFileLoader();
bindGapSlider();
bindGenerate();
bindFolderCopy();
setSelectedAudioFile(null);
setRecordStatus("Use Record Audio to capture a sample from your microphone.");
