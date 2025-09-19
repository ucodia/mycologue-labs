#!/usr/bin/env python3

import subprocess
from pathlib import Path
from typing import Optional
import click


def run_realityscan(input_dir: Path, output_dir: Path, project_name: str) -> bool:
    """
    Run RealityScan to generate 3D models from images.
    
    Args:
        input_dir: Directory containing input images
        output_dir: Directory to save output models
        project_name: Name for the project and output files
    
    Returns:
        True if successful, False otherwise
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    
    hi_glb = output_dir / f"{project_name}.high.glb"
    hi_fbx = output_dir / f"{project_name}.high.fbx"
    low_glb = output_dir / f"{project_name}.low.glb"
    low_fbx = output_dir / f"{project_name}.low.fbx"
    project_file = output_dir / f"{project_name}.rsproj"
    
    rs_args = [
        "C:\\Program Files\\Epic Games\\RealityScan_2.0\\RealityScan.exe",
        "-headless",
        "-addFolder", str(input_dir),
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
        
        # High-poly model
        "-calculateHighModel",
        "-unwrap",
        "-calculateTexture",
        
        # Low-poly model
        "-simplify", "10000",
        "-smooth",
        "-unwrap",
        "-calculateTexture",
        
        # Export models
        "-exportModel", '"Model 1"', str(hi_fbx),
        "-exportModel", '"Model 3"', str(low_fbx),
        "-exportModel", '"Model 1"', str(hi_glb),
        "-exportModel", '"Model 3"', str(low_glb),
        
        # Save & quit
        "-save", str(project_file),
        "-quit"
    ]
    
    try:
        click.echo(f"Running RealityScan for project: {project_name}")
        click.echo(f"Input path (resolved): {input_dir}")
        click.echo(f"Output path (resolved): {output_dir}")
        click.echo(f"Command: {' '.join(rs_args[:5])} ... (truncated)")
        
        realityscan_exe = Path(rs_args[0])
        if not realityscan_exe.exists():
            click.echo(f"RealityScan executable not found: {realityscan_exe}", err=True)
            return False
        
        result = subprocess.run(rs_args, cwd=str(input_dir.parent))
        
        files_created = []
        for file_path, name in [(hi_glb, "High-poly GLB"), (hi_fbx, "High-poly FBX"), 
                               (low_glb, "Low-poly GLB"), (low_fbx, "Low-poly FBX"), 
                               (project_file, "RS project")]:
            if file_path.exists():
                files_created.append((file_path, name))
        
        if files_created:
            click.echo("== Files Created ==")
            for file_path, name in files_created:
                click.echo(f" {name}: {file_path}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running RealityScan: {e}", err=True)
        if e.stdout:
            click.echo(f"Output: {e.stdout}", err=True)
        if e.stderr:
            click.echo(f"Error output: {e.stderr}", err=True)
        return False
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        return False


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
    """
    Generate 3D models from images using RealityScan.
    
    This script processes images in a directory to create high and low-poly 3D models
    using Epic Games RealityScan photogrammetry software.
    """
    image_files = [
        f for f in input.iterdir() 
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg']
    ]
    
    if not image_files:
        click.echo("No image files found in the specified input directory.", err=True)
        return
    
    click.echo(f"Found {len(image_files)} image file(s) to process")
    
    if output is None:
        output_dir = input / "models"
    else:
        output_dir = output
    
    project_name = input.name
    
    click.echo(f"Input directory: {input}")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"Project name: {project_name}")
    
    success = run_realityscan(input, output_dir, project_name)
    
    if success:
        click.echo("\n3D model generation completed successfully")
    else:
        click.echo("\n3D model generation failed", err=True)
        return 1


if __name__ == "__main__":
    main()