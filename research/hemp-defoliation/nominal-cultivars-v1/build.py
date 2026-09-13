from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE.parent / "development-v3" / "evidence" / "anderson-2021-phenotypes.csv"
RUNTIME = ROOT / "runs" / "hemp-cultivar-nominals-v1"

CULTIVARS = [
    ("Cherry Blossom", "cherry-blossom"),
    ("Cherry Blossom (Tuan)", "cherry-blossom-tuan"),
    ("Berry Blossom", "berry-blossom"),
    ("Cherry Blossom x Trump", "cherry-blossom-trump"),
    ("Cherry Wine", "cherry-wine"),
]

HEIGHTS = [
    (31, "HGT 31 DAS"),
    (36, "HGT 36 DAS"),
    (52, "HGT 52 DAS"),
    (67, "HGT 67 DAS"),
    (77, "HGT 77 DAS"),
    (99, "HGT 99 DAS"),
    (114, "HGT 114 DAS"),
]

METRICS = {
    "height_114_cm": ("HGT 114 DAS", "cm", "dominant-apex height"),
    "stem_diameter_max_mm": ("Max Stem Diameter (mm)", "mm", "maximum stem diameter at soil level"),
    "stem_diameter_orthogonal_mm": ("90 Degree Stem Diameter (mm)", "mm", "orthogonal stem diameter at soil level"),
    "cola_length_cm": ("Kola Length (cm)", "cm", "15 cm apical floral sample length measurement"),
    "cola_mass_g": ("Kola Mass (g)", "g", "mass of the sampled apical floral material"),
    "cola_linear_density_g_per_cm": ("Kola Density", "g/cm", "reported mass-to-length ratio"),
    "flower_biomass_g": ("Flower Biomass (g)", "g", "dry flower biomass"),
    "total_biomass_g": ("Total Biomass (g)", "g", "dry total above-ground biomass"),
    "stem_mass_g": ("Stem Mass (g)", "g", "dry stem mass"),
}


def number(value: str | None) -> float | None:
    try:
        parsed = float(value or "")
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summary(values: list[float]) -> dict[str, float | int] | None:
    if not values:
        return None
    result: dict[str, float | int] = {
        "n": len(values),
        "min": round(min(values), 4),
        "q25": round(quantile(values, 0.25), 4),
        "median": round(statistics.median(values), 4),
        "q75": round(quantile(values, 0.75), 4),
        "max": round(max(values), 4),
        "mean": round(statistics.mean(values), 4),
    }
    result["sd"] = round(statistics.stdev(values), 4) if len(values) > 1 else 0.0
    return result


def read_rows() -> list[dict[str, str]]:
    lines = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    return [row for row in csv.DictReader(lines[1:]) if row.get("Barcode")]


def treatment_rows(rows: list[dict[str, str]], cultivar: str, treatments: set[str]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("Pedigree") == cultivar and row.get("Treatment") in treatments]


def summarize_group(rows: list[dict[str, str]]) -> dict:
    heights = []
    for day, column in HEIGHTS:
        values = [value for row in rows if (value := number(row.get(column))) is not None]
        heights.append({"day_after_sowing": day, "height_cm": summary(values)})

    metrics = {}
    for key, (column, unit, meaning) in METRICS.items():
        values = [value for row in rows if (value := number(row.get(column))) is not None]
        metrics[key] = {"unit": unit, "meaning": meaning, "distribution": summary(values)}
    return {"plant_records": len(rows), "height_series": heights, "metrics": metrics}


def empirical_vectors(rows: list[dict[str, str]]) -> list[dict]:
    vectors = []
    for row in rows:
        vector = {
            "record_id": row["Barcode"],
            "treatment": row["Treatment"],
            "replicate": number(row.get("Rep")),
            "height_cm_by_das": {
                str(day): number(row.get(column)) for day, column in HEIGHTS
            },
            "measured": {
                key: number(row.get(column)) for key, (column, _, _) in METRICS.items()
            },
        }
        vectors.append(vector)
    return vectors


