import os
import json
import math
from pathlib import Path
import fitz

from src.drive import get_drive_service, list_pdfs, download_file


def main():
    num_workers = int(os.environ.get("NUM_WORKERS", "10"))

    service = get_drive_service()
    input_folder = os.environ["DRIVE_INPUT_FOLDER_ID"]

    pdfs = list_pdfs(service, input_folder)
    if not pdfs:
        raise SystemExit("No PDFs found in INPUT folder.")

    pdf_info = pdfs[0]
    print(f"Selected PDF: {pdf_info['name']}")

    work_dir = Path("work")
    work_dir.mkdir(exist_ok=True)
    local_pdf_path = work_dir / "input.pdf"
    download_file(service, pdf_info["id"], str(local_pdf_path))

    doc = fitz.open(str(local_pdf_path))
    total_pages = doc.page_count
    doc.close()
    print(f"Total pages: {total_pages}, splitting across {num_workers} workers")

    chunk_size = math.ceil(total_pages / num_workers)
    chunks = []
    for i in range(num_workers):
        start = i * chunk_size + 1
        end = min((i + 1) * chunk_size, total_pages)
        if start > total_pages:
            break
        chunks.append({"worker_id": str(i), "start_page": start, "end_page": end})
        print(f"  worker {i}: pages {start}-{end}")

    matrix = {"include": chunks}

    github_output = os.environ["GITHUB_OUTPUT"]
    with open(github_output, "a") as f:
        f.write(f"matrix={json.dumps(matrix)}\n")
        f.write(f"pdf_name={pdf_info['name']}\n")


if __name__ == "__main__":
    main()
