import os
from src.pdf_processor import extract_page_range, process_pdf


def main():
    start_page = int(os.environ["START_PAGE"])
    end_page = int(os.environ["END_PAGE"])
    worker_id = os.environ["WORKER_ID"]

    input_pdf = "work/input.pdf"
    chunk_pdf = f"work/chunk_{worker_id}.pdf"
    output_dir = "work/output"

    print(f"Worker {worker_id}: extracting pages {start_page}-{end_page}")
    extract_page_range(input_pdf, start_page, end_page, chunk_pdf)

    process_pdf(chunk_pdf, output_dir, page_offset=start_page - 1)
    print(f"Worker {worker_id}: done")


if __name__ == "__main__":
    main()
