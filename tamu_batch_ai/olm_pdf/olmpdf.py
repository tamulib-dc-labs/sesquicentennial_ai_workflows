#!/usr/bin/env python3

import json
import datetime
import hashlib
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image

# OlmOCR imports
from mlx_vlm import load, apply_chat_template, generate
from olmocr.data.renderpdf import render_pdf_to_base64png
from olmocr.prompts import build_finetuning_prompt
from olmocr.prompts.anchor import get_anchor_text

# PDF handling
import PyPDF2


def process_pdf_to_json(pdf_path, model_name="mlx-community/olmOCR-7B-0225-preview-4bit"):
    """
    Simple function to convert PDF to JSON using OlmOCR

    Args:
        pdf_path (str): Path to the PDF file
        model_name (str): OlmOCR model to use

    Returns:
        dict: Dolma-formatted document with OCR results
    """

    # Load OlmOCR model
    print("Loading OlmOCR model...")
    model, processor = load(model_name)
    config = model.config

    # Get PDF page count
    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        num_pages = len(pdf_reader.pages)

    print(f"Processing {num_pages} pages from {pdf_path}")

    # Process each page
    full_text = ""
    page_mappings = []
    char_position = 0

    for page_num in range(1, num_pages + 1):
        print(f"Processing page {page_num}/{num_pages}")

        # Convert PDF page to image
        image_base64 = render_pdf_to_base64png(pdf_path, page_num, target_longest_image_dim=1024)
        image = Image.open(BytesIO(base64.b64decode(image_base64)))

        # Create OCR prompt
        anchor_text = get_anchor_text(pdf_path, page_num, pdf_engine="pdfreport", target_length=4000)
        prompt = build_finetuning_prompt(anchor_text)

        # Apply chat template
        messages = [{"role": "user", "content": prompt}]
        text_prompt = apply_chat_template(processor, config, messages)

        # Generate OCR text
        page_text = ""
        try:
            tokenizer = processor.tokenizer

            for tokens in generate(model, processor, text_prompt, image, max_tokens=1024, temperature=0.1):
                chunk = ""
                if isinstance(tokens, str):
                    chunk = tokens
                elif hasattr(tokens, 'tolist'):
                    tokens = tokens.tolist()
                    if all(isinstance(t, int) for t in tokens):
                        chunk = tokenizer.decode(tokens, skip_special_tokens=True)

                if chunk:
                    page_text += chunk

        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            page_text = f"[ERROR: Could not process page {page_num} - {e}]"

        # Track character positions
        start_pos = char_position
        clean_text = page_text.strip()
        full_text += clean_text
        if page_num < num_pages:  # Add newline except for last page
            full_text += "\n"
        char_position = len(full_text)

        # Store page mapping: [start_char, end_char, page_number]
        page_mappings.append([start_pos, char_position, page_num])

    # Create Dolma document structure
    document_id = hashlib.sha1(full_text.encode()).hexdigest()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

    dolma_doc = {
        "id": document_id,
        "text": full_text,
        "source": "olmocr",
        "added": timestamp,
        "created": timestamp,
        "metadata": {
            "source_file": str(pdf_path),
            "total_pages": num_pages,
            "model_used": model_name
        },
        "attributes": {
            "pdf_page_numbers": page_mappings
        }
    }

    return dolma_doc


def save_json_output(dolma_doc, output_path=None):
    """Save the Dolma document to a JSON file"""
    if output_path is None:
        source_file = dolma_doc["metadata"]["source_file"]
        output_path = Path(source_file).stem + "_ocr.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dolma_doc, f, indent=2, ensure_ascii=False)

    print(f"OCR results saved to: {output_path}")
    return output_path


# Simple CLI usage
if __name__ == "__main__":
    pdf_file = "/Users/mark.baggett/oaktrust_accessibility/teachingmats/Zappos Case Study.pdf"
    output_file = "test.json"

    # Process PDF
    result = process_pdf_to_json(pdf_file)

    # Save results
    save_json_output(result, output_file)

    print(f"\nDocument processed successfully!")
    print(f"Total pages: {result['metadata']['total_pages']}")
    print(f"Total characters: {len(result['text'])}")
