# Stability Statistics Analysis Notes

## Goal

This analysis is for channel/measurement behavior only:
distribution, variability, fading depth, and scenario separability.

It is explicitly different from `distance_measurement` analysis:

- `distance_measurement`: distance-estimation models and distance error metrics.
- `stability_statistics`: channel/measurement statistics only.

No distance-estimation error metrics (MAE/RMSE distance) are computed here.

## Run command

```bash
python tools/analyze_wifi_stability_statistics.py \
  --data_dir experiments/1_2_3_4_5m_los_nlos \
  --out_dir out/stability_statistics \
  --seed 42
```

Optional:

- `--window_sizes "25,50,100"` rolling windows for temporal variability.
- `--acf_max_lag 200` ACF horizon.
- `--distance_focus <float>` fixed distance for temporal analysis; default is most frequent distance.

## What each required figure means

- `ecdf_rssi_by_scenario.png`:
  Empirical CDF of RSSI per scenario.
- `ecdf_csi_mean_amp_by_scenario.png`:
  Empirical CDF of CSI mean amplitude per scenario.
- `hist_rssi_los_vs_nlos.png`:
  Histogram + KDE-like curve for RSSI comparing LoS vs NLoS.
- `hist_csi_cv_los_vs_nlos.png`:
  Histogram + KDE-like curve for CSI CV proxy comparing LoS vs NLoS.
- `rolling_std_rssi.png`:
  Rolling standard deviation of RSSI (windows 25/50/100).
- `rolling_std_csi.png`:
  Rolling standard deviation of CSI mean_amp and CV_amp (windows 25/50/100).
- `acf_rssi.png`:
  RSSI autocorrelation over lag.
- `acf_csi_mean_amp.png`:
  Mean amplitude autocorrelation over lag.
- `boxplot_fading_depth_rssi.png`:
  Scenario-wise distribution of RSSI fading depth (`p95-p5`) per run-distance group.
- `boxplot_fading_depth_csi.png`:
  Scenario-wise distribution of CSI fading depth (`p95-p5`) per run-distance group.
- `pca_separability.png`:
  Exploratory PCA scatter for LoS vs NLoS using RSSI+CSI packet features.

Additional generated exploratory figures:

- `timeseries_rssi_focus.png`
- `timeseries_mean_amp_focus.png`

These are the requested 2000-packet temporal traces for the selected focus distance.

## Tables

- `table_dataset_summary.csv`: packet count, scenario/run/distance coverage.
- `table_skew_kurt_by_scenario.csv`: Fisher skewness and excess kurtosis by scenario.
- `table_fading_depth_by_scenario.csv`: median fading depth by scenario.
- `table_separability_scores.csv`: silhouette scores (LoS vs NLoS) for RSSI-only, CSI-only, combined features.
