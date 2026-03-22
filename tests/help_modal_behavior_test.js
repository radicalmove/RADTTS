#!/usr/bin/env node

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

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
    this.tabIndex = 0;
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
    if (!evt.target) {
      evt.target = this;
    }
    if (!evt.preventDefault) {
      evt.preventDefault = () => {
        evt.defaultPrevented = true;
      };
    }
    const handlers = this.eventListeners.get(evt.type) || [];
    for (const handler of handlers) {
      handler(evt);
    }
    return !evt.defaultPrevented;
  }

  focus() {
    documentStub.activeElement = this;
  }

  setAttribute(name, value) {
    const stringValue = String(value);
    this.attributes.set(name, stringValue);
    if (name === "id") this.id = stringValue;
    if (name === "aria-selected") this.ariaSelected = stringValue;
    if (name === "tabindex") this.tabIndex = Number(stringValue);
    if (name.startsWith("data-")) {
      const key = name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      this.dataset[key] = stringValue;
    }
  }

  getAttribute(name) {
    return this.attributes.get(name) || null;
  }

  removeAttribute(name) {
    this.attributes.delete(name);
    if (name === "aria-selected") delete this.ariaSelected;
    if (name === "tabindex") this.tabIndex = 0;
    if (name.startsWith("data-")) {
      const key = name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      delete this.dataset[key];
    }
  }

  matches(selector) {
    if (selector.startsWith(".")) {
      return this.classList.contains(selector.slice(1));
    }
    if (selector.startsWith("[")) {
      const match = selector.match(/^\[data-([a-z-]+)(?:="([^"]*)")?\]$/);
      if (!match) return false;
      const key = match[1].replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      if (!(key in this.dataset)) return false;
      return match[2] ? this.dataset[key] === match[2] : true;
    }
    return this.tagName.toLowerCase() === selector.toLowerCase();
  }

  closest(selector) {
    let node = this;
    while (node) {
      if (node.matches && node.matches(selector)) return node;
      node = node.parentNode;
    }
    return null;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  querySelectorAll(selector) {
    const result = [];
    const walk = (node) => {
      if (node !== this && node.matches && node.matches(selector)) {
        result.push(node);
      }
      for (const child of node.children || []) {
        walk(child);
      }
    };
    walk(this);
    return result;
  }
}

class FakeButtonElement extends FakeElement {}
class FakeAudioElement extends FakeElement {
  pause() {}
  play() {
    return Promise.resolve();
  }
  load() {}
}
class FakeInputElement extends FakeElement {}
class FakeSelectElement extends FakeElement {}
class FakeTextAreaElement extends FakeElement {}
class FakeDivElement extends FakeElement {}

const elementFactory = new Map();
const specialIds = new Map([
  ["help-btn", () => new FakeButtonElement("button", "help-btn")],
  ["help-modal", () => {
    const modal = new FakeDivElement("div", "help-modal");
    modal.hidden = true;
    const tabs = new FakeDivElement("div");
    tabs.classList.add("help-modal-tabs");
    modal.appendChild(tabs);
    const body = new FakeDivElement("div");
    body.classList.add("help-modal-body");
    modal.appendChild(body);
    const tabKeys = [
      "overview",
      "generate-audio",
      "use-custom-voice",
      "prepare-reference-audio",
      "manage-versions-and-outputs",
      "use-helper-processing",
      "troubleshooting",
    ];
    for (const [index, tabKey] of tabKeys.entries()) {
      const button = new FakeButtonElement("button", `help-tab-${tabKey}`);
      button.classList.add("help-tab");
      if (index === 0) button.classList.add("is-active");
      button.dataset.helpTab = tabKey;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-controls", `help-panel-${tabKey}`);
      button.setAttribute("aria-selected", index === 0 ? "true" : "false");
      button.setAttribute("tabindex", index === 0 ? "0" : "-1");
      tabs.appendChild(button);

      const panel = new FakeDivElement("section", `help-panel-${tabKey}`);
      panel.classList.add("help-panel");
      if (index === 0) panel.classList.add("is-active");
      panel.dataset.helpPanel = tabKey;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", `help-tab-${tabKey}`);
      panel.hidden = index !== 0;
      body.appendChild(panel);
    }
    return modal;
  }],
  ["help-close-btn", () => new FakeButtonElement("button", "help-close-btn")],
  ["themeToggle", () => {
    const button = new FakeButtonElement("button", "themeToggle");
    const icon = new FakeElement("img");
    icon.classList.add("theme-icon");
    button.appendChild(icon);
    button.querySelector = (selector) => (selector === ".theme-icon" ? icon : null);
    return button;
  }],
  ["worker-setup-modal", () => {
    const modal = new FakeDivElement("div", "worker-setup-modal");
    modal.hidden = true;
    return modal;
  }],
  ["reference-trim-modal", () => {
    const modal = new FakeDivElement("div", "reference-trim-modal");
    modal.hidden = true;
    return modal;
  }],
  ["share-project-modal", () => {
    const modal = new FakeDivElement("div", "share-project-modal");
    modal.hidden = true;
    return modal;
  }],
]);

function createGenericElement(id) {
  if (id.endsWith("-btn") || id === "themeToggle") return new FakeButtonElement("button", id);
  if (id.includes("select") || id.includes("quality") || id.includes("format")) return new FakeSelectElement("select", id);
  if (id.includes("textarea") || id === "script-text") return new FakeTextAreaElement("textarea", id);
  if (id.includes("audio") || id.includes("preview")) return new FakeAudioElement("audio", id);
  if (id.includes("input") || id.includes("slider") || id.includes("toggle")) return new FakeInputElement("input", id);
  return new FakeDivElement("div", id);
}

const documentStub = {
  activeElement: null,
  body: new FakeElement("body"),
  documentElement: new FakeElement("html"),
  _listeners: new Map(),
  getElementById(id) {
    if (!elementFactory.has(id)) {
      const element = specialIds.has(id) ? specialIds.get(id)() : createGenericElement(id);
      elementFactory.set(id, element);
    }
    return elementFactory.get(id);
  },
  addEventListener(type, handler) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(handler);
  },
  dispatchEvent(event) {
    const evt = event || { type: "" };
    if (!evt.target) evt.target = this;
    if (!evt.preventDefault) {
      evt.preventDefault = () => {
        evt.defaultPrevented = true;
      };
    }
    const handlers = this._listeners.get(evt.type) || [];
    for (const handler of handlers) handler(evt);
  },
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
};

