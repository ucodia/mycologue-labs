#!/usr/bin/env python3

import subprocess
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import Tuple, Optional
import click
from tqdm import tqdm


def process_image(args: Tuple[Path, Optional[Path], bool]) -> Tuple[str, str, str]:
    """
    Process a single image to create a mask using ImageMagick.
    
    Args:
        args: Tuple containing (input_file_path, output_folder, overwrite)
    
    Returns:
        Tuple of (status, input_file, output_file or error_message)
        status can be: 'success', 'skipped', 'failed'
    """
    input_file, output_folder, overwrite = args
    
    try:
        if output_folder:
            output_file = output_folder / f"{input_file.stem}.mask.png"
        else:
            output_file = input_file.with_suffix('.mask.png')
        
        if output_file.exists() and not overwrite:
            return 'skipped', str(input_file), str(output_file)
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            'magick', str(input_file),
            '-colorspace', 'Gray',
            '-blur', '0x4',
            '-threshold', '4%',
            '-define', 'connected-components:keep-top=1',
            '-connected-components', '8',
            '-type', 'bilevel',
            str(output_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return 'success', str(input_file), str(output_file)
        
    except subprocess.CalledProcessError as e:
        return 'failed', str(input_file), f"Error: {e.stderr}"
    except Exception as e:
        return 'failed', str(input_file), f"Error: {str(e)}"


@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help='Input directory containing JPG images'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default=None,
    help='Output folder for mask files. Files will be named {filename}.mask.png. Default: same as input folder'
)
@click.option(
    '--workers', '-w',
    type=int,
    default=None,
    help='Number of worker processes (default: number of CPU cores)'
)
@click.option(
    '--overwrite',
    is_flag=True,
    default=False,
    help='Overwrite existing mask files (default: skip existing files)'
)
def main(input: Path, output: Optional[Path], workers: Optional[int], overwrite: bool):
    """
    Create mask images from image files using ImageMagick.

    This script processes image files to create binary masks using ImageMagick's
    connected components analysis to isolate the main subject.
    """
    image_files = [
        f for f in input.iterdir() 
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg']
    ]
    image_files = sorted(image_files)
    
    if not image_files:
        click.echo("No image files found in the specified input directory.", err=True)
        return
    
    click.echo(f"Found {len(image_files)} image file(s) to process")
    
    output_folder = output if output else input
    click.echo(f"Output folder: {output_folder}")
    
    if workers is None:
        workers = min(cpu_count(), len(image_files))
    
    click.echo(f"Using {workers} worker process(es)")
    
    process_args = [(image_file, output_folder, overwrite) for image_file in image_files]
    
    successful = 0
    skipped = 0
    failed = 0
    
    with Pool(processes=workers) as pool:
        with tqdm(total=len(image_files), desc="Processing images", unit="file") as pbar:
            for status, input_file, result in pool.imap(process_image, process_args):
                if status == 'success':
                    successful += 1
                elif status == 'skipped':
                    skipped += 1
                else:  # failed
                    failed += 1
                    click.echo(f"Failed to process {input_file}: {result}", err=True)
        
                pbar.update(1)
    
    click.echo(f"\nProcessing complete!")
    click.echo(f"Successfully processed: {successful} files")
    if skipped > 0:
        click.echo(f"Skipped (already exists): {skipped} files")
    if failed > 0:
        click.echo(f"Failed to process: {failed} files", err=True)


if __name__ == "__main__":
    main()