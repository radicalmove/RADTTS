# Shared Help Modal Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one consistent tabbed Help modal system across RADcite, RADcast, and RADTTS, with app-specific overview, task, and troubleshooting content, and make Help available on every screen in each app.

**Architecture:** Keep the implementation local to each app, but use the same modal shell, tab strip behavior, last-opened-tab persistence, and content structure in all three codebases. RADcast and RADTTS will gain a new Help modal using their existing modal-overlay system, while RADcite’s current Help modal will be refactored to the new tabbed layout without changing its topbar entry point.

**Tech Stack:** Server-rendered HTML templates, vanilla JavaScript, CSS, browser localStorage, Python-backed web apps, pytest, `node --check`

---

## File Structure Map

### RADcast

- Modify: `/Users/rcd58/RADcast/src/radcast/templates/index.html`
  - Add the topbar `Help` button.
  - Add Help modal shell markup and app-specific tab content containers.
- Modify: `/Users/rcd58/RADcast/src/radcast/static/ui.js`
  - Add Help modal open/close handlers, tab switching, localStorage restore, and any app-specific content wiring.
- Modify: `/Users/rcd58/RADcast/src/radcast/static/ui.css`
  - Add tabbed Help modal styling that matches the new shared design.
- Test: `/Users/rcd58/RADcast/tests/test_api_ui.py`
  - Add coverage for Help button visibility and any server-side template expectations that already exist in this suite.

### RADTTS

- Modify: `/Users/rcd58/RADTTS/src/radtts/templates/index.html`
  - Add the topbar `Help` button.
  - Add Help modal shell markup and app-specific tab content containers.
- Modify: `/Users/rcd58/RADTTS/src/radtts/static/ui.js`
  - Add Help modal open/close handlers, tab switching, localStorage restore, and any app-specific content wiring.
- Modify: `/Users/rcd58/RADTTS/src/radtts/static/ui.css`
  - Add tabbed Help modal styling that matches the new shared design.
- Test: `/Users/rcd58/RADTTS/tests/test_api_ui.py`
  - Add coverage for Help button visibility and any server-side template expectations that already exist in this suite.

### RADcite

- Modify: `/Users/rcd58/citation-checker/app/templates/index.html`
  - Replace the current static Help modal body with the new tabbed layout and app-specific content sections.
- Modify: `/Users/rcd58/citation-checker/app/static/js/wysiwyg.js`
  - Replace the simple open/close-only Help modal behavior with tab state and last-tab restore behavior.
- Modify: `/Users/rcd58/citation-checker/app/static/css/wysiwyg.css`
  - Replace the legacy Help modal section styling with the new shared tabbed Help visual system.
- Verify manually:
  - No established dedicated front-end Help test surface currently exists in `/Users/rcd58/citation-checker/tests`, so use a manual verification checklist instead of inventing weak automated coverage.

## Shared Design Contract

Use the same structural pattern in all three apps:

```html
<button id="help-btn" class="topbar-btn" type="button">Help</button>

<div id="help-modal" class="modal-overlay" hidden>
  <section class="modal-card help-modal-card" role="dialog" aria-modal="true" aria-labelledby="help-modal-title">
    <header class="modal-header">
      <h2 id="help-modal-title">Help</h2>
      <button type="button" class="modal-close-btn" data-close-help-modal>&times;</button>
    </header>
    <div class="help-modal-tabs" role="tablist">
      <button type="button" class="help-tab is-active" data-help-tab="overview">Overview</button>
    </div>
    <div class="help-modal-body">
      <section class="help-panel is-active" data-help-panel="overview">...</section>
    </div>
  </section>
</div>
```

Use app-specific localStorage keys:

```js
const HELP_STORAGE_KEY = "radcast-help-last-tab";
const HELP_STORAGE_KEY = "radtts-help-last-tab";
const HELP_STORAGE_KEY = "radcite-help-last-tab";
```

Use app-specific tab sets, but always follow:

1. Overview first
2. Task tabs in most-likely-task order
3. Troubleshooting last

## Task 1: Add Shared Help Modal Scaffolding To RADcast

**Files:**
- Modify: `/Users/rcd58/RADcast/src/radcast/templates/index.html`
- Modify: `/Users/rcd58/RADcast/src/radcast/static/ui.js`
- Modify: `/Users/rcd58/RADcast/src/radcast/static/ui.css`
- Test: `/Users/rcd58/RADcast/tests/test_api_ui.py`

- [ ] **Step 1: Write a failing RADcast template/UI test for the Help entry point**

Add or extend a test in `/Users/rcd58/RADcast/tests/test_api_ui.py` that checks the rendered page contains the Help trigger and Help modal shell.

