---
type: belief
id: frag-helpjson-surface-matches-argparse
provenance: 2026-11-24 — R06 review: --chime declared boolean while argparse demanded a value; config and listen leaked onto the cordis_expose surface
ts: 2026-11-24
---

`--help-json` is a **machine contract**, not documentation: every
command it lists is callable by the harness, and every declared
parameter must be spelled exactly as argparse accepts it. A schema that
says `boolean` where argparse expects a value (`--chime true`) makes the
harness emit a bare flag and the CLI fail with `expected one argument` —
the contract lied about its own surface. Declared enums and argparse
`choices` must be the same set.

The ruling: `cordis_expose` lists only **agent-safe** commands.
Anything that writes host config (`config` -> `<host>/voice.json`) or
blocks as a daemon (`listen`, `while True` hotkey loop) stays a CLI
subparser but is never emitted in `commands`. Hiding a command removes
its parameter schema from the contract — argparse remains the source of
truth for how hidden commands are invoked by humans.

Open questions: whether `serve` should also leave the exposed surface
(klanker filters it downstream today); whether hidden commands need a
separate `cli_only` manifest for auditability.
