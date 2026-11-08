"""Generate the Webots world from sim/scenario.py so the 3D scene and the planner use the same positions.

    .venv/Scripts/python sim/webots/make_world.py      ->  sim/webots/worlds/skyforge.wbt
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from sim.scenario import ALT, MOVER_ID, skyforge_world  # noqa: E402

CAM_FOV = 1.2            # rad horizontal (~69 deg): 27 m swath at 20 m
COLORS = {"mine": "1 0.45 0", "hostile": "0.9 0.1 0.1", "radio_shadow": "0.5 0.5 0.5"}


def solid(name, x, y, z, geom, color, transp=0.0, rot="0 0 1 0", def_=None, physics=False):
    head = f"DEF {def_} " if def_ else ""
    bound = f"boundingObject {geom}" if physics else ""
    return (f'{head}Solid {{ translation {x} {y} {z} rotation {rot} name "{name}" children [ Shape {{ '
            f'appearance PBRAppearance {{ baseColor {color} roughness 0.8 metalness 0 transparency {transp} }} '
            f'geometry {geom} }} ] {bound} }}')


def build():
    w = skyforge_world()
    bx, by = w.base
    out = ['#VRML_SIM R2025a utf8',
           'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/robots/dji/mavic/protos/Mavic2Pro.proto"',
           'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/humans/pedestrian/protos/Pedestrian.proto"',
           'WorldInfo { title "SKYFORGE coastal mission" basicTimeStep 8 '
           'defaultDamping Damping { linear 0.2 angular 0.5 } }',
           # chase camera: 8 m behind-left, 5 m above the drone, looking at it; keeps that offset in flight
           f'Viewpoint {{ orientation -0.1849 0.4463 0.8756 0.8837 position {bx - 8} {by - 8} 5.1 near 0.1 '
           'follow "Mavic 2 PRO" followType "Tracking Shot" followSmoothness 0.1 }',
           'Background { skyColor [ 0.55 0.72 0.95 ] }',
           'DirectionalLight { direction -0.4 0.3 -1 intensity 1.6 castShadows FALSE }',
           solid("sand", 100, 70, -0.05, "Box { size 260 200 0.1 }", "0.86 0.78 0.58", physics=True),
           solid("sea", 100, 195, -0.04, "Box { size 260 70 0.1 }", "0.1 0.35 0.65", physics=True),
           solid("home", bx, by, 0.01, "Cylinder { height 0.02 radius 2.5 }", "0.1 0.75 0.3")]
    k = 0
    for z in w.zones:
        x, y = z.center
        k += 1
        if z.kind == "obstacle" and z.id == MOVER_ID:
            out.append(solid("moving obstacle", x, y, 15, f"Box {{ size {2*z.radius} {2*z.radius} 30 }}",
                             "0.95 0.8 0.1", def_="MOVER"))
        elif z.kind == "obstacle" and z.radius > 3:
            out.append(solid(f"building {k}", x, y, 12.5, f"Box {{ size {1.4*z.radius} {1.4*z.radius} 25 }}",
                             "0.6 0.6 0.65", physics=True))
        elif z.kind == "obstacle":
            out.append(solid(f"tree {k}", x, y, 12.5, f"Cylinder {{ height 25 radius {z.radius} }}",
                             "0.2 0.5 0.2", physics=True))
        elif z.kind == "radio_shadow":
            out.append(solid(f"radio shadow {k}", x, y, 15, f"Cylinder {{ height 30 radius {z.radius} }}",
                             COLORS[z.kind], transp=0.85))
        else:   # mine / hostile: draw the exclusion disc
            out.append(solid(f"{z.kind} zone {k}", x, y, 0.03, f"Cylinder {{ height 0.04 radius {z.radius} }}",
                             COLORS[z.kind], transp=0.6))
            if z.kind == "hostile":
                out.append(solid(f"hostile unit {k}", x, y, 1, "Box { size 5 2.5 2 }", "0.25 0.3 0.2"))
    for cls, (x, y) in w.objects:
        k += 1
        if cls == "mine":
            out.append(solid(f"sea mine {k}", x, y, 0.6, "Sphere { radius 0.6 }", "0.15 0.15 0.15"))
        elif cls == "weapon":
            out.append(solid(f"weapon {k}", x, y, 0.08, "Box { size 1 0.15 0.12 }", "0.3 0.2 0.4"))
        else:
            out.append(solid(f"litter {k}", x, y, 0.15, "Cylinder { height 0.3 radius 0.1 }", "0.1 0.8 0.8"))
    for c in w.casualties:
        x, y = c.pos
        shirt = "0.8 0.1 0.1" if c.priority >= 5 else "0.9 0.7 0.2"
        out.append(f'Pedestrian {{ translation {x} {y} 0.2 rotation 0 1 0 1.5708 name "injured {c.id}" '
                   f'controller "<none>" shirtColor {shirt} }}')      # lying on the ground
    out.append(f'Mavic2Pro {{ translation {bx} {by} 0.1 controller "skyforge" supervisor TRUE '
               f'cameraSlot [ Camera {{ width 640 height 480 fieldOfView {CAM_FOV} }} ] '
               'bodySlot [ Display { name "yolo" width 640 height 480 } '
               # orange beacon above the drone so the audience can spot it (visual only, no mass/collision)
               'Pose { translation 0 0 0.25 children [ Shape { appearance PBRAppearance { baseColor 1 0.4 0 '
               'emissiveColor 1 0.4 0 roughness 1 metalness 0 } geometry Sphere { radius 0.15 } } ] } ] }')
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "worlds"), exist_ok=True)
    path = os.path.join(HERE, "worlds", "skyforge.wbt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote", path)
