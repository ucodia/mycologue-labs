#!/usr/bin/env python3

import subprocess
from pathlib import Path
from typing import Optional
import click
from logger import setup_logger

logger = setup_logger(__file__)

@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help='Input directory containing images'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default=None,
    help='Output directory for 3D models. Default: {input}/models'
)
@click.option(
    '--overwrite',
    is_flag=True,
    default=False,
    help='Overwrite existing project files (default: skip existing projects)'
)
def main(input: Path, output: Optional[Path], overwrite: bool):
    """Generate 3D models from images using RealityScan."""
    
    image_files = [f for f in input.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg']]
    
    if not image_files:
        logger.info("No image files found.", err=True)
        return
    
    input_dir = input.resolve()
    output_dir = output.resolve() if output else input.resolve() / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_name = input.name
    script_dir = Path(__file__).parent.resolve()
    export_params_file = script_dir / "rs-params" / "export-params.xml"
    
    project_file = output_dir / f"{project_name}.rsproj"
    if project_file.exists() and not overwrite:
        logger.info(f"Project file already exists: {project_file}")
        logger.info("Use --overwrite to recreate the project")
        return
    
    logger.info(f"Processing {len(image_files)} images from {input_dir}")
    logger.info(f"Output: {output_dir}")
    
    cmd = [
        "C:\\Program Files\\Epic Games\\RealityScan_2.0\\RealityScan.exe",
        "-headless",
        "-addFolder", str(input_dir),

        # General settings
        "-set", "unwrapMaxTexResolution=4096",

        # Alignment and reconstruction
        "-align",
        "-setReconstructionRegionAuto",
        "-scaleReconstructionRegion", "1.1", "1.1", "1.1", "center", "factor",
        
        # Generate base model
        "-calculateNormalModel",
        "-renameSelectedModel", "Normal",
        "-smooth",
        "-renameSelectedModel", "NormalSmooth",

        # Generate 100K model
        "-selectModel", "NormalSmooth",
        "-simplify", "100000",
        "-renameSelectedModel", "Normal100K",
        "-unwrap",
        "-calculateTexture",
        "-exportSelectedModel", str(output_dir / f"{project_name}.100k.glb"), str(export_params_file),
        
        # Generate 10K model
        "-selectModel", "NormalSmooth",
        "-simplify", "10000",
        "-renameSelectedModel", "Normal10K",
        "-unwrap",
        "-calculateTexture",
        "-exportSelectedModel", str(output_dir / f"{project_name}.10k.glb"), str(export_params_file),

        "-save", str(output_dir / f"{project_name}.rsproj"),
        "-quit"
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        output_files = list(output_dir.glob(f"{project_name}.*"))
        if output_files:
            logger.info(f"Successfully created {len(output_files)} files")
        else:
            logger.info("No files created", err=True)
            return 1
            
    except subprocess.CalledProcessError as e:
        logger.error(f"RealityScan failed with code {e.returncode}", err=True)
        return 1
    except Exception as e:
        logger.error(f"Error: {e}", err=True)
        return 1


if __name__ == "__main__":
    main()