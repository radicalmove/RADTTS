#!/usr/bin/env node

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class FakeClassList {
  constructor() {
    this._items = new Set();
  }
  add(...tokens) {
    for (const token of tokens) this._items.add(token);
  }
  remove(...tokens) {
    for (const token of tokens) this._items.delete(token);
  }
  toggle(token, force) {
    if (force === true) {
      this._items.add(token);
      return true;
    }
    if (force === false) {
      this._items.delete(token);
      return false;
    }
    if (this._items.has(token)) {
      this._items.delete(token);
      return false;
    }
    this._items.add(token);
    return true;
  }
  contains(token) {
    return this._items.has(token);
  }
}

class FakeElement {
  constructor(tagName = "div", id = "") {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.children = [];
    this.parentNode = null;
    this.hidden = false;
    this.classList = new FakeClassList();
    this.dataset = {};
    this.style = {};
    this.attributes = new Map();
    this.eventListeners = new Map();
    this.textContent = "";
    this.value = "";
    this.disabled = false;
    this.innerHTML = "";
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  addEventListener(type, handler) {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, []);
    }
    this.eventListeners.get(type).push(handler);
  }

  dispatchEvent(event) {
    const evt = event || { type: "" };
    const handlers = this.eventListeners.get(evt.type) || [];
    for (const handler of handlers) handler(evt);
  }

  querySelector() {
    return null;
  }

  querySelectorAll() {
    return [];
  }

  pause() {}
  play() {
    return Promise.resolve();
  }
  load() {}
  focus() {}
  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }
  getAttribute(name) {
    return this.attributes.get(name) || null;
  }
  removeAttribute(name) {
    this.attributes.delete(name);
  }
}

class FakeAudioElement extends FakeElement {}
class FakeInputElement extends FakeElement {}
class FakeSelectElement extends FakeElement {}
class FakeTextAreaElement extends FakeElement {}
class FakeButtonElement extends FakeElement {}

function createGenericElement(id) {
  if (id.endsWith("-btn") || id.includes("button")) return new FakeButtonElement("button", id);
  if (id.includes("select") || id.includes("quality") || id.includes("format")) return new FakeSelectElement("select", id);
  if (id.includes("textarea") || id === "script-text") return new FakeTextAreaElement("textarea", id);
  if (id.includes("audio") || id.includes("preview")) return new FakeAudioElement("audio", id);
  if (id.includes("input") || id.includes("slider") || id.includes("toggle")) return new FakeInputElement("input", id);
  return new FakeElement("div", id);
}

const elementFactory = new Map();
const documentStub = {
  body: new FakeElement("body"),
  documentElement: new FakeElement("html"),
  activeElement: null,
  getElementById(id) {
    if (!elementFactory.has(id)) {
      elementFactory.set(id, createGenericElement(id));
    }
    return elementFactory.get(id);
  },
  addEventListener() {},
  dispatchEvent() {},
  createElement(tagName) {
    return new FakeElement(tagName);
  },
  querySelectorAll() {
    return [];
  },
};

documentStub.body.classList = new FakeClassList();
documentStub.documentElement.classList = new FakeClassList();

const localStorageStub = {
  _data: new Map(),
  getItem(key) {
    return this._data.has(key) ? this._data.get(key) : null;
  },
  setItem(key, value) {
    this._data.set(key, String(value));
  },
  removeItem(key) {
    this._data.delete(key);
  },
};

const fetchStub = async () => ({
  ok: true,
  status: 200,
  statusText: "OK",
  async json() {
    return { projects: [] };
  },
});

const context = {
  console,
  document: documentStub,
  window: null,
  localStorage: localStorageStub,
  navigator: { clipboard: { async writeText() {} } },
  HTMLElement: FakeElement,
  HTMLButtonElement: FakeButtonElement,
  HTMLAudioElement: FakeAudioElement,
  FileReader: class {},
  FormData: class {},
  URL: {
    createObjectURL() {
      return "blob:fake";
    },
    revokeObjectURL() {},
  },
  fetch: fetchStub,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  Promise,
  Blob,
  Event: class {},
  isFinite,
  parseFloat,
  parseInt,
  Math,
  Date,
};

