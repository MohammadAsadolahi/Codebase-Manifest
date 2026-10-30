# Output contract — version 1

All generated files belong in the target repository's `.architectureY/` directory. Output is UTF-8 Markdown. Reuse the exact headings and filenames across agents; the existing Python CLI uses these filenames too.

## Required overview files

| File | Required headings |
| --- | --- |
| `PROJECT_SUMMARY.md` | `# {Project Name} — General Architecture & Feature Overview`; `## 1. Project Summary` |
| `HIGH_LEVEL_ARCHITECTURE.md` | `## 2. High-Level Architecture`; `### Topology Map`; `### Architecture Boundaries`; `### Dependency Composition & Wiring`; `### Executable Entry Points` |
| `FEATURE_CATALOG.md` | `## 3. Feature Catalog`; `### Frozen Feature Manifest`; `### Feature Details` |
| `01_GENERAL_ARCHITECTURE.md` | Exact content of the three files above, in that order, separated with blank lines; do not generate independently |

**Project summary:** one concise purpose paragraph and an `Aspect | Technology` table of verified major technologies. Avoid route inventories, guessed infrastructure, and detail better covered by feature docs.

**Topology Map:** use these seven lines, with each value supported by startup/composition evidence; use `(none)` if absent.

```text
[Clients / External Actors: ...]
  -> [Ingress Interfaces: ...]
  -> [Runtime Processes: ...]
  -> [Application Boundaries: ...]
  -> [Specialized Runtime Subsystem: ...]
  -> [Async / Realtime Paths: ...]
  -> [Stateful / External Systems: ...]
```

**Architecture Boundaries:** exactly seven bullets, using the seven labels above in the same order. **Executable Entry Points:** table columns `Binary | Path | Purpose`. Mark one-shot CLIs as entry points but not persistent runtime units.

**Frozen Feature Manifest:** table with columns exactly:

```markdown
| Feature Key | Dominant Root | Standalone Reason | Merged Boundaries |
| --- | --- | --- | --- |
```

Sort feature keys alphabetically on first generation, with code-derived names, assigning numbers starting at 1. Under `### Feature Details` provide one `### Feature N: {Feature Key}` paragraph per manifest row, in the same order; three short sentences: capability, owning root/files, key behavior/integrations. On refresh retain identities and ordering, appending genuinely new features rather than renumbering existing features.

## Detailed feature documents

Filename `{N:02d}_{slug}.md`, where `slug` replaces every run of characters other than `A-Z`, `a-z`, `0-9` with `_`, and strips leading/trailing underscores. Feature key and number must match the frozen catalog.

First line: `# Feature N: {Feature Key} -- Flows & Key Files`.

Required sections, in order:

1. `## Overview` — three concise sentences: what the feature does; dominant root and verified primary files; verified integrations (or none).
2. `## Flow 1: {first owned method}`, `## Flow 2: ...` etc. Each has one fenced `text` block: concrete ingress/trigger first, at most six `  -> path/to/file.ext: Symbol` lines, then `  <- stable outcome`. Include meaningful business effects, not boilerplate helper reads. Every step path must exist and identify a real symbol.
3. `## Cross-Feature Coupling`, with the following exact six subheadings:
   - `### Outbound Dependencies (this feature calls INTO other features)`
   - `### Inbound Dependencies (other features call INTO this feature)`
   - `### Hidden Side Effects`
   - `### Events Published`
   - `### Events Consumed`
   - `### Files Touched by Cross-Feature Coupling`
4. `## Database Schema & Relationships`, with:
   - `### Persistence Conventions`
   - `### Models Involved in This Feature`

Where present, render coupling tables with the following header columns:

- Outbound: `Target Feature | Mechanism | Method Called | Trigger`
- Inbound: `Source Feature | Mechanism | Detail`
- Events Published: `Event | Trigger | Payload Keys`
- Events Consumed: `Event | Source | Effect`
- Coupling Files: `File | Reason`

Use `None.` for genuinely absent flows, couplings, events, or models. No fabricated placeholders that could be confused for facts.

**Named models:** add `#### ModelName (table: verified_table_or_unknown)`, then a fenced `text` block:

```text
file: path/to/model_file.ext
primary key: ...
feature-relevant fields: ...
feature-relevant constraints: ...
feature-relevant relations: ...
```

Include only named models directly read/written by the verified flows or direct side effects. Preserve source field names and declaration order; omit unrelated fields.

## Output discipline

- Prefer a smaller accurate feature boundary over a speculative larger one.
- Use the *same* catalog keys for every cross-feature dependency; don't invent synonyms.
- All references to source files must be relative to the repository root.
- Don't use generated documentation to substantiate claims about executable behavior.
- Allow minimal variation across languages/frameworks while preserving the headings and file layout.
