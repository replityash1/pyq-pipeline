import os
from pathlib import Path
from src.drive import get_drive_service, list_pdfs, download_file, upload_file, create_drive_folder
from src.pdf_processor import process_pdf

def main():
    service = get_drive_service()
    input_folder = os.environ["DRIVE_INPUT_FOLDER_ID"]
    output_folder = os.environ["DRIVE_OUTPUT_FOLDER_ID"]

    pdfs = list_pdfs(service, input_folder)
    if not pdfs:
        print("No PDFs found in INPUT folder.")
        return

    # Stage 1: process only the FIRST pdf found, nothing else
    pdf_info = pdfs[0]
    print(f"Processing: {pdf_info['name']}")

    work_dir = Path("work")
    work_dir.mkdir(exist_ok=True)
    local_pdf_path = work_dir / pdf_info["name"]

    download_file(service, pdf_info["id"], str(local_pdf_path))

    output_dir = work_dir / "output"
    process_pdf(str(local_pdf_path), str(output_dir))

    paper_name = Path(pdf_info["name"]).stem
    remote_folder_id = create_drive_folder(service, paper_name, output_folder)

    for file_path in output_dir.rglob("*"):
        if file_path.is_file():
            upload_file(service, str(file_path), remote_folder_id)

    print("Done. Uploaded results to Drive.")

if __name__ == "__main__":
    main()
