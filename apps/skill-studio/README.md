# Astra Skill Studio

A separate prompt-first interface for describing a skill for the existing simulation robot. Preserves the broader desktop app.

The hero loads `assets/robots/yam/v1/yam.urdf` and its original STL visuals through the desktop's authenticated artifact endpoint. These are the YAM geometry files referenced by `tasks/yam_contact_insertion/scene.xml`. Original robot licenses remain in the asset directory. No Mind Robotics models, logos, code or artwork are copied. The independently implemented cel shader uses warm off-white, teal, dark silhouette outlines and quantized lighting inspired by the reference site. The display pose and gentle motion are illustrative; they are not a recorded policy execution.

## Run

Start `apps/desktop` first. Then in this directory:

```sh
bun install
bun run dev
```

The authenticated local URL is saved in `.local/connection.json` (ignored). Restart this server if the desktop backend changes its port or token. The dev server binds only to loopback and proxies API requests to that existing backend; it does not inject authorization into anonymous requests.

The example buttons populate the prompt. Create simulation creates a real isolated project and a Simulation agent assignment through the existing backend, then opens that workspace. It does not automatically claim training or task success, and does not authorize paid GPU jobs. The existing insertion demo is directly linked.

Reduced-motion preferences disable the decorative joint animation. Small screens reduce the background prominence for readable input. The shader uses actual geometry; changing its finish does not modify simulation assets.

## Skill library and active runs

New prompt submissions save persistent skill history in `.local/skills.json`, including the actual desktop project and engineer session IDs. The UI polls the real session status; a completed engineering chat is shown as ready for review, not as a trained or passing skill.

The simulation thread can publish `runs/skill-studio/skills.json` with `{schema_version:1, skills:[...]}`. Each entry supports `id`, `title`, `description`, `status`, `phase`, `updated_at`, `project_id`, `preview_path`, `manifest_path`, `message`, `metrics` and `artifacts`. Paths are repository-relative. Status values: planning, building, training, evaluating, complete, failed, blocked. The app reads this file without modifying simulation outputs. Registered runs override local entries with the same ID.

Prior results are read from `runs/hackathon-demo/final-demo.json`. The verified state-based insertion and unpromoted visual candidate are represented separately. Each skill has Simulation, Results and Artifacts tabs. The scope labels, baseline seed caveats and limitations remain visible in its evidence.

Deep link to a skill using `?skill=machine-tending-v1` (retain the authenticated fragment). `bun test` checks persistence, de-duplication and merging active runs with prior results.

## Native desktop window

With the local backend and Skill Studio server running, use `bun run desktop`. This builds and opens a dedicated Electrobun app named **Astra Skill Studio**, with bundle identifier `dev.astrafactory.skills`, directly on the cel-shaded skill prompt and library. Its development bundle is `build/dev-macos-arm64/Astra Skill Studio-dev.app`. Runtime URLs and tokens remain in ignored `.local` files.

### Astra Yams and replay
The native application is named **Astra Yams**. Its generated robot icon lives in the Dock; the interface keeps a text wordmark. Rebuild with `bun run desktop` to install the icon into the development bundle.

Skill details support `videos[].replay_path`: recorded MuJoCo world-body positions and XYZW quaternions, right-handed Z-up, time-stamped frames. `ReplayScene` uses original YAM URDF visual origins exactly once and renders the recorded poses with the same cel shader as the prompt. Orbit, pan, zoom, pause, scrub, and reset-view controls do not rerun physics. Export metadata should include source trace/scene hashes and outcome. Dynamic boxes carry full dimensions and recorded geom poses under unique object body names.

`Delete from library` writes a tombstone in `.local/deleted-skills.json`; it does not erase experiments or stop/delete agent sessions. Archive remains separately reversible. The prompt accepts up to ten image/CAD reference files totaling 50 MB, saved under the new project's `inputs/` folder before the engineer starts. File content is reference data; geometry still needs inspection and simulation preparation.

Fixture replay objects also accept `mesh_path` (repository-relative STL), `scale`, `local_position`, and `local_quaternion` (XYZW). Multiple objects can share one recorded `body`. Static objects may supply `pose: {position, quaternion}` without a per-frame entry. Optional `camera: {target, position}` frames the workcell; `default_time` opens the relevant recorded moment. Timestamps, including irregular final frames, are authoritative; playback never infers time from frame count.

### Prepared demo workflow
`/studio-api/templates` reads the scenario catalog; `/studio-api/configure` accepts only the three allowlisted scenario IDs and spawns the Python configuration CLI with an argument array. Every run gets a UUID directory; UI metadata and the new simulator bundle are separate. The UI follows real JSONL stage events. A successful setup is **environment configured**, never newly trained. Custom text or reference attachments retain the separate Simulation engineer workflow.

Scenario `stages` reveal prepared concepts, orbitable CAD, live setup checks, and recorded learning evidence. A one-frame design has no playback controls. Recorded scenes offer 0.5×/1×/2×/4× playback, fixture commands, a CAD parts list, selection/focus, and mesh/assembly downloads. Exploded inspection pauses motion and must be restored before playing; robot links retain their recorded poses.
