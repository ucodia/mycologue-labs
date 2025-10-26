import bpy, sys, os, math
from mathutils import Vector, Matrix

def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--")+1:] if "--" in argv else []
    input_path = None
    output_dir = None
    overwrite = False
    make_video = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--input","-i"):
            if i+1 >= len(argv): raise SystemExit("Error: --input requires a value")
            input_path = argv[i+1]; i += 2
        elif a in ("--output","-o"):
            if i+1 >= len(argv): raise SystemExit("Error: --output requires a value")
            output_dir = argv[i+1]; i += 2
        elif a == "--overwrite":
            overwrite = True; i += 1
        elif a == "--video":
            make_video = True; i += 1
        elif a in ("--help","-h"):
            print("Usage: blender --background --python create-preview.py -- --input PATH [--output DIR] [--overwrite] [--video]"); raise SystemExit(0)
        else:
            if not input_path: input_path = a
            i += 1
    if not input_path: raise SystemExit("Error: --input is required")
    return input_path, output_dir, overwrite, make_video

model_path, output_dir, overwrite, make_video = parse_args()

if output_dir:
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    out_path = os.path.join(output_dir, f"{model_name}-preview.mp4" if make_video else f"{model_name}-preview.png")
else:
    out_path = os.path.splitext(model_path)[0] + ("-preview.mp4" if make_video else "-preview.png")

out_path = os.path.abspath(out_path)
os.makedirs(os.path.dirname(out_path), exist_ok=True)

if os.path.exists(out_path) and not overwrite:
    print(f"Preview already exists: {out_path}")
    print("Use --overwrite to recreate the preview")
    raise SystemExit(0)
if os.path.exists(out_path) and overwrite:
    try:
        os.remove(out_path)
    except OSError:
        pass

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
    if not m.use_nodes: continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type=="BSDF_PRINCIPLED"), None)
    if not bsdf: continue
    set_socket(bsdf, ["Metallic"], 0.0)
    set_socket(bsdf, ["Specular","Specular IOR Level"], 0.05)
    set_socket(bsdf, ["Clearcoat"], 0.0)
    set_socket(bsdf, ["Roughness"], 0.9)
    n = bsdf.inputs.get("Normal")
    if n and n.is_linked:
        for lk in list(n.links):
            nt.links.remove(lk)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes: raise SystemExit("No mesh objects")

mins = Vector((float("inf"),)*3); maxs = Vector((float("-inf"),)*3)
for o in meshes:
    for c in o.bound_box:
        v = o.matrix_world @ Vector(c)
        mins.x=min(mins.x,v.x); mins.y=min(mins.y,v.y); mins.z=min(mins.z,v.z)
        maxs.x=max(maxs.x,v.x); maxs.y=max(maxs.y,v.y); maxs.z=max(maxs.z,v.z)
center=(mins+maxs)*0.5
size=(maxs-mins)
max_dim=max(size.x,size.y,size.z) or 1.0

for o in meshes:
    o.matrix_world = Matrix.Translation(-center) @ o.matrix_world
center = Vector((0.0,0.0,0.0))

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
sc.render.use_file_extension = True

if "--video" in sys.argv:
    fps = 30
    dur = 10
    rig = bpy.data.objects.new("Rig", None)
    bpy.context.scene.collection.objects.link(rig)
    rig.location = center
    for o in meshes:
        o.parent = rig
        o.matrix_parent_inverse = rig.matrix_world.inverted()
    sc.frame_start = 1
    sc.frame_end = fps*dur
    rig.rotation_mode = 'XYZ'
    rig.rotation_euler = (0.0,0.0,0.0)
    rig.keyframe_insert(data_path="rotation_euler", frame=sc.frame_start)
    rig.rotation_euler = (0.0,0.0,math.tau)
    rig.keyframe_insert(data_path="rotation_euler", frame=sc.frame_end)
    for fc in rig.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    amp = max_dim * 0.04   # subtle float amplitude
    osc_per_rot = 2        # number of up/down cycles per full rotation
    total_frames = fps * dur
    d = rig.driver_add("location", 2).driver
    d.type = 'SCRIPTED'
    d.expression = f"{amp} * sin(2 * 3.14159 * {osc_per_rot} * frame / {total_frames})"
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    sc.render.ffmpeg.gopsize = 12
    sc.render.ffmpeg.audio_codec = 'AAC'
    sc.render.fps = fps
    sc.render.filepath = out_path
    bpy.ops.render.render(animation=True)
    if not os.path.exists(out_path):
        raise SystemExit("MP4 not written")
    print(out_path)
else:
    sc.frame_set(1)
    sc.render.image_settings.file_format='PNG'
    sc.render.filepath=out_path
    bpy.ops.render.render(write_still=True)
    img=bpy.data.images.get("Render Result")
    if img: img.save_render(out_path)
    if not os.path.exists(out_path):
        raise SystemExit("Image not written")
    print(out_path)