context.window = {
  document: documentStub,
  localStorage: localStorageStub,
  navigator: context.navigator,
  matchMedia: () => ({ matches: false }),
  isSecureContext: true,
  open() {},
  confirm() { return true; },
  prompt() {},
};
context.window.window = context.window;
context.window.document = documentStub;
context.window.fetch = fetchStub;
context.window.URL = context.URL;
context.window.setTimeout = setTimeout;
context.window.clearTimeout = clearTimeout;
context.window.setInterval = setInterval;
context.window.clearInterval = clearInterval;
context.window.console = console;
context.window.navigator = context.navigator;
context.window.requestAnimationFrame = (cb) => setTimeout(cb, 0);
context.window.cancelAnimationFrame = (id) => clearTimeout(id);

for (const id of [
  "project-gateway",
  "workspace",
  "switch-project-btn",
  "share-project-btn",
  "help-btn",
  "active-project-chip",
  "active-project-label",
  "worker-status-pill",
  "worker-status-detail",
  "worker-refresh-btn",
  "worker-setup-btn",
  "worker-setup-links",
  "worker-setup-windows-link",
  "worker-setup-macos-link",
  "worker-copy-macos-btn",
  "worker-copy-linux-btn",
  "worker-setup-modal",
  "worker-setup-close-btn",
  "worker-setup-modal-status",
  "existing-project-select",
  "recent-project-list",
  "refresh-projects-btn",
  "project-gateway-status",
  "audio-dropzone",
  "reference-audio-file",
  "audio-dropzone-title",
  "audio-file-name",
  "voice-source-reference",
  "voice-source-builtin",
  "reference-voice-pane",
  "builtin-voice-pane",
  "saved-sample-select",
  "refresh-samples-btn",
  "delete-saved-sample-btn",
  "saved-sample-status",
  "record-audio-btn",
  "record-status",
  "reference-preview-label",
  "record-preview",
  "reference-trim-modal",
  "reference-trim-close-btn",
  "reference-trim-modal-status",
  "reference-trim-source-name",
  "reference-trim-source-duration",
  "reference-trim-preview",
  "reference-trim-start",
  "reference-trim-end",
  "reference-trim-start-value",
  "reference-trim-end-value",
  "reference-trim-selection-summary",
  "reference-trim-play-btn",
  "reference-trim-apply-btn",
  "reference-trim-skip-btn",
  "share-project-modal",
  "share-project-close-btn",
  "share-project-user-select",
  "share-project-grant-btn",
  "share-project-status",
  "share-project-owner",
  "share-project-members",
  "help-modal",
  "help-close-btn",
  "builtin-voice-select",
  "builtin-voice-status",
  "preview-builtin-voice-btn",
  "builtin-voice-preview",
  "script-text",
  "script-file",
  "script-file-status",
  "script-version-select",
  "restore-script-version-btn",
  "delete-script-version-btn",
  "script-save-status",
  "quality-level",
  "output-format",
  "ums-toggle",
  "ahs-toggle",
  "transcript-toggle",
  "gap-slider",
  "gap-value",
  "generate-btn",
  "cancel-btn",
  "generate-status",
  "progress-wrap",
  "progress-stage",
  "progress-compute",
  "progress-eta",
  "progress-percent",
  "progress-fill",
  "progress-detail",
  "output-list",
]) {
  documentStub.getElementById(id);
}

const uiPath = path.join(__dirname, "..", "src", "radtts", "static", "ui.js");
const source = fs.readFileSync(uiPath, "utf8");
vm.createContext(context);
vm.runInContext(source, context, { filename: uiPath });

