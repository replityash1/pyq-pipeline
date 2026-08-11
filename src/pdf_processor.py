from pathlib import Path
from paddlex import create_pipeline

def process_pdf(pdf_path: str, output_dir: str) -> None:
    pdf = Path(pdf_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    pipeline = create_pipeline(
        pipeline="PP-StructureV3",
        device="cpu",
        enable_mkldnn=False,
    )

    results = pipeline.predict(
        input=str(pdf),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    for page_index, res in enumerate(results, start=1):
        page_dir = output / f"page_{page_index:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)
        res.save_to_json(save_path=str(page_dir))
        res.save_to_markdown(save_path=str(page_dir))
        res.save_to_img(save_path=str(page_dir))