def main() -> None:
    rows = read_rows()
    cultivars = []
    for name, slug in CULTIVARS:
        exact = treatment_rows(rows, name, {"50 ppm N"})
        healthy = treatment_rows(rows, name, {"50 ppm N", "150 ppm N"})
        all_conditions = treatment_rows(rows, name, {row["Treatment"] for row in rows})
        cultivars.append(
            {
                "name": name,
                "slug": slug,
                "role": "starter placeholder" if name == "Cherry Blossom" else "alternative measured cultivar",
                "nominal_photo": f"evidence/{slug}-50ppm.jpg",
                "nominal_condition": {
                    "fertigation": "50 ppm N",
                    "reason": "The paper reports 50 and 150 ppm N as tall, highly branched, healthy plants and 50 ppm N as the optimum measured fertilizer rate.",
                    "summary": summarize_group(exact),
                    "empirical_joint_vectors": empirical_vectors(exact),
                },
                "healthy_condition_envelope": {
                    "fertigation": ["50 ppm N", "150 ppm N"],
                    "summary": summarize_group(healthy),
                    "empirical_joint_vectors": empirical_vectors(healthy),
                },
                "all_treatment_context": summarize_group(all_conditions),
            }
        )

    data = {
        "schema_version": 1,
        "generated_from": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "primary_dataset": {
            "citation": "Anderson II, Pearson, Kjelgren & Brym (2021), Response of essential oil hemp growth, biomass, and cannabinoid profiles to varying fertigation rates",
            "doi": "10.1371/journal.pone.0252985",
            "license": "CC BY 4.0",
            "design": "Five feminized, seed-grown cultivars; six fertilizer treatments; six blocks; greenhouse; 8 weeks vegetative plus 8 weeks flowering.",
        },
        "recommended_first_nominal": {
            "cultivar": "Cherry Blossom",
            "condition": "50 ppm N",
            "status": "research placeholder until the design partner supplies the production cultivar, clone line, plant age, and management history",
        },
        "cultivars": cultivars,
        "randomization_contract": {
            "identity": ["cultivar", "seed lot or clone line", "developmental stage", "management history", "facility recipe"],
            "nominal_sampling": "Select one complete measured row from the 50 ppm N group for the chosen cultivar. Preserve that row's height trajectory, stem cross-section, flower mass, and biomass together.",
            "healthy_envelope_sampling": "For a broader but still evidence-linked envelope, select one complete row from the 50 or 150 ppm N groups for the chosen cultivar.",
            "do_not_do": [
                "Do not draw every scalar independently from its marginal range; that destroys measured covariance.",
                "Do not treat fertilizer-stressed plants as ordinary within-clone variation.",
                "Do not infer branch topology, leaf attachment angles, tissue stiffness, cutting force, or contact damping from this scalar dataset.",
            ],
            "geometry_gap": "The source supplies one frontal cultivar-by-treatment photo grid and scalar plant measurements, not 3D organ coordinates. A nominal graph must be traced from photographs or measured from partner plants.",
            "mechanics_gap": "No flexural stiffness, damping, failure strain, petiole detachment force, or fresh-tissue mass distribution is reported. Those require separate literature priors and physical calibration tests.",
        },
        "secondary_datasets": [
            {
                "name": "Gill et al. industrial hemp phenotyping",
                "doi": "10.25909/29097107.v2",
                "license": "CC BY 4.0 for tabular data; related time-series image archives are CC BY-NC 4.0",
                "genotypes": ["Felina 32", "Ferimon 12", "Han NE"],
                "sample_sizes": {"Felina 32": 10, "Ferimon 12": 10, "Han NE": 20},
                "use": "Daily side-view image sequences and plant-level projected shoot area through day 36; useful for early growth shape and within-genotype visual variation, not flowering architecture.",
            },
            {
                "name": "LAST-Straw",
                "url": "https://lcas.github.io/LAST-Straw/",
                "license": "Not stated on the project page; verify before redistribution or product use.",
                "cultivars": ["Driscoll's Katrina", "Driscoll's Zara"],
                "sample_sizes": {"Driscoll's Katrina": 3, "Driscoll's Zara": 3},
                "use": "Fourteen 3D point-cloud captures per plant over 11 weeks, with organ labels on 28 scans and stem-like skeletons. This is a stronger geometric template for cultivar-conditioned strawberry models than any open Cannabis dataset found in this pass.",
            },
        ],
        "limits": [
            "The five greenhouse cultivars were seed-grown, so within-cultivar spread includes sibling genetic variation as well as environmental and measurement variation.",
            "The 50 ppm N nominal group contains at most six records per cultivar and some fields are missing. Empirical resampling is safer than fitting a high-dimensional Gaussian.",
            "No open, cultivar-labeled, whole-plant 3D Cannabis time series was found in this search.",
        ],
    }

    (HERE / "nominal-models.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for name in ["index.html", "nominal-models.json"]:
        shutil.copy2(HERE / name, RUNTIME / name)
    target_evidence = RUNTIME / "evidence"
    if target_evidence.exists():
        shutil.rmtree(target_evidence)
    shutil.copytree(HERE / "evidence", target_evidence)
    print(f"Built {len(cultivars)} cultivar profiles at {RUNTIME}")


if __name__ == "__main__":
    main()
