# AstraFactory desktop

Electrobun native window, Bun backend, React workspace, and Three.js CAD viewer. The desktop code is isolated from the simulation package.

## Run

Requires Bun, macOS, and a signed-in Codex installation. From this directory:

```sh
bun install
bunx electrobun prepare
bun run desktop
```

`bun run dev` runs the same workspace without the native shell. Its local URL is recorded in `.local/connection.json`. Do not share that file: its URL contains the local access token. `CODEX_BIN` can override the Codex executable.

## Working capabilities

- Create, name, inspect, follow up, steer, and interrupt real Codex sessions. Roles provide task instructions; they are not file ownership enforcement.
- Use the local ChatGPT account through Codex App Server, without embedding an API key. Available models come from the account.
- Explicit command/file and MCP tool approval UI.
- Inspect STL geometry, mesh-based URDF at its zero joint pose, self-contained GLB, images, text reports, and recorded simulation videos.
- Automatically index actual files under `tasks`, `runs`, `docs`, and `assets/robots`.
- Attach human or agent reviews to SHA-256 artifact versions.
- Authenticated local MCP tools: `workspace_status`, `list_artifacts`, `read_artifact`, `review_artifact`.

## Boundaries

This is a development app, not a signed distributable. The launch command supplies absolute workspace and UI paths. The simulation viewer plays recorded evidence; it does not host a live MuJoCo process or establish that a policy succeeded. URDF visualization does not simulate dynamics, joint limits, or collisions. External glTF dependencies and URDF package URI resolution are not implemented.

Sessions persist in the usual Codex store and can be read in the desktop app. Independent App Server instances do not share live runtime ownership: avoid driving the same active turn from both apps. Reopening AstraFactory marks interrupted local sessions disconnected; a follow-up resumes them with a fresh MCP connection.

Agents can read text via MCP and inspect local images through their normal file tools. Binary images/video are reviewed in the human viewer; the MCP text reader is not a video analysis tool. Role conflicts, automatic agent-to-agent dispatch, and enforced design approval gates remain future work. No activity or outcome is fabricated.

## Validation

`bun run typecheck` and `bun test`. Integration verified against the installed Codex App Server: ChatGPT authentication, an Astra thread, approved MCP artifact listing, final response, and persisted history retrieval. Native Electrobun/Bun launch and CAD rendering verified visually.
