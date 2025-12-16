import click
from tamu_batch_ai import ClaudeAV, ClaudeWork, process_json_directory
from tamu_batch_ai.claude.htr import ClaudePage, ClaudeImage
import os
from tqdm import tqdm
from csv import DictReader
import json
import urllib.request
from pathlib import Path

@click.group()
def cli() -> None:
    pass

@cli.command(
    "describe_vtts", help="Creates Descriptive Metadata from VTT Files"
)
@click.option(
    "--path_to_vtts",
    "-p",
    help="The path to the VTTs you want to generate metadata from",
)
@click.option(
    "--csv",
    "-c",
    help="The CSV to write your output to",
    default="flattened.csv"
)
@click.option(
    "--temporary_directory",
    "-t",
    help="The temporary directory to write your output to",
    default=".tmp"
)
def describe_vtts(path_to_vtts, csv, temporary_directory) -> None:
    total_cost = 0
    os.makedirs(temporary_directory, exist_ok=True)
    for filename in os.listdir(temporary_directory):
        filepath = os.path.join(temporary_directory, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    for path, directories, files in os.walk(path_to_vtts):
        for file in tqdm(files):
            if '.vtt' in file:
                av_work = ClaudeAV(vtt_file=f"{path}/{file}")
                raw_response, metadata = av_work.get_metadata()
                av_work.save_metadata(
                    metadata,
                    output_path=f"{temporary_directory}/{file.split('/')[-1].replace('.caption.vtt', '').replace('.vtt', '')}"
                )
                try:
                    cost = av_work.calculate_cost()
                    total_cost += cost['total_cost_usd']
                except:
                    print("Could not calculate costs.")
    
    process_json_directory(
        temporary_directory,
        csv
    )
    print(f"Total cost estimates were approximately ${total_cost}.")


@cli.command(
    "describe_images_from_csv", help="Runs HTR and Creates Descriptive Metadata from a CSV of Images"
)
@click.option(
    "--input_csv",
    "-i",
    help="The path to the CSV containing related images",
)
@click.option(
    "--output_csv",
    "-o",
    help="The path to write the HTR and descriptive metadata. Must have files in a column called 'Filenames'.",
    default="flattened.csv"
)
@click.option(
    "--temporary_directory",
    "-t",
    help="The temporary directory to write your output to",
    default=".tmp"
)
def describe_images_from_csv(input_csv, output_csv, temporary_directory) -> None:
    total_cost = 0
    os.makedirs(temporary_directory, exist_ok=True)
    for filename in os.listdir(temporary_directory):
        filepath = os.path.join(temporary_directory, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    with open(input_csv, newline="") as f:
        total_rows = sum(1 for _ in f) - 1 
    with open(input_csv, 'r') as my_csv:
        reader = DictReader(my_csv)
        for row in tqdm(reader, total=total_rows):
            pages = row["Filenames"].split('|')
            work = ClaudeWork(pages=pages)
            raw_response, metadata = work.get_metadata()
            metadata["full_text"] = work.full_page_responses
            work.save_metadata(
                metadata,
                output_path=f"{temporary_directory}/metadata"
            )
            try:
                    cost = work.calculate_cost()
                    total_cost += cost['total_cost_usd']
            except:
                print("Could not calculate costs.")
    
    process_json_directory(
        temporary_directory,
        output_csv=output_csv
    )
    print(f"Total cost estimates were approximately ${total_cost}.")


@cli.command(
    "run_htr", help="Runs HTR on a set of pages and stores them as JSON"
)
@click.option(
    "--input_csv",
    "-i",
    help="The path to the CSV containing related images",
)
@click.option(
    "--output_json",
    "-o",
    help="The path to write the HTR and descriptive metadata. Must have files in a column called 'Filenames'.",
    default="flattened.csv"
)
@click.option(
    "--temporary_directory",
    "-t",
    help="The temporary directory to write your output to",
    default=".tmp"
)
def generate_handwritten_text(input_csv, output_json, temporary_directory) -> None:
    total_cost = 0
    os.makedirs(temporary_directory, exist_ok=True)
    for filename in os.listdir(temporary_directory):
        filepath = os.path.join(temporary_directory, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)

    # Count total rows for progress bar
    with open(input_csv, newline="") as f:
        total_rows = sum(1 for _ in f) - 1

    # Process each row in the CSV
    with open(input_csv, 'r') as my_csv:
        reader = DictReader(my_csv)
        for row in tqdm(reader, total=total_rows, desc="Processing pages"):
            pages = row["Filenames"].split('|')

            # Run HTR on each page
            htr_results = []
            for page_path in pages:
                page = ClaudePage()
                extracted_text, page_data = page.extract_text_with_claude(page_path)
                htr_results.append({
                    "filename": page_path,
                    "extracted_text": extracted_text,
                    "details": page_data
                })

                # Calculate cost for this page
                try:
                    cost = page.calculate_cost()
                    total_cost += cost['total_cost_usd']
                except:
                    print(f"Could not calculate costs for {page_path}.")

            # Save HTR results for this set of pages
            output_filename = pages[0].split('/')[-1].replace('.jpg', '').replace('.png', '').replace('.tif', '')
            output_path = f"{temporary_directory}/{output_filename}_htr.json"

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "pages": htr_results,
                    "full_text": "\n\n".join([r["extracted_text"] for r in htr_results])
                }, f, indent=2, ensure_ascii=False)

    # Process all JSON files into output CSV
    process_json_directory(
        temporary_directory,
        output_csv=output_json
    )

    print(f"Total cost estimates were approximately ${total_cost:.6f}.")


