import click
from tamu_batch_ai import ClaudeAV, ClaudeWork, process_json_directory
import os
from tqdm import tqdm
from csv import DictReader

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
def describe_vtts(path_to_vtts, csv):
    total_cost = 0
    os.makedirs(".tmp", exist_ok=True)
    for filename in os.listdir(".tmp"):
        filepath = os.path.join(".tmp", filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    for path, directories, files in os.walk(path_to_vtts):
        for file in tqdm(files):
            if '.vtt' in file:
                av_work = ClaudeAV(vtt_file=f"{path}/{file}")
                raw_response, metadata = av_work.get_metadata()
                av_work.save_metadata(
                    metadata, 
                    formats=["json"], 
                    output_path=f".tmp/{file.split('/')[-1].replace('.caption.vtt', ''). replace('.vtt', '')}"
                )
                try:
                    cost = av_work.calculate_cost()
                    total_cost += cost['total_cost_usd']
                except:
                    print("Could not calculate costs.")
    
    process_json_directory(
        ".tmp", 
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
def describe_images_from_csv(input_csv, output_csv):
    total_cost = 0
    os.makedirs(".tmp", exist_ok=True)
    for filename in os.listdir(".tmp"):
        filepath = os.path.join(".tmp", filename)
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
                formats=["json"],
                output_path=".tmp/metadata"
            )
            try:
                    cost = work.calculate_cost()
                    total_cost += cost['total_cost_usd']
            except:
                print("Could not calculate costs.")
    
    process_json_directory(
        ".tmp", 
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
def generate_handwritten_text(input_csv, output_json):
    total_cost = 0
    
