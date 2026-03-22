# Shared Help Modal Rise-Style Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the shared help-modal rollout across RADcite, RADcast, and RADTTS so the Help entry point is visually aligned and the modal feels like a larger, article-style, Rise-inspired help surface.

**Architecture:** Keep the current shared behavior contract and per-app content model, but restyle the modal shell and tab strip, expand the article content, and align the Help button placement/color in RADcast and RADTTS to RADcite. The work remains local to each app and can be implemented in parallel.

**Tech Stack:** Server-rendered HTML templates, vanilla JavaScript, CSS, browser localStorage, pytest, Node-based focused JS tests where already present.

---

## Task 1: RADcast Rise-Style Help Refresh

**Files:**
- Modify: `/Users/rcd58/RADcast/src/radcast/templates/index.html`
- Modify: `/Users/rcd58/RADcast/src/radcast/static/ui.css`
- Modify: `/Users/rcd58/RADcast/src/radcast/static/ui.js`
- Test: `/Users/rcd58/RADcast/tests/test_api_ui.py`
- Test: `/Users/rcd58/RADcast/tests/help_modal_behavior.test.js`

- [ ] Restyle the topbar Help trigger to match RADcite's color and visual position.
- [ ] Widen and heighten the Help modal shell.
- [ ] Redesign the tab strip into chunkier top tabs with two-row wrapping support.
- [ ] Convert tab content into richer article sections with note/tip callouts.
- [ ] Verify localStorage restore and keyboard tab behavior still work.
- [ ] Run focused RADcast Help tests.

## Task 2: RADTTS Rise-Style Help Refresh

**Files:**
- Modify: `/Users/rcd58/RADTTS/src/radtts/templates/index.html`
- Modify: `/Users/rcd58/RADTTS/src/radtts/static/ui.css`
- Modify: `/Users/rcd58/RADTTS/src/radtts/static/ui.js`
- Test: `/Users/rcd58/RADTTS/tests/test_api_ui.py`
- Test: `/Users/rcd58/RADTTS/tests/help_modal_behavior_test.js`

- [ ] Restyle the topbar Help trigger to match RADcite's color and visual position.
- [ ] Widen and heighten the Help modal shell.
- [ ] Redesign the tab strip into chunkier top tabs with two-row wrapping support.
- [ ] Convert tab content into richer article sections with note/tip callouts.
- [ ] Verify localStorage restore and keyboard tab behavior still work.
- [ ] Run focused RADTTS Help tests.

## Task 3: RADcite Rise-Style Help Refresh

**Files:**
- Modify: `/Users/rcd58/citation-checker/app/templates/index.html`
- Modify: `/Users/rcd58/citation-checker/app/static/css/wysiwyg.css`
- Modify: `/Users/rcd58/citation-checker/app/static/js/wysiwyg.js`

- [ ] Keep the existing Help trigger as the visual reference.
- [ ] Widen and heighten the Help modal shell.
- [ ] Redesign the tab strip into chunkier top tabs with two-row wrapping support.
- [ ] Convert tab content into richer article sections with note/tip callouts.
- [ ] Verify last-tab restore and keyboard tab behavior still work.
- [ ] Run syntax/manual verification appropriate to RADcite.

## Task 4: Review And Deploy

**Files:**
- Verify all touched files above

- [ ] Re-run focused automated checks in RADcast and RADTTS.
- [ ] Run syntax/manual checks for RADcite.
- [ ] Deploy the three updated review branches to the dev instances.
- [ ] Verify the served assets and dev endpoints before handing back for review.
