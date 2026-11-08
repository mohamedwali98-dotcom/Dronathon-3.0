"""Generate the Webots world from sim/scenario.py so the 3D scene and the planner use the same positions.

    .venv/Scripts/python sim/webots/make_world.py      ->  sim/webots/worlds/skyforge.wbt
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from sim.scenario import ALT, MOVER_ID, skyforge_world  # noqa: E402

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
           'WorldInfo { title "SKYFORGE coastal mission" basicTimeStep 8 '
           'defaultDamping Damping { linear 0.2 angular 0.5 } }',
           f'Viewpoint {{ orientation -0.25 0.25 0.93 1.64 position {bx} {by - 45} 40 near 0.2 '
           'follow "Mavic 2 PRO" followSmoothness 0.2 }',
           'Background { skyColor [ 0.55 0.72 0.95 ] }',
           'DirectionalLight { direction -0.4 0.3 -1 intensity 3 castShadows FALSE }',
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
        out.append(solid(f"injured {c.id}", x, y, 0.25, "Capsule { height 1.3 radius 0.25 }",
                         "0.85 0.2 0.2" if c.priority >= 5 else "0.9 0.7 0.2", rot="0 1 0 1.5708"))
    out.append(f'Mavic2Pro {{ translation {bx} {by} 0.1 controller "skyforge" supervisor TRUE '
               'cameraSlot [ Camera { width 400 height 240 } ] }')
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "worlds"), exist_ok=True)
    path = os.path.join(HERE, "worlds", "skyforge.wbt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote", path)
