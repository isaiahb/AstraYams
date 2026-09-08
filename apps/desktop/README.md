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

- Prompt-led project catalog; new prompts create a project folder, brief, and lead session.
- Explicit ID, ME, EE, software, manufacturing, and simulation workstreams with artifact stages and research spikes.
- Engineering change proposals and handoffs linked to the source file hash, assignable to a real engineer session.
- Preloaded arm assets / recorded experiments and a separately labeled lunar concept brief.

- Create, name, inspect, follow up, steer, and interrupt real Codex sessions. Roles provide task instructions; they are not file ownership enforcement.
- Use the local ChatGPT account through Codex App Server, without embedding an API key. Available models come from the account.
- Explicit command/file and MCP tool approval UI.
- Inspect STL geometry, mesh-based URDF at its zero joint pose, self-contained GLB, images, text reports, and recorded simulation videos.
- Automatically index actual files under `tasks`, `runs`, `docs`, and `assets/robots`, and project-owned `apps/desktop/workspaces` folders.
- Attach human or agent reviews to SHA-256 artifact versions.
- Authenticated local MCP tools: `workspace_status`, `list_artifacts`, `read_artifact`, `review_artifact`, `publish_artifact`, `create_work_item`. Tool artifact access is scoped to its project; this is not a filesystem sandbox for agent shell tools.

## Boundaries

This is a development app, not a signed distributable. The launch command supplies absolute workspace and UI paths. The simulation viewer plays recorded evidence; it does not host a live MuJoCo process or establish that a policy succeeded. URDF visualization does not simulate dynamics, joint limits, or collisions. External glTF dependencies and URDF package URI resolution are not implemented.

Sessions persist in the usual Codex store and can be read in the desktop app. Independent App Server instances do not share live runtime ownership: avoid driving the same active turn from both apps. Reopening AstraFactory marks interrupted local sessions disconnected; a follow-up resumes them with a fresh MCP connection.

Agents can read text via MCP and inspect local images through their normal file tools. Binary images/video are reviewed in the human viewer; the MCP text reader is not a video analysis tool. General team scheduling, role conflicts, and enforced design approval gates remain future work. No activity or outcome is fabricated.

## Validation

`bun run typecheck` and `bun test`. Integration verified against the installed Codex App Server: ChatGPT authentication, an Astra thread, approved MCP artifact listing, final response, and persisted history retrieval. Native Electrobun/Bun launch and CAD rendering verified visually.

Project metadata, reviews, assignments, and organization persist in `.local/workspace.json`; new project files live in ignored `workspaces/` folders. They remain local until explicitly exported or committed. Legacy assets are referenced in place. The lunar brief is a research starting point, not a completed engineering example.

The feedback loop supports one bounded automatic revision → independent re-test cycle per proposal. The user supplies fixed acceptance criteria; the engineer submits a separate artifact through MCP, then the tester starts when that turn completes. The tester executes the task-specific procedure with its normal tools and submits an evidence report. This orchestrates real sessions; it does not embed a physics engine or independently prove an agent’s reported pass. No automatic retry or paid GPU launch is performed.

Changed evidence, missing submissions, failed/interrupted sessions and app restarts stop the cycle with a visible blocker. A failed test requests a new revision; it does not change acceptance criteria. New cycles require new proposals. All source, revision and test report hashes are retained. The UI exposes each session and report for review.

Workflow tests use a deterministic session adapter to verify dispatch, stale-version detection, session ownership, interruption, and bounded stopping. They are software tests, not robot simulation evidence.
