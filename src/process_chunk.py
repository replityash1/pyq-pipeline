import os
import subprocess
import shutil
import sys
from pathlib import Path

import pymupdf  # replaces deprecated `import fitz`


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_page(input_pdf: str, page_num: int, output_pdf: str) -> None:
    """Extract a single page (1-indexed) from input_pdf into output_pdf."""
    src = pymupdf.open(input_pdf)
    dst = pymupdf.open()
    dst.insert_pdf(src, from_page=page_num - 1, to_page=page_num - 1)
    dst.save(output_pdf)
    dst.close()
    src.close()


def run_marker(staging_dir: Path, marker_out_dir: Path) -> bool:
    """
    Run Marker on the staging folder.

    Returns True on success, False on failure.

    marker-pdf 1.x uses:
        marker <input_dir> --output_dir <output_dir> [--workers N]

    --force_ocr is kept; it exists in both 1.x and 2.x.
    We deliberately avoid the 2.x llamacpp / surya-ocr backend by pinning
    marker-pdf==1.6.2 in the workflow (see install step).
    """
    cmd = [
        "marker",
        str(staging_dir),
        "--output_dir", str(marker_out_dir),
        "--workers", "1",       # single worker is fine for CI; avoids OOM
        "--force_ocr",
    ]
    print(f"Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"Marker exited with code {result.returncode}", flush=True)
        return False
    return True


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def process_pdf(
    pdf_path: str,
    output_dir: str,
    start_page: int,
    end_page: int,
) -> int:
    """
    Process pages [start_page, end_page] (inclusive, 1-indexed) of pdf_path.

    Returns the number of pages successfully converted.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    staging_dir  = Path("work/staging")
    marker_out   = Path("work/marker_out")
    staging_dir.mkdir(parents=True, exist_ok=True)
    marker_out.mkdir(parents=True, exist_ok=True)

    page_nums = list(range(start_page, end_page + 1))

    # ── Step 1: extract every assigned page into the staging folder ──────────
    for page_num in page_nums:
        temp_pdf = staging_dir / f"page_{page_num:03d}.pdf"
        extract_page(pdf_path, page_num, str(temp_pdf))
        print(f"Extracted page {page_num}", flush=True)

    # ── Step 2: run Marker once over the whole staging folder ────────────────
    print(f"--- Running Marker (batch mode) on {len(page_nums)} pages ---", flush=True)
    marker_ok = run_marker(staging_dir, marker_out)
    if not marker_ok:
        print("Marker batch run failed — no output will be written.", flush=True)

    # ── Step 3: collect Marker's output into the layout the merge step wants ─
    success_count = 0
    for page_num in page_nums:
        pdf_stem = f"page_{page_num:03d}"
        page_dir = output / pdf_stem
        page_dir.mkdir(parents=True, exist_ok=True)

        # Marker 1.x writes:  <output_dir>/<pdf_stem>/<pdf_stem>.md  (+ images)
        marker_result = marker_out / pdf_stem
        if not marker_result.exists():
            print(f"No Marker output for page {page_num} (likely failed)", flush=True)
            continue

        md_file = marker_result / f"{pdf_stem}.md"
        if md_file.exists():
            shutil.copy(md_file, page_dir / f"{pdf_stem}.md")
        else:
            print(f"Missing .md for page {page_num}", flush=True)
            continue

        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            for img in marker_result.glob(ext):
                shutil.copy(img, page_dir / img.name)

        print(f"Page {page_num} completed successfully.", flush=True)
        success_count += 1

    # ── Step 4: clean up temporary files ─────────────────────────────────────
    for tmp in (staging_dir, marker_out):
        if tmp.exists():
            shutil.rmtree(tmp)

    return success_count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Provided by the workflow matrix
    start_page = int(os.environ["START_PAGE"])
    end_page   = int(os.environ["END_PAGE"])

    # marker-pdf 1.x uses PyTorch directly — no llamacpp / surya backend.
    # These two vars are belt-and-suspenders in case any transitive dep checks.
    os.environ.setdefault("TORCH_DEVICE", "cpu")
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    chunk_pdf  = "work/input.pdf"
    output_dir = "work/output"

    if not Path(chunk_pdf).exists():
        # The download-artifact step puts the file at work/<filename>.
        # Handle the common case where the artifact contains a differently-
        # named PDF by picking the first .pdf we find under work/.
        candidates = list(Path("work").glob("*.pdf"))
        if not candidates:
            print("ERROR: no PDF found under work/", flush=True)
            sys.exit(1)
        chunk_pdf = str(candidates[0])
        print(f"Using PDF: {chunk_pdf}", flush=True)

    n = process_pdf(chunk_pdf, output_dir, start_page, end_page)
    total = end_page - start_page + 1
    print(f"Done: {n}/{total} pages converted.", flush=True)

    if n == 0:
        # Fail the job so the matrix run is marked red in GitHub Actions
        sys.exit(1)


if __name__ == "__main__":
    main()
