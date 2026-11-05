"""Headless Blender scene script for orthographic still-image camera motion.

Invoked only by blender_backend.py:
  blender --background --factory-startup --python blender_scene.py -- --job <job.json>

Not imported by the main Python process. Uses only Blender's bundled Python.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    return parser.parse_args(argv)


def clear_scene(bpy):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights, bpy.data.worlds):
        for block in list(coll):
            coll.remove(block)


def build_plane(bpy, image_path, sw, sh, flip_v: bool, interpolation="Linear"):
    """Plane spans source pixel units; origin at image center.

    Default Blender plane size=2 has verts at +/-1. Scale (sw/2, sh/2) yields
    X in [-sw/2, sw/2], Y in [-sh/2, sh/2].
    Source top-left (0,0) -> Blender (-sw/2, +sh/2) when UV places file top on +Y.
    """
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "SourcePlane"
    plane.scale = (sw / 2.0, sh / 2.0, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    image = bpy.data.images.load(str(image_path))
    # Keep byte values close to file; treat as non-color if needed after QA.
    image.colorspace_settings.name = "sRGB"

    mat = bpy.data.materials.new(name="EmissionTexture")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = interpolation
    coord = nodes.new("ShaderNodeTexCoord")
    if flip_v:
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value[1] = -1.0
        mapping.inputs["Location"].default_value[1] = 1.0
        links.new(coord.outputs["UV"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    else:
        links.new(coord.outputs["UV"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    plane.data.materials.append(mat)

    # Flat world so out-of-frame is obvious during framing QA.
    world = bpy.data.worlds.new("FlatWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wnodes.clear()
    wout = wnodes.new("ShaderNodeOutputWorld")
    bg = wnodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    world.node_tree.links.new(bg.outputs["Background"], wout.inputs["Surface"])
    return plane, image


def configure_color(scene):
    scene.display_settings.display_device = "sRGB"
    # Standard avoids AgX tone-mapping wash; verified against checker whites.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    try:
        scene.sequencer_colorspace_settings.name = "sRGB"
    except Exception:
        pass


def configure_render(scene, width, height, engine_name, use_gpu: bool, samples=4):
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.film_transparent = False
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.use_file_extension = True

    # Under --factory-startup, Cycles may not appear in enum_items even when usable.
    chosen = engine_name
    try:
        scene.render.engine = chosen
    except Exception as exc:
        raise RuntimeError(f"Could not set requested render engine {engine_name!r}") from exc

    if chosen == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.seed = 0
        scene.cycles.use_animated_seed = False
        scene.cycles.use_denoising = False
        scene.cycles.filter_type = "BLACKMAN_HARRIS"
        scene.cycles.filter_width = 1.0
        scene.cycles.device = "GPU" if use_gpu else "CPU"
    elif chosen.startswith("BLENDER_EEVEE"):
        eevee = getattr(scene, "eevee", None)
        if eevee is not None:
            for attr, value in (
                ("taa_render_samples", 1),
                ("use_gtao", False),
                ("use_bloom", False),
                ("use_ssr", False),
                ("use_motion_blur", False),
            ):
                if hasattr(eevee, attr):
                    setattr(eevee, attr, value)
    elif chosen == "BLENDER_WORKBENCH":
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "TEXTURE"
    return chosen


def make_camera(bpy, sw, sh):
    data = bpy.data.cameras.new("OrthoCam")
    data.type = "ORTHO"
    data.shift_x = 0.0
    data.shift_y = 0.0
    data.clip_start = 0.1
    data.clip_end = max(sw, sh) * 10.0
    cam = bpy.data.objects.new("OrthoCam", data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    # Camera looks along local -Z; keep +Y as up.
    cam.rotation_euler = (0.0, 0.0, 0.0)
    cam.location = (0.0, 0.0, max(sw, sh))
    return cam


def set_camera_view(cam, view, sw, sh, out_w, out_h):
    x, y, w, h = view
    # Source top-left origin -> Blender center origin, Y-up.
    cx_src = (x + w / 2.0) * sw
    cy_src = (y + h / 2.0) * sh
    cx = cx_src - sw / 2.0
    cy = sh / 2.0 - cy_src
    cam.location = (cx, cy, cam.location.z)

    view_w = w * sw
    view_h = h * sh
    aspect = out_w / out_h
    if abs(view_w / view_h - aspect) > 1e-4:
        raise RuntimeError(f"View aspect {view_w / view_h} != output aspect {aspect}")
    # AUTO sensor fit: ortho_scale is the larger render axis in Blender units.
    if out_w >= out_h:
        cam.data.ortho_scale = view_w
    else:
        cam.data.ortho_scale = view_h
    cam.data.sensor_fit = "AUTO"


def projection_error(cam, scene, view, sw, sh):
    corners = cam.data.view_frame(scene=scene)
    xs = [p.x + cam.location.x + sw / 2 for p in corners]
    ys = [sh / 2 - p.y - cam.location.y for p in corners]
    x, y, w, h = view
    actual = [min(xs), min(ys), max(xs), max(ys)]
    expected = [x * sw, y * sh, (x + w) * sw, (y + h) * sh]
    return max(abs(a - b) for a, b in zip(actual, expected))


def main():
    import bpy

    args = parse_args(sys.argv)
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    image_path = Path(job["image"])
    frames_dir = Path(job["frames_dir"])
    frames_dir.mkdir(parents=True, exist_ok=True)
    width = int(job["width"])
    height = int(job["height"])
    sw, sh = job["source_size"]
    views = job["views"]
    start_frame = int(job.get("start_frame", 0))
    engine_pref = job.get("engine", "CYCLES")
    use_gpu = bool(job.get("use_gpu", False))
    # Default flip_v False: Blender image/UV already places file top on +Y for our plane.
    flip_v = bool(job.get("flip_v", False))

    clear_scene(bpy)
    scene = bpy.context.scene
    configure_color(scene)
    chosen = configure_render(scene, width, height, engine_pref, use_gpu, job.get("samples", 4))
    build_plane(bpy, image_path, sw, sh, flip_v=flip_v, interpolation=job.get("interpolation", "Linear"))
    cam = make_camera(bpy, sw, sh)

    report = {
        "engine": chosen,
        "blender_version": bpy.app.version_string,
        "frames_written": [],
        "uv_v_flipped": flip_v,
        "ortho_scale_rule": "max_axis_AUTO_sensor_fit",
        "plane_size_rule": "primitive_size2_scale_half_extent",
        "coordinate_system": "source_pixels_after_exif_top_left_origin",
        "use_gpu": use_gpu if chosen == "CYCLES" else chosen.startswith("BLENDER_EEVEE"),
        "samples": job.get("samples", 4),
        "interpolation": job.get("interpolation", "Linear"),
        "max_projection_boundary_error_source_px": 0.0,
    }

    for i in range(start_frame, len(views)):
        # Use frame_###### without extension; Blender appends .png when use_file_extension.
        stem = frames_dir / f"frame_{i:05d}"
        out_path = frames_dir / f"frame_{i:05d}.png"
        # Driver verified the prefix; rerender the suffix including corrupt frames.
        set_camera_view(cam, views[i], sw, sh, width, height)
        scene.frame_set(i + 1)
        error = projection_error(cam, scene, views[i], sw, sh)
        report["max_projection_boundary_error_source_px"] = max(report["max_projection_boundary_error_source_px"], error)
        if error > .005:
            raise RuntimeError(f"Camera projection differs from requested view by {error} source pixels")
        scene.render.filepath = str(stem.resolve())
        bpy.ops.render.render(write_still=True)
        if not out_path.exists():
            # Some builds write exactly filepath as given.
            alt = Path(str(stem))
            if alt.exists() and not out_path.exists():
                alt.rename(out_path)
        if not out_path.exists():
            raise RuntimeError(f"Blender did not write {out_path}")
        report["frames_written"].append(str(out_path))

    report_path = Path(job["report_path"])
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("CAMERA_MOTION_BLENDER_DONE", len(report["frames_written"]), flush=True)


if __name__ == "__main__":
    main()
