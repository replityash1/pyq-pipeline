import os
import time
from pathlib import Path
import fitz  # pymupdf
from google import genai
from google.genai import types

TRANSCRIPTION_PROMPT = """You are transcribing a page from an Indian competitive exam question paper (bilingual English/Hindi, mixed with science/math content).

STRICT RULES:
1. Transcribe ALL text exactly as printed. Do not paraphrase, correct spelling, or "fix" anything.
2. Preserve question numbers exactly as they appear.
3. Keep English and Hindi versions of the same question together, clearly labeled.
4. For genuine mathematical or scientific equations, write them in LaTeX between $ signs.
5. For chemical structures, molecular diagrams, physics diagrams, circuit diagrams, or any non-text visual element: do NOT attempt to describe, redraw, or interpret it. Insert exactly this placeholder instead: [DIAGRAM]
6. For tables, reproduce them as Markdown tables.
7. If text is genuinely illegible, write [UNCLEAR] rather than guessing.
8. Do not solve or answer any question. Do not add commentary or explanation.
9. Output valid Markdown only — no preamble, no "here is the transcription", nothing but the content.
"""


def extract_page_range(input_pdf: str, start_page: int, end_page: int, output_pdf: str) -> None:
    src = fitz.open(input_pdf)
    dst = fitz.open()
    dst.insert_pdf(src, from_page=start_page - 1, to_page=end_page - 1)
    dst.save(output_pdf)
    dst.close()
    src.close()


def render_pdf_pages_to_images(pdf_path: str, output_dir: Path, dpi: int = 200) -> list[Path]:
    doc = fitz.open(pdf_path)
    image_paths = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        img_path = output_dir / f"_render_{i+1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
    doc.close()
    return image_paths


def transcribe_page(client: genai.Client, image_path: Path, max_retries: int = 4) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",  # Updated to a stable, working model string
                contents=[TRANSCRIPTION_PROMPT, image_part],
            )
            return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) * 10  # 10s, 20s, 40s, 80s
            print(f"  Retry {attempt + 1}/{max_retries} after error: {e}. Waiting {wait}s...")
            time.sleep(wait)


def process_pdf(pdf_path: str, output_dir: str, page_offset: int = 0) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    image_paths = render_pdf_pages_to_images(pdf_path, output)

    for local_index, img_path in enumerate(image_paths, start=1):
        global_page_num = page_offset + local_index
        page_dir = output / f"page_{global_page_num:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Transcribing page {global_page_num}...")
        markdown_text = transcribe_page(client, img_path)

        (page_dir / f"page_{global_page_num:03d}.md").write_text(markdown_text, encoding="utf-8")
        img_path.rename(page_dir / f"page_{global_page_num:03d}.png")

        time.sleep(2)  # small pacing gap to help stay under per-minute rate limits