```python
def test_index_contains_help_button_and_modal(client):
    response = client.get("/")
    text = response.text
    assert 'id="help-btn"' in text
    assert 'id="help-modal"' in text
```

- [ ] **Step 2: Run the RADcast test to verify it fails**

Run:

```bash
pytest /Users/rcd58/RADcast/tests/test_api_ui.py -k help -v
```

Expected: FAIL because the Help button and Help modal shell do not exist yet.

- [ ] **Step 3: Add the RADcast topbar Help button and modal shell**

Modify `/Users/rcd58/RADcast/src/radcast/templates/index.html`:

- add `Help` to the topbar actions beside the existing `Projects` / `Share` / `Admin` buttons
- keep it visible regardless of project-loaded state
- add a new Help modal after the existing share and worker setup modals
- add the RADcast tab list in this order:
  - Overview
  - Process audio
  - Clean up pauses and filler words
  - Generate captions
  - Use trim clip
  - Use helper processing
  - Troubleshooting

- [ ] **Step 4: Implement the minimal RADcast modal behavior**

Modify `/Users/rcd58/RADcast/src/radcast/static/ui.js`:

- cache Help DOM nodes near the existing modal node declarations
- add:

```js
const HELP_STORAGE_KEY = "radcast-help-last-tab";

function showHelpModal() {}
function hideHelpModal() {}
function selectHelpTab(tabKey) {}
function restoreHelpTab() {}
```

- use the same body/modal-open convention the app already uses for share/worker setup modals
- store the selected tab key in localStorage
- restore the saved tab on modal open, fallback to `overview`

- [ ] **Step 5: Add the minimal shared Help modal styling in RADcast**

Modify `/Users/rcd58/RADcast/src/radcast/static/ui.css`:

- extend existing modal styles with:
  - `.help-modal-card`
  - `.help-modal-tabs`
  - `.help-tab`
  - `.help-panel`
  - `.help-panel.is-active`
  - `.help-lead`
  - `.help-steps`
  - `.help-note`
- keep the Help modal visually consistent with the app’s existing modal system, not a separate design language

- [ ] **Step 6: Re-run the targeted RADcast test**

Run:

```bash
pytest /Users/rcd58/RADcast/tests/test_api_ui.py -k help -v
```

Expected: PASS

- [ ] **Step 7: Commit the RADcast scaffolding**

```bash
git -C /Users/rcd58/RADcast add \
  /Users/rcd58/RADcast/src/radcast/templates/index.html \
  /Users/rcd58/RADcast/src/radcast/static/ui.js \
  /Users/rcd58/RADcast/src/radcast/static/ui.css \
  /Users/rcd58/RADcast/tests/test_api_ui.py
git -C /Users/rcd58/RADcast commit -m "Add RADcast tabbed help modal scaffold"
```

## Task 2: Add Shared Help Modal Scaffolding To RADTTS

**Files:**
- Modify: `/Users/rcd58/RADTTS/src/radtts/templates/index.html`
- Modify: `/Users/rcd58/RADTTS/src/radtts/static/ui.js`
- Modify: `/Users/rcd58/RADTTS/src/radtts/static/ui.css`
- Test: `/Users/rcd58/RADTTS/tests/test_api_ui.py`

- [ ] **Step 1: Write a failing RADTTS template/UI test for the Help entry point**

Add or extend a test in `/Users/rcd58/RADTTS/tests/test_api_ui.py` that checks the rendered page contains the Help trigger and Help modal shell.

```python
def test_index_contains_help_button_and_modal(client):
    response = client.get("/")
    text = response.text
    assert 'id="help-btn"' in text
    assert 'id="help-modal"' in text
```

- [ ] **Step 2: Run the RADTTS test to verify it fails**

Run:

```bash
pytest /Users/rcd58/RADTTS/tests/test_api_ui.py -k help -v
```

Expected: FAIL because the Help button and Help modal shell do not exist yet.

- [ ] **Step 3: Add the RADTTS topbar Help button and modal shell**

Modify `/Users/rcd58/RADTTS/src/radtts/templates/index.html`:

- add `Help` to the topbar actions beside the existing `Projects` / `Share` / `Admin` buttons
- keep it visible regardless of project-loaded state
- add a new Help modal after the existing share / worker setup / reference trim modals
- add the RADTTS tab list in this order:
  - Overview
  - Generate audio
  - Use a custom voice
  - Prepare reference audio
  - Manage versions and outputs
  - Use helper processing
  - Troubleshooting

- [ ] **Step 4: Implement the minimal RADTTS modal behavior**

Modify `/Users/rcd58/RADTTS/src/radtts/static/ui.js`:

- cache Help DOM nodes near the existing modal declarations
- add:

