# Shared Help Modal Redesign For RADcite, RADcast, And RADTTS

## Summary

Redesign the help experience across RADcite, RADcast, and RADTTS so all three apps use the same modal structure, the same tab interaction model, and the same visual behavior, while keeping the actual help content specific to each app.

The goal is that if a user learns the help system in one app, they can use it immediately in the other two apps without relearning the interface.

## Goals

- Use the existing topbar `Help` entry point pattern from RADcite as the reference.
- Make `Help` available on every screen in RADcite, RADcast, and RADTTS.
- Use one shared modal structure across all three apps.
- Give each app a custom overview tab and custom task tabs.
- Order task tabs from most likely task to less likely task.
- Remember the last-opened help tab per app so reopening the modal reduces repeated clicks.
- End each app’s help sequence with a troubleshooting tab.

## Non-Goals

- Centralize help content into a shared CMS or editable content store.
- Introduce search, accordions, or nested help navigation in the first version.
- Add media-heavy help content such as screenshots or videos in the first version.
- Rework unrelated modal behavior outside the help system.

## User Experience

### Shared Behavior

Each app exposes a `Help` button in the topbar on every screen, including project-selection or empty states.

Opening `Help` shows a modal with:

- a modal title row
- a horizontal tab strip
- a content panel for the selected tab
- a close control

The active tab is visually obvious and the tab set behaves the same way in all three apps.

The modal reopens on the last tab viewed for that specific app by storing the selected tab key in browser storage. If no saved tab exists, the modal opens on the first overview tab.

### Content Pattern For Every Tab

Each tab follows the same content pattern:

1. Task or section title
2. Short description explaining what the task is for
3. Numbered step-by-step instructions
4. Inline notes only where they add value

This keeps the writing style predictable even though the content differs by app.

### Overview Tab Pattern

The first tab in every app is an overview/getting-started tab that explains:

- what the app does
- when to use it
- the basic first-run workflow

The content is app-specific, not shared boilerplate.

### Task Tab Pattern

Middle tabs are specific tasks named by user outcome, not by UI region. They are ordered by likelihood of use.

Initial task groups:

#### RADcast

- Process audio
- Clean up pauses and filler words
- Generate captions
- Use trim clip
- Use helper processing

#### RADTTS

- Generate audio
- Use a custom voice
- Prepare reference audio
- Manage versions and outputs
- Use helper processing

#### RADcite

- Start a project
- Upload and review a document
- Add or fix citations
- Manage course references
- Manage module readings
- Share and export

### Troubleshooting Tab Pattern

The final tab in every app is troubleshooting. It lists the most common problems, likely causes, and what the user should try next.

## Architecture

### Shared Structural Pattern

The implementation should use the same conceptual help-modal component shape in all three apps:

- topbar help trigger
- modal shell
- tab navigation
- content renderer
- per-app last-tab persistence

This does not require creating a shared package or cross-repo dependency. The structure can be implemented separately inside each app while following the same markup and behavior contract.

### Content Storage

Help content is written directly into each app, not loaded from an external source.

Each app should define:

- a tab list
- a content object or equivalent tab-keyed structure

That structure should be easy to extend later if task tabs are added or rewritten.

### Persistence

Each app stores its own last-opened help tab key in local browser storage using an app-specific key to avoid collisions.

## Interaction Design

### Trigger Availability

- RADcite keeps the existing topbar help entry point and updates it to the new modal structure.
- RADcast adds the same help button into the topbar and keeps it visible on all screens.
- RADTTS adds the same help button into the topbar and keeps it visible on all screens.

### Open And Close Behavior

- Clicking `Help` opens the modal.
- Clicking the close button closes it.
- Clicking outside the modal closes it if that matches current app modal conventions.
- Escape closes it if current modal conventions support Escape.

The help modal should follow the dominant modal accessibility and focus behavior already used in each app instead of inventing a separate rule set.

### Tabs

- Tabs switch immediately without closing the modal.
- The selected tab is saved when switched.
- Reopening the modal restores the saved tab for that app.

## Data Flow

1. User clicks the topbar `Help` button.
2. App opens the help modal.
3. App looks up the last-saved tab key for that app.
4. If the key exists and is valid, that tab is selected.
5. Otherwise, the overview tab is selected.
6. When the user changes tabs, the app updates the selected tab state and writes the tab key to browser storage.

No server interaction is required.

## Error Handling

- If browser storage is unavailable, the modal should still work and simply default to the overview tab.
- If a stored tab key is invalid after a future content change, fall back to the overview tab.
- If a help button is rendered before project data is ready, it should still open help because the help system should not depend on project state.

## Testing Strategy

### Manual Verification

For each app:

- Help button is visible on project-selection and in-project screens.
- Help modal opens and closes correctly.
- Overview tab loads first on first open.
- Switching tabs updates the content correctly.
- Reopening help restores the last viewed tab.
- Troubleshooting is the final tab.

### Automated Coverage

Where the current codebase supports lightweight UI tests or state tests:

- tab-state restore logic
- invalid stored-tab fallback
- help-button visibility outside loaded-project states

At minimum, implementation should include regression-safe UI state tests for the selected tab behavior in RADcast and RADTTS and equivalent coverage or a manual verification checklist for RADcite if its current test surface is thinner.

## Rollout Notes

Implement the redesign as a help-only change. Do not combine it with unrelated modal or topbar refactors.

Use one consistent visual language across all three apps so users can transfer what they learn from one app to the others.
