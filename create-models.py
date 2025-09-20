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
        "-align",
        "-setReconstructionRegionAuto",
        "-scaleReconstructionRegion", "1.1", "1.1", "1.1", "center", "factor",
        
        # Texture settings
        "-set", "UnwrapMaxTextureSize=4096",
        "-set", "UnwrapMaxChartsCount=0",
        "-set", "TextureMaxSize=4096",
        "-set", "TextureFileType=png",
        "-set", "TextureIsPowerOf2=1",
        "-set", "TextureIsSquare=1",
        "-set", "TextureImageFill=1",
        "-set", "TextureNormalSpace=tangent",
        "-set", "TextureNormalStyle=DirectX",
        
        # Process
        "-calculateHighModel",
        "-unwrap",
        "-calculateTexture",
        "-simplify", "10000",
        "-smooth",
        "-unwrap",
        "-calculateTexture",
        
        # Export - use absolute paths
        "-exportModel", "Model 1", str(output_dir / f"{project_name}.high.fbx"),
        "-exportModel", "Model 3", str(output_dir / f"{project_name}.low.fbx"),
        "-exportModel", "Model 1", str(output_dir / f"{project_name}.high.glb"),
        "-exportModel", "Model 3", str(output_dir / f"{project_name}.low.glb"),
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