```js
const HELP_STORAGE_KEY = "radtts-help-last-tab";

function showHelpModal() {}
function hideHelpModal() {}
function selectHelpTab(tabKey) {}
function restoreHelpTab() {}
```

- use the same modal open/close behavior already used for the other RADTTS modals
- store the selected tab key in localStorage
- restore the saved tab on modal open, fallback to `overview`

- [ ] **Step 5: Add the minimal shared Help modal styling in RADTTS**

Modify `/Users/rcd58/RADTTS/src/radtts/static/ui.css`:

- add the same Help modal class family used in RADcast, adapted to RADTTS’s modal tokens
- keep sizing, tab spacing, and content rhythm aligned with the RADcast implementation so users experience the same system in both apps

- [ ] **Step 6: Re-run the targeted RADTTS test**

Run:

```bash
pytest /Users/rcd58/RADTTS/tests/test_api_ui.py -k help -v
```

Expected: PASS

- [ ] **Step 7: Commit the RADTTS scaffolding**

```bash
git -C /Users/rcd58/RADTTS add \
  /Users/rcd58/RADTTS/src/radtts/templates/index.html \
  /Users/rcd58/RADTTS/src/radtts/static/ui.js \
  /Users/rcd58/RADTTS/src/radtts/static/ui.css \
  /Users/rcd58/RADTTS/tests/test_api_ui.py
git -C /Users/rcd58/RADTTS commit -m "Add RADTTS tabbed help modal scaffold"
```

## Task 3: Refactor RADcite’s Existing Help Modal To The Shared Tabbed Pattern

**Files:**
- Modify: `/Users/rcd58/citation-checker/app/templates/index.html`
- Modify: `/Users/rcd58/citation-checker/app/static/js/wysiwyg.js`
- Modify: `/Users/rcd58/citation-checker/app/static/css/wysiwyg.css`

- [ ] **Step 1: Preserve the existing RADcite Help trigger and replace only the modal internals**

Modify `/Users/rcd58/citation-checker/app/templates/index.html`:

- keep `helpTopbarBtn` as the existing entry point
- replace the current long static help body with:
  - shared tab strip
  - tab-keyed content panels
- use this RADcite tab order:
  - Overview
  - Start a project
  - Upload and review a document
  - Add or fix citations
  - Manage course references
  - Manage module readings
  - Share and export
  - Troubleshooting

- [ ] **Step 2: Replace RADcite’s open/close-only Help behavior with tab-state behavior**

Modify `/Users/rcd58/citation-checker/app/static/js/wysiwyg.js`:

- keep `showHelpModal()` and `hideHelpModal()` as the public entry points used by the template
- add:

```js
const HELP_STORAGE_KEY = "radcite-help-last-tab";

function selectHelpTab(tabKey) {}
function restoreHelpTab() {}
```

- update the current Help modal behavior so opening Help restores the last viewed tab
- do not reintroduce the old bug where Help was hidden on some screens; Help should remain available in all app states

- [ ] **Step 3: Replace the legacy RADcite Help section styling with the shared tabbed layout**

Modify `/Users/rcd58/citation-checker/app/static/css/wysiwyg.css`:

- retire or stop relying on `.help-section` as the primary structure
- add styles for:
  - `.help-modal-tabs`
  - `.help-tab`
  - `.help-panel`
  - `.help-lead`
  - `.help-steps`
  - `.help-note`
- keep the Help button styling unchanged unless it is required for consistency with the tabbed modal behavior

- [ ] **Step 4: Run lightweight verification on the RADcite front-end file**

Run:

```bash
node --check /Users/rcd58/citation-checker/app/static/js/wysiwyg.js
```

Expected: PASS

- [ ] **Step 5: Commit the RADcite refactor**

```bash
git -C /Users/rcd58/citation-checker add \
  /Users/rcd58/citation-checker/app/templates/index.html \
  /Users/rcd58/citation-checker/app/static/js/wysiwyg.js \
  /Users/rcd58/citation-checker/app/static/css/wysiwyg.css
git -C /Users/rcd58/citation-checker commit -m "Refactor RADcite help modal into tabbed layout"
```

## Task 4: Write App-Specific Help Content For All Three Apps

**Files:**
- Modify: `/Users/rcd58/RADcast/src/radcast/templates/index.html`
- Modify: `/Users/rcd58/RADTTS/src/radtts/templates/index.html`
- Modify: `/Users/rcd58/citation-checker/app/templates/index.html`

- [ ] **Step 1: Write the RADcast Help copy**

Populate the RADcast tabs with:

