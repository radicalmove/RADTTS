# Shared Help Modal Rise-Style Redesign

## Summary

Refine the first shared help-modal rollout in RADcite, RADcast, and RADTTS so it feels more like a compact documentation experience than a small utility dialog. The revised design keeps the shared interaction model, but changes the visual treatment, content density, and topbar entry-point alignment.

## Goals

- Make the Help button in RADcast and RADTTS match RADcite's color treatment and roughly the same topbar placement.
- Keep Help available on every screen in all three apps.
- Redesign the modal to be wider and taller than the first rollout.
- Use a top-aligned tab strip that feels like filing-cabinet tabs rather than thin navigation pills.
- Allow tabs to wrap to two compact rows when needed.
- Make the content region a scrollable article with more detailed guidance.
- Add richer `Tip`, `Note`, and `Troubleshooting` callout blocks inside help articles.
- Preserve last-opened-tab behavior per app.

## Non-Goals

- Rework unrelated topbar buttons outside the Help button placement/color alignment.
- Introduce screenshots, videos, or media embeds.
- Add server-backed help content or a CMS.

## User Experience

### Topbar Entry Point

RADcite remains the visual reference. RADcast and RADTTS should move their Help button into the same visual cluster and use the same color styling so the trigger feels identical across all three apps.

### Modal Layout

The revised modal should:

- open noticeably wider and taller than the current version
- use a fixed header area
- use a fixed tab strip directly under the header
- allow the tab strip to wrap to a second compact row
- keep the article body as the primary scrolling surface

### Tab Style

Tabs should feel like document tabs:

- chunkier than the current slim buttons
- visually grouped as a set of labeled sections
- clearly active when selected
- readable even when multiple rows are present

### Content Style

Each tab should read like a compact documentation article:

- short orientation paragraph
- section headings where useful
- numbered steps
- inline callout boxes for tips, notes, or edge cases

The content should be more detailed than the first rollout, not merely rearranged.

## Per-App Content Expectations

The overall pattern remains:

1. Overview
2. Task tabs ordered by most likely use
3. Troubleshooting last

The existing task lists from the first rollout remain valid, but each article should be expanded with more complete instructions and contextual notes.

## Architecture

The shared behavior contract remains the same:

- modal open/close behavior
- per-app last-tab persistence
- keyboard-accessible tabs
- app-specific content embedded directly in each app

This redesign is primarily a template/CSS/content pass, with only light JS adjustment where the tab strip or focus behavior depends on the new structure.

## Testing Strategy

- Preserve the existing focused Help behavior tests in RADcast and RADTTS.
- Update any assertions that depend on class names or structure if necessary.
- Verify keyboard tab switching still works.
- Manually verify in RADcite that:
  - Help opens on all screens
  - wrapped tabs remain usable
  - the article body scrolls while the header/tab strip stays stable
  - last-tab persistence still works
