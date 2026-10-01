# Changelog

## 1.1.0 — 2026-09-30

- Added an opt-in, loopback-only appearance panel with responsive HTML/CSS and no web dependencies.
- Added 10 styles and an offline searchable Unicode/emoji picker, including per-marker overrides.
- Curated color palettes by semantic role and predominant emoji color, with explicit exceptions where no clear equivalent exists.
- Added read-only previews, enabled/max-badge controls, atomic preference saves, snapshots and conflict-aware undo.
- Made completed/unknown theme icons effective unless explicitly overridden by legacy configuration.
- Kept custom marker history for safe title recognition after theme changes and undo.
- Preserved hybrid defaults and all lifecycle classification; no bulk renaming or model calls occur in the panel.

## 1.0.0 — 2026-09-30

- Preserved the existing lifecycle behavior as the user-designated stable baseline.
- Re-ran all 23 repository tests successfully before appearance work.
- Kept the historical source and documented live-validation limits intact.
- Adopted CC BY-NC 4.0 for version 1.0.0 and subsequent releases at the author's request.

## 0.2.0 — 2026-09-28

- Replaced cross-process live-state guessing with an event-authoritative reducer and local store.
- Added `waiting_on_user`, configurable themes, profiles, modifiers and context/long-run telemetry.
- Added atomic thread records, intent/applied journal, snapshots, granular conflict-safe rollback and clean.
- Added late reconciliation, three-attempt `Stop` reads, legacy migration and sanitized fixture capture.
- Added preview, status/doctor, render-all, on/off and profile commands.
- Split runtime into pure reducer/renderer, evidence sources and a single title-writer boundary.
- Kept the v0.1 Python API and source entry point compatible where practical.
- Preserved the installed v0.1 sources and architecture without private runtime
  data, and documented the executed local migration to trusted v0.2 hooks.
- Restored structured project slugs with existing-tag, configured-root, Git-origin
  and checkout-directory precedence; legacy state markers now seed migrated views.

## 0.1.0 — 2026-09-28

- Established Thread State branding, `/thread-state` skill and repository identity.
- Packaged a standard-library event handler and an allowlisted local RPC client.
- Removed polling and prose classification from the repository runtime.
- Added direct UUID lookup, per-thread locks, bounded RPC waits and child cleanup.
- Added dry-run inspection, reversible hook merging, pre-write ledger and readback.
- Preserved editorial titles by skipping unsafe/overlength updates.
- Documented experimental protocol dependencies and outstanding live validation.

The earlier personal thread-status prototype is outside this release and remains
unchanged by repository creation. No migration, GitHub publication or plugin
marketplace installation is implied by this commit.
