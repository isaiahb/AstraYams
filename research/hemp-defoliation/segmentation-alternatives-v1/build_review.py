"""Build a static, no-inference review of returned alternative-segmentation outputs."""
import argparse
import html
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def rel(path, out):
    return path.relative_to(out).as_posix() if path.is_relative_to(out) else path.as_uri()


def fmt(value):
    if isinstance(value, float):
        return f"{value:.4f}"
    return html.escape(str(value))


def metrics_table(rows):
    if not rows:
        return "<p>No result rows returned.</p>"
    keys = ["threshold", "foreground_coverage", "core_coverage", "proxy_precision", "proxy_iou", "definite_background_pixels", "predicted_pixels"]
    head = "".join(f"<th>{k}</th>" for k in keys)
    body = "".join("<tr>" + "".join(f"<td>{fmt(row.get(k, '—'))}</td>" for k in keys) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def visual_section(report, folder, out):
    if not report:
        return "<p class='missing'>Visual-region output was not returned.</p>"
    chunks = ["<h2>Executed: SAM3 visual-region-exemplar diagnostic</h2>",
              "<p class='notice'>Same SAM3 checkpoint, not an independent model. Each broad post-hoc region box may contain multiple blades, stem or background. Do not infer tight-exemplar quality, organ accuracy, or a held-out result.</p>",
              f"<p>Input SHA-256: <code>{html.escape(report.get('input_sha256', 'unknown'))}</code>; device: {html.escape(report.get('device', 'unknown'))}; elapsed: {fmt(report.get('elapsed_seconds', 'unknown'))} s.</p>"]
    source = folder / "input.png"
    chunks.append(f"<figure class='source'><a href='{rel(source, out)}'><img src='{rel(source, out)}'></a><figcaption>Frozen input image used by the tiled/residual baseline and every alternative run.</figcaption></figure>")
    baseline = report.get("optional_baseline")
    if baseline and baseline.get("available"):
        chunks += ["<h3>Frozen tiled/residual baseline — same proxy/ROI diagnostic</h3>",
                   "<p>This is a comparison table only; it is not ground truth and does not select an alternative candidate.</p>",
                   metrics_table(baseline.get("metrics", []))]
    for run in report.get("runs", []):
        seed = run["seed_region"]
        chunks += [f"<h3>Seed region: {html.escape(seed)}</h3>",
                   f"<p>Normalized box: <code>{html.escape(str(run.get('seed_box_cxcywh_normalized')))}</code>; proposals ≥0.1: {fmt(run.get('proposal_count_score_ge_0_1'))}</p>",
                   metrics_table(run.get("metrics", [])), "<div class='gallery'>"]
        for threshold in (0.5, 0.25, 0.1):
            img = folder / f"{seed}-coverage-{threshold}.png"
            chunks.append(f"<figure><a href='{rel(img, out)}'><img src='{rel(img, out)}' loading='lazy'></a><figcaption>{html.escape(seed)} · score ≥ {threshold}</figcaption></figure>")
        chunks.append("</div>")
        for row in run.get("review_diagnostic", []):
            labels = []
            for region in row["regions"]:
                hits = ", ".join(f"{a['id']}={'hit' if a['covered'] else 'miss'}" for a in region["anchors"])
                labels.append(f"{region['id']}: {hits}; ROI predicted pixels={region['roi_predicted_pixels']}")
            chunks.append(f"<p class='diag'>Threshold {row['threshold']}: {html.escape(' | '.join(labels))}</p>")
        proposal = folder / f"{seed}-proposals.npz"
        score = folder / f"{seed}-scores.npz"
        chunks.append(f"<p>Raw files: <a href='{rel(proposal, out)}'>packed proposals</a> · <a href='{rel(score, out)}'>score map</a>.</p>")
    return "\n".join(chunks)


def point_section(report, folder, out):
    if not report:
        failure = folder / "failure.log"
        if failure.exists():
            return ("<h2>Attempted: SAM3 targeted point refinement</h2>"
                    "<p class='notice'>Initial attempt did not execute because this script omitted the official "
                    "<code>enable_inst_interactivity=True</code> builder option; it was a configuration error, not a "
                    "checkpoint limitation. This preserved log will be superseded by the bounded corrected retry.</p>"
                    f"<pre>{html.escape(failure.read_text())}</pre><p><a href='{rel(failure, out)}'>Preserved worker failure log</a>.</p>")
        return "<p class='missing'>Point-refinement output was not returned.</p>"
    chunks = ["<h2>Executed: SAM3 targeted point refinement</h2>",
              "<p class='notice'>Oracle-assisted interaction: all six points were selected post-hoc. Each run has one reviewed positive point and one same-region negative point. These are not autonomous prompts or validation labels; predicted IoU is model output, not observed IoU.</p>",
              f"<p>Input SHA-256: <code>{html.escape(report.get('input_sha256', 'unknown'))}</code>; device: {html.escape(report.get('device', 'unknown'))}; elapsed: {fmt(report.get('elapsed_seconds', 'unknown'))} s.</p>"]
    initial_failure = folder / "initial-config-failure.log"
    if initial_failure.exists():
        chunks.append("<p class='diag'>The initial point attempt omitted <code>enable_inst_interactivity=True</code>; it was corrected before this completed run. "
                      f"<a href='{rel(initial_failure, out)}'>Preserved initial configuration log</a>.</p>")
    for run in report.get("runs", []):
        anchor = run["target_anchor"]
        chunks += [f"<h3>{html.escape(anchor)} — positive {run['positive_xy']}, negative {html.escape(run['negative_anchor'])} {run['negative_xy']}</h3>", "<div class='gallery'>"]
        # Show every raw ambiguous-click candidate. Do not select one for the viewer.
        for candidate in run.get("candidates", []):
            index = candidate["candidate_index"]
            img = folder / f"{anchor}-candidate-{index}.png"
            diag = candidate.get("diagnostic", {})
            chunks.append(f"<figure><a href='{rel(img, out)}'><img src='{rel(img, out)}' loading='lazy'></a><figcaption>candidate {index}; predicted IoU {fmt(candidate.get('predicted_iou'))}; proxy IoU {fmt(diag.get('proxy_iou'))}; proxy coverage {fmt(diag.get('foreground_coverage'))}</figcaption></figure>")
        chunks.append("</div>")
        raw = folder / f"{anchor}-raw-multimask.npz"
        chunks.append(f"<p><a href='{rel(raw, out)}'>Raw three-mask output, predicted quality, and logits</a>.</p>")
    return "\n".join(chunks)


parser = argparse.ArgumentParser()
parser.add_argument("--visual-dir", type=Path, default=HERE / "evidence" / "visual-exemplar")
parser.add_argument("--point-dir", type=Path, default=HERE / "evidence" / "point-refinement")
parser.add_argument("--out-dir", type=Path, default=HERE / "evidence")
args = parser.parse_args()
args.out_dir.mkdir(parents=True, exist_ok=True)
visual = json.loads((args.visual_dir / "result.json").read_text()) if (args.visual_dir / "result.json").exists() else None
point = json.loads((args.point_dir / "result.json").read_text()) if (args.point_dir / "result.json").exists() else None

page = f"""<!doctype html><meta charset='utf-8'><title>Segmentation alternatives v1 review</title>
<style>
body{{font:15px/1.45 system-ui,sans-serif;margin:28px;max-width:1450px;color:#17251d;background:#f5f6f2}} h1,h2{{color:#173d2c}} h2{{margin-top:42px}} .notice{{background:#fff3c6;padding:12px;border-left:4px solid #bf8916}} .missing{{color:#922}} .gallery{{display:flex;flex-wrap:wrap;gap:14px}} figure{{margin:0;max-width:300px;background:white;padding:8px;border:1px solid #d1d7d0}} img{{display:block;width:100%;height:auto}} figcaption{{font-size:12px;margin-top:5px}} table{{border-collapse:collapse;background:white;margin:12px 0}}th,td{{border:1px solid #cbd2cb;padding:5px 7px;text-align:right}}th{{background:#e4eee6}} code{{font-size:12px}} .diag{{font-size:12px;background:#e9eef0;padding:8px}}
</style>
<h1>Segmentation alternatives v1 — inspection report</h1>
<p>Frozen 381×444 source; compare only under the stated fixed proxy/ROI/threshold diagnostics. The color proxy is not a mask ground truth; these results make no leaf, leaflet, stem, hierarchy, or boundary-accuracy claim.</p>
<h2>Research-only candidates — not executed here</h2>
<ul><li>SAM 3.1 is a new checkpoint release for Object Multiplex/video tracking; official release material does not establish a still-image gain for this input.</li><li>SAM2 automatic/interactive, HQ-SAM, ZeroPlantSeg, and trained plant-instance models remain candidates described in the project README, with their setup, license, and domain limits.</li></ul>
{visual_section(visual, args.visual_dir, args.out_dir)}
{point_section(point, args.point_dir, args.out_dir)}
"""
(args.out_dir / "index.html").write_text(page)
print(args.out_dir / "index.html")