context.window = {
  document: documentStub,
  localStorage: localStorageStub,
  navigator: context.navigator,
  matchMedia: () => ({ matches: false }),
  isSecureContext: true,
  open() {},
  prompt() {},
};
context.window.window = context.window;
context.window.HTMLElement = FakeElement;
context.window.HTMLButtonElement = FakeButtonElement;
context.window.HTMLAudioElement = FakeAudioElement;
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
  "switch-project-btn",
  "share-project-btn",
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

documentStub.activeElement = documentStub.getElementById("help-btn");
localStorageStub.setItem("radtts-help-last-tab", "not-a-real-tab");

const uiPath = path.join(__dirname, "..", "src", "radtts", "static", "ui.js");
const source = fs.readFileSync(uiPath, "utf8");
vm.createContext(context);
vm.runInContext(source, context, { filename: uiPath });

assert.equal(documentStub.body.classList.contains("modal-open"), false);

const helpBtn = documentStub.getElementById("help-btn");
const helpModal = documentStub.getElementById("help-modal");
const helpCloseBtn = documentStub.getElementById("help-close-btn");
const tabsNode = helpModal.querySelector(".help-modal-tabs");
const overviewTab = helpModal.querySelector('[data-help-tab="overview"]');
const helperTab = helpModal.querySelector('[data-help-tab="use-helper-processing"]');
const troubleshootingTab = helpModal.querySelector('[data-help-tab="troubleshooting"]');
helpModal.appendChild(helpCloseBtn);

helpBtn.focus();
context.openHelpModal();
assert.equal(helpModal.hidden, false);
assert.equal(documentStub.body.classList.contains("modal-open"), true);
assert.equal(overviewTab.getAttribute("aria-selected"), "true");
assert.equal(documentStub.activeElement, overviewTab);
assert.equal(localStorageStub.getItem("radtts-help-last-tab"), "overview");

context.selectHelpTab("use-helper-processing", { focusTab: true });
assert.equal(helperTab.getAttribute("aria-selected"), "true");
assert.equal(documentStub.activeElement, helperTab);
assert.equal(localStorageStub.getItem("radtts-help-last-tab"), "use-helper-processing");

context.closeHelpModal();
assert.equal(helpModal.hidden, true);
assert.equal(documentStub.body.classList.contains("modal-open"), false);
assert.equal(documentStub.activeElement, helpBtn);

helpBtn.focus();
context.openHelpModal();
assert.equal(documentStub.activeElement, helperTab);

helperTab.focus();
helpModal.dispatchEvent({
  type: "keydown",
  key: "Tab",
  shiftKey: true,
  target: helperTab,
});
assert.equal(documentStub.activeElement, helpCloseBtn);

helpCloseBtn.focus();
helpModal.dispatchEvent({
  type: "keydown",
  key: "Tab",
  shiftKey: false,
  target: helpCloseBtn,
});
assert.equal(documentStub.activeElement, helperTab);

tabsNode.dispatchEvent({
  type: "keydown",
  key: "ArrowRight",
  target: helperTab,
});
assert.equal(troubleshootingTab.getAttribute("aria-selected"), "true");
assert.equal(documentStub.activeElement, troubleshootingTab);
assert.equal(localStorageStub.getItem("radtts-help-last-tab"), "troubleshooting");

documentStub.dispatchEvent({
  type: "keydown",
  key: "Escape",
  target: documentStub,
});
assert.equal(helpModal.hidden, true);
assert.equal(documentStub.activeElement, helpBtn);

console.log("help modal behavior test passed");
