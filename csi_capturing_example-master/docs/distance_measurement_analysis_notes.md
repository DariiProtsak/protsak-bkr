# Distance Measurement Analysis Notes

## Run command

```bash
python tools/analyze_wifi_distance_measurement.py \
  --data_dir experiments/1_2_3_4_5m_los_nlos \
  --out_dir out/distance_measurement \
  --seed 42
```

Optional flags:

- `--use_pca`: use only summary + PCA CSI features for kNN.
- `--knn_k <int>`: set k for kNN distance regression (default: 7).
- `--test_size <float>`: grouped test split fraction (default: 0.3).
- `--group_col <name>`: group column for leakage-safe split (default: `run_id`).

## Split protocol (leakage control)

- The script uses `GroupShuffleSplit` from scikit-learn.
- Grouping defaults to `run_id`, so packets from one run are never split between train and test.
- With this dataset (`run_id` in `{1, 2}`), one run is selected for train and the other for test.
- PCA and model fitting are train-only; test packets are transformed/predicted using train-fitted objects.

## Models included

- RSSI baseline: log-distance model fitted on train packets.
- Stabilized RSSI variant: same model form on burst-median RSSI.
- CSI model: kNN regression on CSI-derived features (unified and per-scenario versions).

## Output files

- `out/distance_measurement/tables/table_metrics_overall.csv`
- `out/distance_measurement/tables/table_metrics_by_scenario.csv`
- `out/distance_measurement/figs/cdf_error.png`
- `out/distance_measurement/figs/scatter_pred_vs_true.png`
- `out/distance_measurement/figs/boxplot_error_by_scenario.png`
- `out/distance_measurement/figs/timeseries_stability.png`
- `out/distance_measurement/report.md`
