const responseNode = document.getElementById("response");
const projectGatewayNode = document.getElementById("project-gateway");
const workspaceNode = document.getElementById("workspace");
const switchProjectBtn = document.getElementById("switch-project-btn");
const activeProjectChip = document.getElementById("active-project-chip");
const activeProjectLabelNode = document.getElementById("active-project-label");
const existingProjectSelectNode = document.getElementById("existing-project-select");
const openProjectFormNode = document.getElementById("open-project-form");
const refreshProjectsBtn = document.getElementById("refresh-projects-btn");
const projectGatewayStatusNode = document.getElementById("project-gateway-status");

let activeProjectId = null;

function cleanOptional(value) {
  const trimmed = (value ?? "").trim();
  return trimmed.length ? trimmed : null;
}

function cleanNumber(value) {
  const trimmed = (value ?? "").trim();
  if (!trimmed.length) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function showResponse(title, payload) {
  if (!responseNode) return;
  responseNode.textContent = JSON.stringify({ title, payload }, null, 2);
}

function setGatewayStatus(message, isError = false) {
  if (!projectGatewayStatusNode) return;
  projectGatewayStatusNode.textContent = message || "";
  projectGatewayStatusNode.style.color = isError ? "#a73527" : "#555";
}

function setWorkspaceVisible(visible) {
  if (projectGatewayNode) projectGatewayNode.hidden = visible;
  if (workspaceNode) workspaceNode.classList.toggle("workspace-hidden", !visible);
  if (switchProjectBtn) switchProjectBtn.hidden = !visible;
  if (activeProjectChip) activeProjectChip.hidden = !visible;
}

function applyActiveProject(projectId) {
  activeProjectId = projectId;
  if (activeProjectLabelNode) activeProjectLabelNode.textContent = projectId;
  document
    .querySelectorAll('form[data-project-bound="true"] input[name="project_id"]')
    .forEach((input) => {
      input.value = projectId;
    });
}

function requireActiveProject() {
  if (!activeProjectId) {
    throw new Error("Select or create a project first.");
  }
  return activeProjectId;
}

function fileToBase64(file) {
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

function updateOpenButtonState() {
  const hasSelection = Boolean(existingProjectSelectNode && existingProjectSelectNode.value);
  const openBtn = document.getElementById("open-project-btn");
  if (openBtn) openBtn.disabled = !hasSelection;
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
        const data = await requestJSON("/projects", "POST", payload);
        applyActiveProject(projectId);
        setWorkspaceVisible(true);
        setGatewayStatus("");
        showResponse("project created", data);
        await loadProjects(projectId);
      } catch (err) {
        setGatewayStatus(`Project create failed: ${String(err)}`, true);
        showResponse("project create failed", { error: String(err) });
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
      setWorkspaceVisible(true);
      setGatewayStatus("");
      showResponse("project selected", { project_id: projectId });
    });
  }

  if (refreshProjectsBtn) {
    refreshProjectsBtn.addEventListener("click", async () => {
      await loadProjects(existingProjectSelectNode ? existingProjectSelectNode.value : null);
    });
  }

  if (switchProjectBtn) {
    switchProjectBtn.addEventListener("click", async () => {
      activeProjectId = null;
      if (activeProjectLabelNode) activeProjectLabelNode.textContent = "";
      setWorkspaceVisible(false);
      setGatewayStatus("");
      await loadProjects();
    });
  }

  setWorkspaceVisible(false);
  loadProjects();
}

function bindTranscribe() {
  const form = document.getElementById("transcribe-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const payload = {
      project_id: requireActiveProject(),
      audio_path: (fd.get("audio_path") || "").trim(),
      name: cleanOptional(fd.get("name")),
      model: cleanOptional(fd.get("model")) || "small",
      language: cleanOptional(fd.get("language")),
      beam_size: cleanNumber(fd.get("beam_size")) || 5,
    };

    try {
      const data = await requestJSON("/transcribe", "POST", payload);
      showResponse("transcription complete", data);
    } catch (err) {
      showResponse("transcription failed", { error: String(err) });
    }
  });
}

function bindClip() {
  const form = document.getElementById("clip-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const payload = {
      project_id: requireActiveProject(),
      audio_path: (fd.get("audio_path") || "").trim(),
      segments_json_path: (fd.get("segments_json_path") || "").trim(),
      output_name: (fd.get("output_name") || "").trim(),
      start_time: cleanNumber(fd.get("start_time")),
      end_time: cleanNumber(fd.get("end_time")),
      start_phrase: cleanOptional(fd.get("start_phrase")),
      end_phrase: cleanOptional(fd.get("end_phrase")),
      verification_mode: fd.get("verification_mode"),
      output_format: fd.get("output_format"),
    };

    try {
      const data = await requestJSON("/clip", "POST", payload);
      showResponse("clip extracted", data);
    } catch (err) {
      showResponse("clip failed", { error: String(err) });
    }
  });
}

