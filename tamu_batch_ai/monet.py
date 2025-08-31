import click
from tamu_batch_ai import ClaudeAV, ClaudeWork
import os
from tqdm import tqdm

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
def describe_vtts(path_to_vtts):
    for path, directories, files in os.walk(path_to_vtts):
        for file in tqdm(files):
            if '.vtt' in file:
                av_work = ClaudeAV(vtt_file=f"{path}/{file}")
                raw_response, metadata = av_work.get_metadata()
                av_work.save_metadata(
                    metadata, formats=["json"], 
                    output_path=f"tmp/{file.split('/')[-1].replace('.caption.vtt', ''). replace('.vtt', '')}"
                )