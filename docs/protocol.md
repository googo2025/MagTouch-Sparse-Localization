# Protocol and data dictionary

## Fixed scientific scope

- Reconstruction: 381 complete training sequences, 101 development sequences, 277,348 development frames and 3,916,620 valid magnetic components. Historical layouts select the lowest saved development loss over epochs 1–1500 (1–1000 for independently retrained S5). The historical localization screen used a hybrid input and selected S2/S3/S5. Only its selected candidate summary is in this package.
- Paired experiment: seeds 101, 202, 303. A uses S1–S5 as input and target. B uses S2/S3/S5 as input and S1–S5 as target. C uses S2/S3/S5 as input and target. All nine used the same 11,939-parameter recurrent field model, fixed physical readout, validity masks, 100 µT field scaling, matched within-seed initialization and sequence order. AdamW used betas (0.9, 0.999), eps 1e-8 and weight decay 0. Each complete sequence contributes one update, for 571,500 updates per run. Cosine learning rate is 3e-6 + 0.5 × (3e-4 − 3e-6) × [1 + cos(π × (epoch − 1) / 1499)]. The paper uses the fixed epoch-1500 checkpoint. Later training is outside this release.
- Frozen localization: A/B/C use all five reconstructed fields. M uses all five measured fields. The locator, normalization, native timing and reset flags, reference masks and acceptance rules are fixed. All ten variants were scored on the same 97 complete seen-indenter development sequences and 132,595 eligible position targets. The three localization domains are rounded (15), hemispherical (52) and small flat (30). There are 91,863 separate nominal lifted frames. Replay makes zero optimizer updates.
- Statistics: per-sequence raw errors use all eligible position targets, and position summary metrics weight sequences equally within each domain and domains equally. P95 is computed per sequence first. Contact misses and false contacts use frame counts on their fixed denominators. For A/B/C, seed metrics are averaged equally. Paired bootstrap estimates use 10,000 draws of complete sequences within each domain, with the three trained seeds held fixed (RNG seed 20261109). These are conditional descriptive intervals.

## Files

| File | Contents |
| --- | --- |
| `localization_sequence_scores.csv` | 970 de-identified rows. The same `sequence` code refers to the same experimental sequence across variants. The key is (`variant`, `sequence`). |
| `field_layout_scores.csv` | Pooled raw magnetic RMSE and absolute-error P95 in µT for all 13 reduced configurations and the original five-node field reference. The reference is stored at published precision. |
| `layout_screen_candidate.json` | Selected historical three-node candidate and hybrid localization scores. Coverage is a fraction. |
| `seed202_node_rmse.csv` | Pooled valid-component magnetic RMSE at each node for seed 202. |
| `sensor_coordinates_mm.csv` | Five sensor center coordinates in the registered frame. |
| `training_dev_samples.csv` | 947 observed complete epochs across six B/C runs. TRAIN and DEV are common S235 normalized MSE. The series contains gaps and includes epoch 1 and epoch 1500 for each run. |
| `expected_paired_effects.json` | Expected statistical results checked by the numerical reproduction script. |
| `source_provenance.json` | SHA-256 fingerprints of the source score receipts, field summary, historical screen and frozen weights. The receipt names and private paths are omitted. |

`coverage` is the accepted fraction. `good_fraction` is the fraction within 0.5 mm of the nominal reference, including rejected outputs. The joint accepted-and-accurate fraction is computed as coverage minus bad_accepted_fraction. `bad_accepted_fraction` is the fraction accepted with an error above 0.5 mm. All three use all eligible position targets as denominator. `aligned_mean_mm` removes one sequence-wide constant XYZ offset for diagnosis. The primary result uses raw coordinates. Contact output and coordinate acceptance are distinct.

Absolute results JSON array order: raw mean mm, sequence P95 mm, coverage %, constant-offset diagnostic mean mm, accepted with error >0.5 mm %, accepted with error ≤0.5 mm %, missed contacts %, false contacts %, count missed, count false contacts. Contrast arrays use the first six fields in the same order, with differences in percentage points for percentage fields.

The two matched-trajectory figure families use the native saved prediction arrays. The receipt documents deterministic display selection, masks and paired errors. The packaged scalar scores reproduce the statistics and six scalar-derived figure families. Regenerating trajectories requires the saved native arrays in the original project archive.
