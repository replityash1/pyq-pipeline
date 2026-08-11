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
    
    for global_page_num in range(start_page, end_page + 1):
        print(f"--- Processing page {global_page_num} with Local AI (Marker) ---")
        
        # 1. Create standard page directory expected by your merge script
        page_dir = output / f"page_{global_page_num:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Extract just this single page into a temporary PDF
        temp_pdf = page_dir / f"temp_page_{global_page_num:03d}.pdf"
        extract_page(pdf_path, global_page_num, str(temp_pdf))
        
        # 3. Create a staging area for Marker outputs
        marker_out_dir = page_dir / "marker_out"
        marker_out_dir.mkdir(parents=True, exist_ok=True)
        
        # 4. Execute Marker OCR (Language flag removed - v2.0 auto-detects English/Hindi)
        cmd = [
            "marker_single",
            str(temp_pdf),
            "--output_dir", str(marker_out_dir),
            "--force_ocr"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # 5. Marker places results in a subfolder named after the input file
            pdf_stem = temp_pdf.stem
            marker_result_dir = marker_out_dir / pdf_stem
            
            # 6. Move the markdown output to match your original structure
            md_file = marker_result_dir / f"{pdf_stem}.md"
            if md_file.exists():
                final_md_path = page_dir / f"page_{global_page_num:03d}.md"
                shutil.copy(md_file, final_md_path)
                
            # 7. Move any extracted graphs, equations, or diagrams
            for img_file in marker_result_dir.glob("*.png"):
                shutil.copy(img_file, page_dir / img_file.name)
            for img_file in marker_result_dir.glob("*.jpg"):
                shutil.copy(img_file, page_dir / img_file.name)
                
        except subprocess.CalledProcessError as e:
            print(f"Error processing page {global_page_num}: {e}")
            
        finally:
            # 8. THE FIX: Clean up ALL temporary files unconditionally
            # This guarantees you never get a zip full of raw PDFs again!
            if temp_pdf.exists():
                temp_pdf.unlink()
            if marker_out_dir.exists():
                shutil.rmtree(marker_out_dir)
                
        print(f"Page {global_page_num} completed successfully.")

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
