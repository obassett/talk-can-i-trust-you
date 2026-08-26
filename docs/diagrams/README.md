# Diagrams

Presenterm shows **PNGs** on the slides. We author the PNGs in **Excalidraw** and
export them here — no live rendering, no d2/chromium at present time.

## Files

| Base name          | `.excalidraw` (edit this)      | `.png` (presenterm loads this)       |
| ------------------ | ------------------------------ | ------------------------------------ |
| `round1-system`    | Gateway → … → Warehouse chain  | slide "Round 1 · The System"         |
| `castle`           | walled castle / implicit trust | slide "The Castle"                   |
| `attestation`      | Server → Agent → Workload      | slide "Concept 4 · Attestation"      |
| `partner-endpoint` | compromised partner → Dispatch | slide "Round 3 · Omen Rides…"        |

`slides.md` references the PNGs as `![...](diagrams/<name>.png)`. Keep the **same
basename** on export and the slide picks it up with no edit.

> The `.png` files currently checked in are **auto-generated placeholders** (from
> the matching `.svg`, via `rsvg-convert`). They render fine, but the intent is
> for you to open the `.excalidraw`, refine it, and export over the top.

## Editing

Open the `.excalidraw` file in either:

- **excalidraw.com** — *Menu → Open*, pick the file.
- **VS Code** — the *Excalidraw* extension (`pomdtr.excalidraw-editor`) edits
  `.excalidraw` files inline.

## Exporting (the settings that matter)

*Menu → Export image* (or select all → right-click → *Copy to PNG*), then:

- **Background: OFF** — transparent, so it sits on the dark slide. This is the one
  setting that ruined earlier attempts; don't skip it.
- **Scale: 3×** — crisp on a projector. (Stored in each scene's `appState`.)
- Save as `diagrams/<name>.png`, overwriting the placeholder.

## Palette (theme-agnostic — reads on light *and* dark slides)

The deck runs light on a projector (`presenterm --theme light slides.md`) and dark
for screen-share (`presenterm --theme dark slides.md`). Presenterm can't swap
images per theme, so each diagram must work on **both** backgrounds. Rules:

- Box fill `#313244` (dark) · label text `#cdd6f4` (light) — a "dark card" that
  reads on either background. Keep labels **inside** a filled box.
- Strokes / arrows / outlines `#6c6ff5` (mid indigo) — contrasts on white *and*
  near-black. (Plain lavender `#b4befe` vanished on light — don't use it for lines.)
- Faint / mesh lines and **any free-standing label** `#6c7086` (mid gray) — light
  text would disappear on a projector, so never put light text on the bare canvas.

## Adding a new diagram

1. Draw it in Excalidraw with the palette above, save `diagrams/<name>.excalidraw`.
2. Export a transparent 3× PNG to `diagrams/<name>.png`.
3. Add `![<name>](diagrams/<name>.png)` to the slide in `slides.md`.
