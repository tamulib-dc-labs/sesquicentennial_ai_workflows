import click
from tamu_batch_ai import ClaudeAV, ClaudeWork, process_json_directory
import os
from tqdm import tqdm
from csv import DictReader

@click.group()
def cli() -> None:
    pass

@cli.command(
    "describe_vtts", help="Creates Desriptive Metadata from VTT Files"
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
    os.makedirs("tmp", exist_ok=True)
    for path, directories, files in os.walk(path_to_vtts):
        for file in tqdm(files):
            if '.vtt' in file:
                av_work = ClaudeAV(vtt_file=f"{path}/{file}")
                raw_response, metadata = av_work.get_metadata()
                av_work.save_metadata(
                    metadata, formats=["json"], 
                    output_path=f"tmp/{file.split('/')[-1].replace('.caption.vtt', ''). replace('.vtt', '')}"
                )
                try:
                    cost = av_work.calculate_cost()
                    total_cost += cost['total_cost_usd']
                except:
                    print("Could not calculate costs.")
    
    process_json_directory(
        "tmp", 
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
    os.makedirs("tmp", exist_ok=True)
    with open(input_csv, 'r') as my_csv:
        reader = DictReader(my_csv)
        for row in tqdm(reader):
            pages = row["Filenames"].split(' | ')
            work = ClaudeWork(pages=pages)
            raw_response, metadata = work.get_metadata()
            work.save_metadata(
                metadata,
                formats=["json"],
                output_path="tmp/metadata"
            )
            try:
                    cost = work.calculate_cost()
                    total_cost += cost['total_cost_usd']
            except:
                print("Could not calculate costs.")
    
    process_json_directory(
        "tmp", 
        output_csv=output_csv
    )
    print(f"Total cost estimates were approximately ${total_cost}.")
