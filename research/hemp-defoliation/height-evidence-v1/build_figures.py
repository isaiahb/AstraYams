"""Extract attributed figures from local open-access research PDFs, without image synthesis."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
jobs = [
    ("massuela-2022", 5, (100, 210, 1180, 644), "dated-architecture.png"),
    ("burgel-2020", 6, (382, 330, 888, 1409), "measured-height-curves.png"),
]
records = []
(ROOT / "figures").mkdir(exist_ok=True)
for paper, page, crop, output in jobs:
    source = ROOT / "papers" / f"{paper}.pdf"
    with tempfile.TemporaryDirectory() as temp:
        stem = Path(temp) / "page"
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
                        "-scale-to", "1800", "-png", str(source), str(stem)], check=True)
        rendered = Image.open(stem.with_suffix(".png"))
        assert rendered.size == (1273, 1800), rendered.size
        rendered.crop(crop).save(ROOT / "figures" / output)
    records.append({"source": str(source.relative_to(ROOT)), "page": page,
                    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "crop_pixels_at_1273_by_1800": crop, "output": f"figures/{output}",
                    "changes": "Page crop only; no alterations to plants, plots or labels. Captions paraphrased on review page."})
(ROOT / "figure-provenance.json").write_text(json.dumps(records, indent=2) + "\n")
