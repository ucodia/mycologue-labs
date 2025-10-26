import bpy, sys, os, math
from mathutils import Vector

def parse_args():
    """Parse command line arguments."""
    argv = sys.argv
    argv = argv[argv.index("--")+1:] if "--" in argv else []
    
    # Default values
    input_path = None
    output_dir = None
    overwrite = False
    
    i = 0
    while i < len(argv):
        if argv[i] == "--input" or argv[i] == "-i":
            if i + 1 < len(argv):
                input_path = argv[i + 1]
                i += 2
            else:
                raise SystemExit("Error: --input requires a value")
        elif argv[i] == "--output" or argv[i] == "-o":
            if i + 1 < len(argv):
                output_dir = argv[i + 1]
                i += 2
            else:
                raise SystemExit("Error: --output requires a value")
        elif argv[i] == "--overwrite":
            overwrite = True
            i += 1
        elif argv[i] == "--help" or argv[i] == "-h":
            print("Usage: blender --background --python create-preview.py -- [options]")
            print()
            print("Options:")
            print("  --input, -i PATH     Input 3D model file (.glb, .gltf, .obj, .fbx)")
            print("  --output, -o DIR     Output directory for preview image")
            print("  --overwrite          Overwrite existing preview files")
            print("  --help, -h           Show this help message")
            raise SystemExit(0)
        else:
            # Assume it's the input file for backward compatibility
            if not input_path:
                input_path = argv[i]
            i += 1
    
    if not input_path:
        raise SystemExit("Error: --input is required")
    
    return input_path, output_dir, overwrite

# Parse arguments
model_path, output_dir, overwrite = parse_args()

# Determine output path
if output_dir:
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    out_path = os.path.join(output_dir, f"{model_name}-preview.png")
else:
    out_path = os.path.splitext(model_path)[0] + "-preview.png"

# Check for overwrite early to avoid unnecessary rendering
if os.path.exists(out_path) and not overwrite:
    print(f"Preview already exists: {out_path}")
    print("Use --overwrite to recreate the preview")
    raise SystemExit(0)

# Ensure output directory exists
os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

ext = os.path.splitext(model_path)[1].lower()
if ext == ".obj":
    bpy.ops.import_scene.obj(filepath=model_path)
elif ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=model_path)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=model_path)
else:
    raise SystemExit(f"Unsupported: {ext}")

def set_socket(bsdf, names, value):
    for n in names:
        s = bsdf.inputs.get(n)
        if s:
            if s.is_linked:
                for lk in list(s.links):
                    bsdf.id_data.links.remove(lk)
            s.default_value = value
            return

for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type=="BSDF_PRINCIPLED"), None)
    if not bsdf:
        continue
    set_socket(bsdf, ["Metallic"], 0.0)
    set_socket(bsdf, ["Specular","Specular IOR Level"], 0.05)
    set_socket(bsdf, ["Clearcoat"], 0.0)
    set_socket(bsdf, ["Roughness"], 0.9)
    n = bsdf.inputs.get("Normal")
    if n and n.is_linked:
        for lk in list(n.links):
            nt.links.remove(lk)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("No mesh objects")

from mathutils import Vector
mins = Vector((float("inf"),)*3); maxs = Vector((float("-inf"),)*3)
for o in meshes:
    for c in o.bound_box:
        v = o.matrix_world @ Vector(c)
        mins.x=min(mins.x,v.x); mins.y=min(mins.y,v.y); mins.z=min(mins.z,v.z)
        maxs.x=max(maxs.x,v.x); maxs.y=max(maxs.y,v.y); maxs.z=max(maxs.z,v.z)
center=(mins+maxs)*0.5
size=(maxs-mins)
max_dim=max(size.x,size.y,size.z) or 1.0

bpy.ops.object.camera_add()
cam=bpy.context.object
bpy.context.scene.camera=cam
fov=math.radians(50.0)
dist=(max_dim*0.5)/math.tan(fov*0.5)*2.0
cam.location=center+Vector((0.0,-dist,dist*0.2))
empty=bpy.data.objects.new("Aim",None)
bpy.context.scene.collection.objects.link(empty)
empty.location=center
con=cam.constraints.new(type="TRACK_TO")
con.target=empty
con.track_axis="TRACK_NEGATIVE_Z"
con.up_axis="UP_Y"
cam.data.lens_unit='FOV'
cam.data.angle=fov
cam.data.clip_start=dist*0.001
cam.data.clip_end=dist*100.0

bpy.ops.object.light_add(type='AREA', location=center+Vector((dist*0.8,-dist*0.6,dist*0.6)))
key=bpy.context.object
key.data.energy=4000.0
key.data.size=max_dim
bpy.ops.object.light_add(type='AREA', location=center+Vector((-dist*0.6,-dist*0.4,dist*0.3)))
fill=bpy.context.object
fill.data.energy=1800.0
fill.data.size=max_dim

if not bpy.context.scene.world:
    bpy.context.scene.world=bpy.data.worlds.new("World")
w=bpy.context.scene.world
w.use_nodes=True
bg=w.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value=(0.9,0.9,0.9,1.0)
bg.inputs["Strength"].default_value=1.0

sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE_NEXT'
sc.view_settings.view_transform='Standard'
sc.render.resolution_x=1024
sc.render.resolution_y=1024
sc.render.film_transparent=False
sc.render.image_settings.file_format='PNG'
sc.render.filepath=out_path

bpy.ops.render.render(write_still=True)
img=bpy.data.images.get("Render Result")
if img: img.save_render(out_path)
print(out_path)
