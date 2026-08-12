import os
import subprocess
import shutil
from pathlib import Path
import fitz  # pymupdf

def extract_page(input_pdf: str, page_num: int, output_pdf: str) -> None:
    src = fitz.open(input_pdf)
    dst = fitz.open()
    dst.insert_pdf(src, from_page=page_num - 1, to_page=page_num - 1)
    dst.save(output_pdf)
    dst.close()
    src.close()

def process_pdf(pdf_path: str, output_dir: str, start_page: int, end_page: int) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    staging_dir = Path("work/staging")
    marker_out_dir = Path("work/marker_out")
    staging_dir.mkdir(parents=True, exist_ok=True)
    marker_out_dir.mkdir(parents=True, exist_ok=True)

    page_nums = list(range(start_page, end_page + 1))

    # 1. Extract every page assigned to this worker into ONE staging folder,
    #    up front, before Marker ever runs.
    for global_page_num in page_nums:
        temp_pdf = staging_dir / f"page_{global_page_num:03d}.pdf"
        extract_page(pdf_path, global_page_num, str(temp_pdf))
        print(f"Extracted page {global_page_num}")

    # 2. Run Marker ONCE on the whole staging folder. This loads the
    #    detection/layout/reading-order/recognition models a single time
    #    for the entire batch instead of once per page.
    print(f"--- Running Marker (batch mode) on {len(page_nums)} pages ---")
    cmd = [
        "marker",
        str(staging_dir),
        "--output_dir", str(marker_out_dir),
        "--force_ocr",
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Marker batch run failed: {e}")

    # 3. Re-assemble Marker's per-PDF output folders into the page_XXX/
    #    layout the merge step expects.
    for global_page_num in page_nums:
        pdf_stem = f"page_{global_page_num:03d}"
        page_dir = output / pdf_stem
        page_dir.mkdir(parents=True, exist_ok=True)

        marker_result_dir = marker_out_dir / pdf_stem
        if not marker_result_dir.exists():
            print(f"No Marker output found for page {global_page_num} (likely failed)")
            continue

        md_file = marker_result_dir / f"{pdf_stem}.md"
        if md_file.exists():
            shutil.copy(md_file, page_dir / f"{pdf_stem}.md")

        for img_file in marker_result_dir.glob("*.png"):
            shutil.copy(img_file, page_dir / img_file.name)
        for img_file in marker_result_dir.glob("*.jpg"):
            shutil.copy(img_file, page_dir / img_file.name)

        print(f"Page {global_page_num} completed successfully.")

    # 4. Clean up all temporary staging/marker files unconditionally.
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    if marker_out_dir.exists():
        shutil.rmtree(marker_out_dir)

def main():
    start_page = int(os.environ["START_PAGE"])
    end_page = int(os.environ["END_PAGE"])
    chunk_pdf = "work/input.pdf"
    output_dir = "work/output"
    
    # Force the local AI to run on the GitHub Action CPU
    os.environ["TORCH_DEVICE"] = "cpu"
    
    process_pdf(chunk_pdf, output_dir, start_page, end_page)

if __name__ == "__main__":
    main()
