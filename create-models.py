#!/usr/bin/env python3

import subprocess
from pathlib import Path
from typing import Optional
import click


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
def main(input: Path, output: Optional[Path]):
    """Generate 3D models from images using RealityScan."""
    
    # Check for image files
    image_files = [f for f in input.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg']]
    
    if not image_files:
        click.echo("No image files found.", err=True)
        return
    
    # Setup paths
    output_dir = output if output else input / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_name = input.name
    
    click.echo(f"Processing {len(image_files)} images from {input}")
    click.echo(f"Output: {output_dir}")
    
    # RealityScan command
    cmd = [
        "C:\\Program Files\\Epic Games\\RealityScan_2.0\\RealityScan.exe",
        "-headless",
        "-addFolder", str(input.resolve()),
        "-align",
        "-setReconstructionRegionAuto",
        
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
        
        # Export
        "-exportModel", '"Model 1"', str(output_dir / f"{project_name}.high.fbx"),
        "-exportModel", '"Model 3"', str(output_dir / f"{project_name}.low.fbx"),
        "-exportModel", '"Model 1"', str(output_dir / f"{project_name}.high.glb"),
        "-exportModel", '"Model 3"', str(output_dir / f"{project_name}.low.glb"),
        "-save", str(output_dir / f"{project_name}.rsproj"),
        "-quit"
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        output_files = list(output_dir.glob(f"{project_name}.*"))
        if output_files:
            click.echo(f"✓ Created {len(output_files)} files")
        else:
            click.echo("✗ No files created", err=True)
            return 1
            
    except subprocess.CalledProcessError as e:
        click.echo(f"✗ RealityScan failed: {e.returncode}", err=True)
        return 1
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        return 1


if __name__ == "__main__":
    main()