function bindSynthesize() {
  const form = document.getElementById("synth-form");
  if (!form) return;

  const modeSelect = document.getElementById("mode-select");
  const modelSelect = document.getElementById("model-id");
  const presetSelect = document.getElementById("preset-select");
  const executionModeSelect = document.getElementById("execution-mode");
  const referencePathInput = document.getElementById("reference-audio-path");
  const referenceFileInput = document.getElementById("reference-audio-file");

  function applyExecutionMode() {
    const workerMode = executionModeSelect.value === "worker";
    referencePathInput.style.display = workerMode ? "none" : "block";
    referenceFileInput.style.display = workerMode ? "block" : "none";
    referencePathInput.required = !workerMode;
    referenceFileInput.required = workerMode;
  }

  function applyMode() {
    const mode = modeSelect.value;
    const mapped = window.RADTTS_UI?.modes?.[mode];
    if (mapped) modelSelect.value = mapped;
  }

  function applyPreset() {
    const option = presetSelect.selectedOptions[0];
    if (!option || !option.value) return;

    const chunkMode = option.dataset.chunkMode;
    const pauseMin = option.dataset.pauseMin;
    const pauseMax = option.dataset.pauseMax;
    const maxTokens = option.dataset.maxTokens;
    const modelMode = option.dataset.modelMode;

    if (chunkMode) form.elements.chunk_mode.value = chunkMode;
    if (pauseMin) form.elements.pause_min.value = pauseMin;
    if (pauseMax) form.elements.pause_max.value = pauseMax;
    if (maxTokens) form.elements.max_new_tokens.value = maxTokens;
    if (modelMode) {
      modeSelect.value = modelMode;
      applyMode();
    }
  }

  modeSelect.addEventListener("change", applyMode);
  presetSelect.addEventListener("change", applyPreset);
  executionModeSelect.addEventListener("change", applyExecutionMode);
  applyMode();
  applyExecutionMode();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);

    const payload = {
      project_id: requireActiveProject(),
      text: (fd.get("text") || "").trim(),
      reference_text: cleanOptional(fd.get("reference_text")),
      model_id: fd.get("model_id"),
      max_new_tokens: cleanNumber(fd.get("max_new_tokens")) || 1200,
      chunk_mode: fd.get("chunk_mode"),
      pause_config: {
        strategy: "random_uniform_with_length_adjustment",
        min_seconds: cleanNumber(fd.get("pause_min")) || 0.45,
        max_seconds: cleanNumber(fd.get("pause_max")) || 1.1,
        seed: cleanNumber(fd.get("pause_seed")),
      },
      output_format: fd.get("output_format"),
      output_name: (fd.get("output_name") || "").trim(),
      voice_clone_authorized: fd.get("ack_voice_clone") === "on",
    };

    try {
      if (executionModeSelect.value === "worker") {
        const file = referenceFileInput.files && referenceFileInput.files[0];
        if (!file) {
          throw new Error("Select a reference audio file for worker mode");
        }
        const b64 = await fileToBase64(file);
        const workerPayload = {
          ...payload,
          reference_audio_b64: b64,
          reference_audio_filename: file.name,
        };
        const data = await requestJSON("/synthesize/worker", "POST", workerPayload);
        showResponse("worker synthesis job queued", data);
      } else {
        payload.reference_audio_path = (fd.get("reference_audio_path") || "").trim();
        const data = await requestJSON("/synthesize", "POST", payload);
        showResponse("synthesis job started", data);
      }
    } catch (err) {
      showResponse("synthesis failed", { error: String(err) });
    }
  });
}

function bindCaptions() {
  const form = document.getElementById("captions-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);

    const payload = {
      project_id: requireActiveProject(),
      audio_path: (fd.get("audio_path") || "").trim(),
      name: cleanOptional(fd.get("name")),
      model: cleanOptional(fd.get("model")) || "small",
      language: cleanOptional(fd.get("language")),
    };

    try {
      const data = await requestJSON("/captions", "POST", payload);
      showResponse("captions generated", data);
    } catch (err) {
      showResponse("captions failed", { error: String(err) });
    }
  });
}

function bindJobLookup() {
  const form = document.getElementById("job-form");
  const cancelBtn = document.getElementById("job-cancel");
  if (!form || !cancelBtn) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const projectId = requireActiveProject();
    const jobId = (fd.get("job_id") || "").trim();

    try {
      const data = await requestJSON(`/jobs/${encodeURIComponent(jobId)}?project_id=${encodeURIComponent(projectId)}`, "GET");
      showResponse("job status", data);
    } catch (err) {
      showResponse("job fetch failed", { error: String(err) });
    }
  });

  cancelBtn.addEventListener("click", async () => {
    const fd = new FormData(form);
    const projectId = requireActiveProject();
    const jobId = (fd.get("job_id") || "").trim();

    try {
      const data = await requestJSON(`/jobs/${encodeURIComponent(jobId)}/cancel?project_id=${encodeURIComponent(projectId)}`, "POST");
      showResponse("job cancel requested", data);
    } catch (err) {
      showResponse("job cancel failed", { error: String(err) });
    }
  });
}

function bindWorkers() {
  const inviteBtn = document.getElementById("worker-invite-btn");
  const refreshBtn = document.getElementById("worker-refresh-btn");
  const commandArea = document.getElementById("worker-install-command");
  if (!inviteBtn || !refreshBtn || !commandArea) return;

  inviteBtn.addEventListener("click", async () => {
    try {
      const data = await requestJSON("/workers/invite", "POST", { capabilities: ["synthesize"] });
      commandArea.value = data.install_command;
      showResponse("worker invite generated", data);
    } catch (err) {
      showResponse("worker invite failed", { error: String(err) });
    }
  });

  refreshBtn.addEventListener("click", async () => {
    try {
      const data = await requestJSON("/workers", "GET");
      showResponse("workers", data);
    } catch (err) {
      showResponse("worker list failed", { error: String(err) });
    }
  });
}

bindProjectGateway();
bindTranscribe();
bindClip();
bindSynthesize();
bindCaptions();
bindJobLookup();
bindWorkers();
