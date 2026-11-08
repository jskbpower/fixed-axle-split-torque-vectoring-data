# Fixed axle split rear torque vectoring data

This repository contains the numerical data for *Rear Torque Vectoring Feedforward for Lap Time Optimisation with a Fixed Axle Split in a Three Motor Electric Vehicle* by Longjie Ren and Lin Chen. The vehicle model uses a fixed 35% front share of positive drive torque. Uniform road friction is 0.92 for dry and 0.60 for wet. Zhejiang, Shanghai, Milford and Madrid are the development circuits. Suzuka, Nürburgring and Sepang are held out.

## Files

| Path | Contents |
| --- | --- |
| `results/dry_gain.csv` | 35 dry laps with equal rear torque, fixed G = 2, fitted scalar G, the 16-coefficient dry map or free rear torque bias. |
| `results/surface_transfer.csv` | 84 principal dry/wet entries for 77 distinct trajectories. The dry map and dry matched calibration share the same seven trajectories. |
| `results/held_out_structure.csv` | 54 trajectories for the same-coefficient-count comparison, including the equal, fitted scalar and rear-free references. |
| `results/cg_height.csv` | Seven-circuit dry comparison at 0.400, 0.495 and 0.600 m. |
| `results/parameter_transfer.csv` | Zhejiang and Shanghai cases for centre-of-gravity height, mass and coupled front weight/roll shares. |
| `results/teacher_structure_errors.csv` | Teacher error for the two structures under the three regularisation choices. |
| `calibration/teacher_{dry,wet,pooled}.csv` | 4500 dry samples, 4103 wet samples, and their 8603-row pooled fit input with rebalanced weights. |
| `calibration/bernstein_coefficients.csv` | Three principal, six common-curvature and one parameter-transfer 4 × 4 matrices, with speed basis index `i` and rear axle torque basis index `j`. |
| `calibration/scalar_gains.csv` | The fixed and fitted scalar gains. |
| `trajectories/index.csv` | 258 distinct archived trajectories across the result tables, with file names, dimensions, lap times and SHA-256 checksums. |
| `trajectories/*.npz` | Numerical mesh-node and Legendre-point arrays in physical units. |
| `diagnostics/*.csv` | Recorded per-trajectory check values, tolerances and outcomes for the principal and held-out comparisons. |
| `verify_data.py` | Recomputes the article's headline differences, retention values and diagnostic counts and checks each trajectory file. |

## Results and strategies

The comparison tables join to the trajectory index on `trajectory_id`. Repeated entries and shared references can use one ID. Each study table defines its own paired equal and rear-free reference laps. The lap time is the integrated time. The objective, where provided, also includes the numerical penalties. A blank field indicates that the quantity is not recorded in that summary table.

- `equal` sets the rear torque difference to zero. `free` leaves it free within the specified vehicle model and fixed axle split.
- `fixed_g2` and `constant` are the historical fixed G = 2 and teacher-fitted scalar, respectively.
- In the principal comparison, `fitted_dry` uses the dry map, `fitted_special` uses the map matched to the evaluation surface, and `fitted_joint` uses the pooled map.
- In the held-out comparison, `longitudinal_simple_*` is the load transfer structure. `steering_only_*` is the simplified steering-angle structure. The suffix `joint` denotes pooled calibration. These six coefficient sets use the common output-curvature rule.
- In the parameter comparisons, `fitted_frozen` and `fitted_updated` use the same principal dry coefficients. Their physical load factors use nominal and updated parameters, respectively. `constant_frozen` and `constant_updated` apply the same distinction to the fitted scalar. `steering` uses the frozen simplified dry structure from the original coefficient-regularised fit, recorded under the parameter-transfer batch.
- `h400`, `h495` and `h600` are heights in mm. `m2300` and `m2700` are masses in kg with fixed yaw inertia. `f400` and `f600` correspond to 40% and 60% front static weight and lateral load transfer shares, changed together. `nominal` uses 2503 kg, 0.495 m and 50% front static weight and lateral load transfer shares.

Saving is relative to equal rear torque at the same circuit and evaluation condition. Aggregate retention is the sum of strategy savings divided by the sum of rear-free savings, multiplied by 100. Compute sums before rounding. Teacher rows contain the values and distance weights used for the fit. Rear difference is rear-right minus rear-left torque. Wheel speed columns use rad/s.

## Trajectory array schema

| Key | Shape | Meaning |
| --- | --- | --- |
| `distance_m` | (N,) | Centreline distance at mesh nodes, including both endpoints. |
| `curvature_per_m` | (N,) | Centreline curvature at mesh nodes. |
| `time_s` | (N,) | Integrated time from the lap start. |
| `state` | (10, N) | Physical vehicle states in the order listed below. |
| `control` | (5, N) | Physical control channels in the order listed below. |
| `load_transfer` | (2, N) | Algebraic longitudinal and lateral load transfer, in N. |
| `collocation_distance_m` | (3(N−1),) | Three interior points per interval in interval order. |
| `collocation_state` | (10, 3(N−1)) | Physical states at those interior points, in the same channel order as `state`. |

State order is longitudinal and lateral speed (m/s), yaw rate (rad/s), lateral offset (m), heading error (rad), wheel speeds (rad/s) for front left, front right, rear left and rear right, and battery state of charge (fraction). Control order is total positive drive torque (N·m), signed total brake torque (N·m, nonpositive), front road-wheel steering angle (rad), aerodynamic input (fixed at zero), and rear torque difference (N·m). The interior points are stored in increasing distance, with three consecutive points per interval.

The original discrete acceptance and the supplementary diagnostics are reported separately. The principal set has 77/77 original passes and 0/77 complete supplementary passes. The held-out structure set has 54/54 original passes and 0/54 complete supplementary passes. The dynamics and continuity row records a scaled equation residual. Other path checks report scaled excesses. The input slew row counts an all-channel pass using the stored maximum and a tolerance of 0.05 in each corresponding physical unit. The published table omits a single magnitude for the mixed-unit slew row. The stored trajectories are local discrete solutions. Continuous feasibility between nodes remains unverified.

## Check the data

Install NumPy in your Python environment, then run:

```bash
python verify_data.py
```

The checks run on the exported records. Re-solving the original lap optimisation requires the original model and solver configuration. Use the article and its Supplemental Material for the method, parameter values and acceptance definitions. The citation metadata are in `CITATION.cff`.

## 中文索引

`results` 是圈时与教师误差表，`calibration` 是教师样本和冻结系数，`trajectories` 是节点及配点轨迹，`diagnostics` 是两批逐条验收诊断。用 `trajectory_id` 关联。运行 `verify_data.py` 可核对圈时收益、两批验收计数和轨迹文件校验值。