- Overview: what RADcast does, when to use it, first-run processing flow
- Process audio: choose audio, trim, process, download result
- Clean up pauses and filler words: when to use the cleanup toggles and what they change
- Generate captions: SRT/VTT behavior and reviewed-caption expectation
- Use trim clip: how the trim rail works and that it is non-destructive
- Use helper processing: helper status, fallback behavior, what to expect
- Troubleshooting: slow jobs, helper offline, caption review, upload/selection issues

- [ ] **Step 2: Write the RADTTS Help copy**

Populate the RADTTS tabs with:

- Overview: what RADTTS does and the basic generation workflow
- Generate audio: create/open project, enter text, generate, review versions
- Use a custom voice: choose or configure a custom voice path
- Prepare reference audio: trim/select a useful reference sample
- Manage versions and outputs: completed versions, metadata, playback, save, folder path
- Use helper processing: helper status, fallback, what happens if no helper is live
- Troubleshooting: helper issues, long jobs, generation failures, reference problems

- [ ] **Step 3: Write the RADcite Help copy**

Populate the RADcite tabs with:

- Overview: what RADcite does and the high-level project workflow
- Start a project: create/open project and choose structure
- Upload and review a document: upload, parse, move between document and citations
- Add or fix citations: how to use citation actions and why statuses change
- Manage course references: use project/course references and edit/delete actions
- Manage module readings: reading groups, APA readiness, and reading maintenance
- Share and export: share access and export output behavior
- Troubleshooting: missing jumps, missing highlights, upload issues, reading/reference confusion

- [ ] **Step 4: Keep the content structure uniform**

For each tab:

- add a short lead paragraph
- add numbered steps
- add notes only where they prevent common mistakes

Do not add screenshots, nested accordions, or deeply technical copy.

- [ ] **Step 5: Commit the content pass**

```bash
git -C /Users/rcd58/RADcast add /Users/rcd58/RADcast/src/radcast/templates/index.html
git -C /Users/rcd58/RADcast commit -m "Write RADcast help tab content"

git -C /Users/rcd58/RADTTS add /Users/rcd58/RADTTS/src/radtts/templates/index.html
git -C /Users/rcd58/RADTTS commit -m "Write RADTTS help tab content"

git -C /Users/rcd58/citation-checker add /Users/rcd58/citation-checker/app/templates/index.html
git -C /Users/rcd58/citation-checker commit -m "Write RADcite help tab content"
```

## Task 5: Verify Shared Behavior And Polish Cross-App Consistency

**Files:**
- Modify if needed:
  - `/Users/rcd58/RADcast/src/radcast/static/ui.css`
  - `/Users/rcd58/RADTTS/src/radtts/static/ui.css`
  - `/Users/rcd58/citation-checker/app/static/css/wysiwyg.css`
  - `/Users/rcd58/RADcast/src/radcast/static/ui.js`
  - `/Users/rcd58/RADTTS/src/radtts/static/ui.js`
  - `/Users/rcd58/citation-checker/app/static/js/wysiwyg.js`

- [ ] **Step 1: Run focused automated checks**

Run:

```bash
pytest /Users/rcd58/RADcast/tests/test_api_ui.py -v
pytest /Users/rcd58/RADTTS/tests/test_api_ui.py -v
node --check /Users/rcd58/RADcast/src/radcast/static/ui.js
node --check /Users/rcd58/RADTTS/src/radtts/static/ui.js
node --check /Users/rcd58/citation-checker/app/static/js/wysiwyg.js
```

Expected: PASS

- [ ] **Step 2: Run a manual cross-app checklist**

Verify in each app:

- Help button is visible before and after loading/opening a project
- Help modal opens from every screen state
- Overview is first on first open
- Selecting another tab persists across close/reopen
- Task tabs are app-specific and ordered by likely use
- Troubleshooting is last
- Close, Escape, and overlay click behavior match the local modal conventions

- [ ] **Step 3: Fix any drift in spacing, tab sizing, or active-state styling**

If any app looks inconsistent:

- adjust only the Help modal-specific classes
- do not refactor unrelated topbar or modal styling

- [ ] **Step 4: Run full verification before completion**

Run:

```bash
pytest /Users/rcd58/RADcast/tests -q
pytest /Users/rcd58/RADTTS/tests -q
node --check /Users/rcd58/citation-checker/app/static/js/wysiwyg.js
```

Expected:

- RADcast test suite passes
- RADTTS test suite passes
- RADcite Help JS syntax check passes

- [ ] **Step 5: Commit the final cross-app polish**

```bash
git -C /Users/rcd58/RADcast commit -am "Polish RADcast help modal behavior"
git -C /Users/rcd58/RADTTS commit -am "Polish RADTTS help modal behavior"
git -C /Users/rcd58/citation-checker commit -am "Polish RADcite help modal behavior"
```
