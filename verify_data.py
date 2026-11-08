"""复算公开数据包中的论文指标，并核对轨迹文件。"""
import csv
import hashlib
import math
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def total(rows, strategy, surface=None, role=None, case=None):
    selected = [
        float(r["lap_time_s"])
        for r in rows
        if r["strategy"] == strategy
        and (surface is None or r["surface"] == surface)
        and (role is None or r["circuit_role"] == role)
        and (case is None or r["case"] == case)
    ]
    assert selected, (strategy, surface, role, case)
    return math.fsum(selected)


def retained(rows, strategy, surface=None):
    equal = total(rows, "equal", surface)
    free = total(rows, "free", surface)
    return 100 * (equal - total(rows, strategy, surface)) / (equal - free)


def check_trajectories():
    entries = read_csv("trajectories/index.csv")
    assert len(entries) == 268
    index = {r["trajectory_id"]: r for r in entries}
    assert len(index) == len(entries)
    for r in entries:
        path = ROOT / r["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == r["sha256"], path
        nodes = int(r["mesh_nodes"])
        points = int(r["collocation_points"])
        assert points == 3 * (nodes - 1)
        with np.load(path, allow_pickle=False) as a:
            expected = {
                "distance_m": (nodes,),
                "curvature_per_m": (nodes,),
                "time_s": (nodes,),
                "state": (10, nodes),
                "control": (5, nodes),
                "load_transfer": (2, nodes),
                "collocation_distance_m": (points,),
                "collocation_state": (10, points),
            }
            assert set(a.files) == set(expected)
            for name, shape in expected.items():
                assert a[name].shape == shape and np.isfinite(a[name]).all(), (path, name)
            assert np.all(np.diff(a["distance_m"]) > 0)
            assert np.all(np.diff(a["time_s"]) > 0)
            assert abs(a["time_s"][-1] - float(r["lap_time_s"])) < 1e-8
    return index


def check_join(index):
    counts = {
        "dry_gain": 35, "surface_transfer": 84, "held_out_structure": 54,
        "cg_height": 126, "parameter_transfer": 84,
    }
    found = {}
    for table, count in counts.items():
        rows = read_csv(f"results/{table}.csv")
        assert len(rows) == count
        found[table] = rows
        for r in rows:
            item = index[r["trajectory_id"]]
            assert r["circuit"] == item["circuit"]
            assert abs(float(r["lap_time_s"]) - float(item["lap_time_s"])) < 1e-5
    return found


def check_diagnostics(name, results, original, expected):
    rows = read_csv(f"diagnostics/{name}.csv")
    ids = {r["trajectory_id"] for r in results}
    assert len(ids) == original
    assert all(r["original_accepted"] == "true" for r in results)
    assert all(r["full_supplemental_pass"] == "false" for r in results)
    assert len(rows) == original * 12
    checks = {r["check"] for r in rows}
    count = Counter()
    seen = set()
    for r in rows:
        key = r["trajectory_id"], r["check"]
        assert key not in seen and key[0] in ids
        seen.add(key)
        if r["check"] == "Full supplementary diagnostic":
            assert r["passed"] == "false"
        else:
            count[r["check"]] += float(r["worst_value"]) <= float(r["tolerance"])
            assert (r["passed"] == "true") == (float(r["worst_value"]) <= float(r["tolerance"]))
    assert len(checks) == 12
    assert [count[x] for x in (
        "Collocation dynamics and state continuity",
        "All supplementary path constraints",
        "Four friction ellipse constraints",
        "Algebraic load transfer closure",
        "Positive wheel-load constraints",
        "Wheel slip constraints",
        "Available vehicle power constraint",
        "All input slew limits",
        "Rear motor torque ceiling",
        "Rear motor power ceilings",
        "Front motor power ceiling",
        "Full supplementary diagnostic",
    )] == expected
    print(f"{name}: {original}/{original} original passes, 0/{original} full supplementary passes")


def main():
    index = check_trajectories()
    rows = check_join(index)
    dry, wet = rows["dry_gain"], rows["surface_transfer"]
    delta = total(dry, "constant") - total(dry, "fitted_dry")
    held = total(dry, "constant", role="held_out") - total(dry, "fitted_dry", role="held_out")
    assert f"{delta:.3f}" == "1.961" and f"{held:.3f}" == "0.716"
    assert f"{retained(dry, 'fitted_dry'):.2f}" == "95.24"
    assert [f"{retained(wet, s, 'wet'):.2f}" for s in (
        "fitted_dry", "fitted_special", "fitted_joint"
    )] == ["34.28", "95.09", "72.37"]
    for surface, value in [("dry", "0.068"), ("wet", "0.240")]:
        full = total(rows["held_out_structure"], f"longitudinal_simple_{surface}", surface)
        simple = total(rows["held_out_structure"], f"steering_only_{surface}", surface)
        assert f"{simple-full:.3f}" == value
    for case, value in [("h400", "0.704"), ("h600", "0.537")]:
        height = rows["cg_height"]
        assert f"{total(height, 'fitted_frozen', case=case)-total(height, 'fitted_updated', case=case):.3f}" == value
    for surface, size in [("dry", 4500), ("wet", 4103), ("pooled", 8603)]:
        teacher = read_csv(f"calibration/teacher_{surface}.csv")
        assert len(teacher) == size
        assert {r["circuit"] for r in teacher} == {"zhejiang", "shanghai", "milford", "madrid"}
        if surface == "pooled":
            weight = [math.fsum(float(r["mesh_sample_weight"]) for r in teacher if r["surface"] == s) for s in ("dry", "wet")]
            assert math.isclose(*weight, rel_tol=1e-10)
    coefficients = read_csv("calibration/bernstein_coefficients.csv")
    sets = Counter((r["batch"], r["surface"], r["structure"]) for r in coefficients)
    assert len(sets) == 10 and all(n == 16 for n in sets.values())
    assert all(float(r["coefficient"]) >= 0 for r in coefficients)
    check_diagnostics("surface_transfer", rows["surface_transfer"], 77, [77,0,0,0,77,34,77,5,77,23,26,0])
    check_diagnostics("held_out_structure", rows["held_out_structure"], 54, [54,0,0,0,54,23,54,4,54,9,31,0])
    print(f"{len(index)} trajectory files checked. Dry 16-coefficient gain over fitted scalar: {delta:.3f} s.")


if __name__ == "__main__":
    main()
    from verify_supplement import main as check_supplement
    check_supplement()

