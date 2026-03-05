const responseNode = document.getElementById("response");

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
  responseNode.textContent = JSON.stringify({ title, payload }, null, 2);
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

function bindCreateProject() {
  const form = document.getElementById("create-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const payload = {
      project_id: fd.get("project_id").trim(),
      course: cleanOptional(fd.get("course")),
      module: cleanOptional(fd.get("module")),
      lesson: cleanOptional(fd.get("lesson")),
    };

    try {
      const data = await requestJSON("/projects", "POST", payload);
      showResponse("project created", data);
    } catch (err) {
      showResponse("project create failed", { error: String(err) });
    }
  });
}

function bindTranscribe() {
  const form = document.getElementById("transcribe-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const payload = {
      project_id: fd.get("project_id").trim(),
      audio_path: fd.get("audio_path").trim(),
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
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const payload = {
      project_id: fd.get("project_id").trim(),
      audio_path: fd.get("audio_path").trim(),
      segments_json_path: fd.get("segments_json_path").trim(),
      output_name: fd.get("output_name").trim(),
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
  const modeSelect = document.getElementById("mode-select");
  const modelSelect = document.getElementById("model-id");
  const presetSelect = document.getElementById("preset-select");

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
  applyMode();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);

    const payload = {
      project_id: fd.get("project_id").trim(),
      text: fd.get("text").trim(),
      reference_audio_path: fd.get("reference_audio_path").trim(),
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
      output_name: fd.get("output_name").trim(),
      voice_clone_authorized: fd.get("ack_voice_clone") === "on",
    };

    try {
      const data = await requestJSON("/synthesize", "POST", payload);
      showResponse("synthesis job started", data);
    } catch (err) {
      showResponse("synthesis failed", { error: String(err) });
    }
  });
}

function bindCaptions() {
  const form = document.getElementById("captions-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);

    const payload = {
      project_id: fd.get("project_id").trim(),
      audio_path: fd.get("audio_path").trim(),
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

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const projectId = fd.get("project_id").trim();
    const jobId = fd.get("job_id").trim();

    try {
      const data = await requestJSON(`/jobs/${encodeURIComponent(jobId)}?project_id=${encodeURIComponent(projectId)}`, "GET");
      showResponse("job status", data);
    } catch (err) {
      showResponse("job fetch failed", { error: String(err) });
    }
  });

  cancelBtn.addEventListener("click", async () => {
    const fd = new FormData(form);
    const projectId = fd.get("project_id").trim();
    const jobId = fd.get("job_id").trim();

    try {
      const data = await requestJSON(`/jobs/${encodeURIComponent(jobId)}/cancel?project_id=${encodeURIComponent(projectId)}`, "POST");
      showResponse("job cancel requested", data);
    } catch (err) {
      showResponse("job cancel failed", { error: String(err) });
    }
  });
}

bindCreateProject();
bindTranscribe();
bindClip();
bindSynthesize();
bindCaptions();
bindJobLookup();
