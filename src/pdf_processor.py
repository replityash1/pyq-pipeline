from pathlib import Path
import fitz  # pymupdf
from paddlex import create_pipeline


def extract_page_range(input_pdf: str, start_page: int, end_page: int, output_pdf: str) -> None:
    """Extract pages [start_page, end_page] (1-indexed, inclusive) into a new PDF."""
    src = fitz.open(input_pdf)
    dst = fitz.open()
    dst.insert_pdf(src, from_page=start_page - 1, to_page=end_page - 1)
    dst.save(output_pdf)
    dst.close()
    src.close()


def process_pdf(pdf_path: str, output_dir: str, page_offset: int = 0) -> None:
    """page_offset lets each worker name its output folders with the TRUE
    page number from the original document, not 1,2,3... relative to its chunk."""
    pdf = Path(pdf_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    pipeline = create_pipeline(
        pipeline="PP-StructureV3",
        device="cpu",
        enable_mkldnn=False,
        cpu_threads=4,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        use_seal_recognition=False,
        use_chart_recognition=False,
    )

    results = pipeline.predict(input=str(pdf))

    for local_index, res in enumerate(results, start=1):
        global_page_num = page_offset + local_index
        page_dir = output / f"page_{global_page_num:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)
        res.save_to_json(save_path=str(page_dir))
        res.save_to_markdown(save_path=str(page_dir))
        res.save_to_img(save_path=str(page_dir))
