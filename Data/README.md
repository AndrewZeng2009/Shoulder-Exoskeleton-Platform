# Trial-level data

`trial_level_data.csv` contains every trial from both test sessions (420 rows: 210 per session), in the order they were run.
Session 1 and Session 2 were run on consecutive days; the device was removed and re-donned, and the EMG electrodes replaced, between sessions.
No personally identifying information is included.

| Column | Meaning |
|---|---|
| `session` | 1 or 2 |
| `trial_in_session` | Run order within the session (1–210), from the randomized protocol |
| `run_order_overall` | Run order across both sessions (1–420) |
| `test_type` | `EMG`, `Bench torque`, `In vivo torque`, or `ROM` |
| `motion` | `Flexion`, `Abduction`, `Horizontal adduction`, or `Fixed at 90 deg` (bench torque) |
| `load_lb` | Hand-held load in lb (EMG: 0, 3, 5; in vivo torque: 5; blank otherwise) |
| `condition` | `Baseline` (device not worn), `Harness-only` (worn, no assistance), `Passive-only` (elastic), `Active-only` (servo), `Active+passive`; blank for ROM |
| `repetition_in_session` | 1–5: which repetition of this test/motion/load/condition within the session |
| `trial_index_1to10` | Repetition across both sessions (Session 1 = 1–5, Session 2 = 6–10) |
| `emg_mean_counts` | Mean of all EMG samples in the 5 s trial window (MyoWare 2.0 envelope, Arduino 10-bit ADC counts; not MVC-normalized) |
| `emg_peak_counts` | Maximum EMG sample in the same window (ADC counts) |
| `torque_nm` | Bench: steady-state stall torque; in vivo: peak torque during the movement (N·m) |
| `pitch_deg`, `roll_deg`, `yaw_deg` | Maximum Euler angle on each axis during the ROM trial (degrees; BNO055 fused output) |
| `battery_v_after_trial` | 2S LiPo voltage read after the trial with a charger's voltage readout (V) |

In addition to the 420 after-trial readings in `battery_v_after_trial`, battery voltage was read once before the first trial of each session: 8.40 V before Session 1 and 7.64 V before Session 2. The battery was not recharged between sessions.

Reproduce every statistic, table, and figure in the paper with:

```
pip install -r Analysis/requirements.txt
python Analysis/analyze.py
```

`Shoulder_Exoskeleton_Data.xlsx` is the original analysis spreadsheet, with its formulas, exported from Google Sheets.