vm.runInContext(
  `
    state.currentStatus = "running";
    state.currentStage = "generation";
    state.jobStartedAtMs = Date.now() - 60000;
    state.stageStartedAtMs = Date.now() - 60000;
    state.actualProgress = 51;
    state.displayProgress = 51;
    state.currentJobLogs = [];
    state.computeMode = "worker";
    state.latestDetail = "Generating first chunk. This can take a while.";
    updateProgressVisuals(51, "generation");
  `,
  context,
);

assert.equal(
  documentStub.getElementById("progress-eta").textContent,
  "Time left to process: estimating...",
);

const heavyAssessment = vm.runInContext(
  `
    assessRunPreflight({
      text: "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven. Sentence eight. Sentence nine. Sentence ten. Sentence eleven. Sentence twelve. Sentence thirteen. Sentence fourteen. Sentence fifteen. Sentence sixteen. Sentence seventeen. Sentence eighteen. Sentence nineteen. Sentence twenty.",
      averageGapSeconds: 0.8,
      addFillers: false,
      voiceSource: "reference",
      quality: "normal",
      referenceDurationSeconds: 10,
    })
  `,
  context,
);
assert.equal(heavyAssessment.severity, "heavy");
assert.match(heavyAssessment.estimatedLocalRangeLabel, /^\d+-\d+ minutes$/);

let confirmCalls = 0;
context.window.confirm = () => {
  confirmCalls += 1;
  return false;
};
context.confirm = context.window.confirm;
const confirmed = vm.runInContext(
  `
    confirmRunPreflightIfNeeded(
      assessRunPreflight({
        text: "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven. Sentence eight. Sentence nine. Sentence ten. Sentence eleven. Sentence twelve. Sentence thirteen. Sentence fourteen. Sentence fifteen. Sentence sixteen. Sentence seventeen. Sentence eighteen. Sentence nineteen. Sentence twenty.",
        averageGapSeconds: 0.8,
        addFillers: false,
        voiceSource: "reference",
        quality: "normal",
        referenceDurationSeconds: 10,
      })
    )
  `,
  context,
);
assert.equal(confirmed, false);
assert.equal(confirmCalls, 1);

const batchDetail = vm.runInContext(
  `detailFromLogLine("generation batch 2/5", "generation")`,
  context,
);
assert.equal(batchDetail, "Generating speech (2/5 batches complete)");

vm.runInContext(
  `
    renderOutputs([
      {
        output_name: "sample",
        version_number: 1,
        audio_download_url: "/audio.mp3",
        srt_download_url: "/sample.srt",
        vtt_download_url: "/sample.vtt",
      },
    ]);
  `,
  context,
);
assert.match(documentStub.getElementById("output-list").innerHTML, /Open transcript \(\.srt\)/);
assert.match(documentStub.getElementById("output-list").innerHTML, /Open captions \(\.vtt\)/);

(async () => {
  context.fetch = async () => ({
    ok: false,
    status: 524,
    statusText: "Timeout",
    async json() {
      throw new Error("non-json");
    },
  });
  context.window.fetch = context.fetch;

  await vm.runInContext(
    `
      state.activeProjectRef = "proj-1";
      state.activeJobId = "job-1";
      state.currentStatus = "running";
      state.currentStage = "generation";
      state.jobStartedAtMs = Date.now() - 30000;
      state.stageStartedAtMs = Date.now() - 30000;
      state.actualProgress = 45;
      state.displayProgress = 45;
      state.currentJobLogs = [];
      state.computeMode = "worker";
      state.latestDetail = "Generating first chunk. This can take a while.";
      pollJob();
    `,
    context,
  );

  await new Promise((resolve) => setTimeout(resolve, 0));

  const activeJobId = vm.runInContext("state.activeJobId", context);
  assert.equal(activeJobId, "job-1");
  assert.match(documentStub.getElementById("generate-status").textContent, /Retrying/i);

  console.log("progress behavior test passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
