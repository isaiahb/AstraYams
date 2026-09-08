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
