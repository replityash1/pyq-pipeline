import os
from pathlib import Path
from src.drive import get_drive_service, create_drive_folder, upload_file


def main():
    service = get_drive_service()
    output_folder = os.environ["DRIVE_OUTPUT_FOLDER_ID"]
    pdf_name = os.environ["PDF_NAME"]

    merged_dir = Path("merged_output")
    paper_name = Path(pdf_name).stem
    remote_folder_id = create_drive_folder(service, paper_name, output_folder)

    count = 0
    for file_path in merged_dir.rglob("*"):
        if file_path.is_file():
            upload_file(service, str(file_path), remote_folder_id)
            count += 1

    print(f"Uploaded {count} files to Drive under '{paper_name}'.")


if __name__ == "__main__":
    main()