@cli.command(
    "analyze_images", help="Analyzes images/maps with existing metadata to suggest enhanced Dublin Core elements"
)
@click.option(
    "--input_csv",
    "-i",
    help="CSV with columns: image_path (file or URL), existing_metadata, material_type (MAP|PHOTOGRAPH|DRAWING|etc)",
    required=True
)
@click.option(
    "--output_csv",
    "-o",
    help="The path to write the metadata analysis results",
    default="image_analysis.csv"
)
@click.option(
    "--temporary_directory",
    "-t",
    help="The temporary directory to write your output to",
    default=".tmp"
)
def analyze_images(input_csv, output_csv, temporary_directory) -> None:
    total_cost = 0
    downloaded_files = []  # Track downloaded files for cleanup

    def download_image(url, temp_dir):
        """Download image from URL to temporary directory."""
        filename = url.split('/')[-1].split('?')[0]  # Get filename from URL, remove query params
        if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.tif', '.tiff']):
            filename += '.jpg'  # Add extension if missing

        local_path = os.path.join(temp_dir, f"download_{filename}")

        try:
            urllib.request.urlretrieve(url, local_path)
            downloaded_files.append(local_path)
            return local_path
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return None

    # Create and clear temporary directory
    os.makedirs(temporary_directory, exist_ok=True)
    for filename in os.listdir(temporary_directory):
        filepath = os.path.join(temporary_directory, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)

    # Count total rows for progress bar
    with open(input_csv, newline="") as f:
        total_rows = sum(1 for _ in f) - 1

    try:
        # Process each row in the CSV
        with open(input_csv, 'r') as my_csv:
            reader = DictReader(my_csv)
            for idx, row in enumerate(tqdm(reader, total=total_rows, desc="Analyzing images")):
                image_path = row.get("image_path", "")
                existing_metadata = row.get("existing_metadata", "")
                material_type = row.get("material_type", "IMAGE")

                if not image_path:
                    print(f"Skipping row {idx+1}: no image_path provided")
                    continue

                # Check if image_path is a URL
                is_url = image_path.startswith('http://') or image_path.startswith('https://')

                if is_url:
                    # Download the image
                    local_image_path = download_image(image_path, temporary_directory)
                    if not local_image_path:
                        print(f"Skipping row {idx+1}: failed to download {image_path}")
                        continue
                else:
                    local_image_path = image_path

                # Create ClaudeImage instance
                image_analyzer = ClaudeImage(
                    image_path=local_image_path,
                    existing_metadata=existing_metadata,
                    material_type=material_type
                )

                # Analyze the image with metadata
                raw_response, metadata = image_analyzer.analyze_image_with_metadata(local_image_path)

                # Add source info to metadata
                metadata["source_image"] = image_path  # Store original path/URL
                metadata["material_type"] = material_type

                # Save results
                if is_url:
                    # Use URL-based filename
                    output_filename = image_path.split('/')[-1].split('?')[0].replace('.jpg', '').replace('.png', '').replace('.tif', '')
                else:
                    output_filename = image_path.split('/')[-1].replace('.jpg', '').replace('.png', '').replace('.tif', '')

                output_path = f"{temporary_directory}/{output_filename}_analysis.json"

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                # Calculate cost
                try:
                    cost = image_analyzer.calculate_cost()
                    total_cost += cost['total_cost_usd']
                except:
                    print(f"Could not calculate costs for {image_path}.")

        # Process all JSON files into output CSV
        process_json_directory(
            temporary_directory,
            output_csv=output_csv
        )

        print(f"Total cost estimates were approximately ${total_cost:.6f}.")

    finally:
        # Clean up downloaded files
        for filepath in downloaded_files:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Could not remove temporary file {filepath}: {e}")

