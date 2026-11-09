# MagTouch Sparse Localization

Research companion for **From Five to Three: Spatial Sampling and Training Supervision for Magnetic Tactile Localization**.

- English manuscript: [PDF](paper/Sparse_Magnetic_Sensors_EN.pdf) · [Word](paper/Sparse_Magnetic_Sensors_EN.docx) · [source](paper/Sparse_Magnetic_Sensors_EN.md)
- 中文稿：[PDF](paper/Sparse_Magnetic_Sensors_ZH.pdf) · [Word](paper/Sparse_Magnetic_Sensors_ZH.docx) · [源稿](paper/Sparse_Magnetic_Sensors_ZH.md)
- [中文说明](README.zh.md) · [Protocol and data dictionary](docs/protocol.md)

## What the comparison measures

The original five-node CSML localizer remains frozen. The fixed 1500-epoch comparison separates reducing online input from removing supervision at omitted nodes. At common five-node supervision, reducing the input to S2/S3/S5 increased domain-balanced raw mean error by 0.060 mm and sequence P95 by 0.236 mm. Three-node-only supervision instead yielded false-contact declarations on all nominal lifts across the three trained seeds. Layout screening with measured retained nodes and reconstructed omitted nodes is reported separately from fully reconstructed replay.

## Five-node reference repositories

| Source | Role here |
| --- | --- |
| [MagTouch-CSML, frozen snapshot](https://github.com/googo2025/MagTouch-CSML/tree/02cd40217672b43e0860c9a902ea8b4f77f922ca) | Five-node localization, shared inference weights, normalization and scoring protocol. The [published shared weights](https://github.com/googo2025/MagTouch-CSML/blob/02cd40217672b43e0860c9a902ea8b4f77f922ca/models/shared_provenance.json) match the SHA-256 recorded in this replay. |
| [Five-node shared field](https://github.com/googo2025/magtouch-temporal-state-reconstruction/tree/ca291d4d5324ca4b0fd42658022761cd6cfb9602/methods/shared_field) | Five-node magnetic field reconstruction and the epoch-529 engineering reference. |
| [Original apparatus](https://github.com/googo2025/MagTouch-RA-3d-trajectory-recon/tree/acb12b054abb75be53636fc5f2b4496c61de149c) | Five triaxial Hall nodes, magnet array and acquisition setup. |

## Reproduce the results

Run from the repository root with Python 3.10 or later:

```bash
python -m pip install -r requirements.txt
python scripts/reproduce.py --output reproduced
python scripts/figures.py --output reproduced --lang EN
```

Use `--lang both` with Microsoft YaHei or Noto Sans CJK SC installed to render both languages. The numerical script verifies all four contrasts against the packaged manuscript results. The plotting script regenerates all six figure families using the packaged data. Font and rendering versions can affect image pixels. The final manuscript figures are included alongside the paper source.

The package reproduces the **reported statistical analysis and figures from saved scores**. Its analysis data cover 970 replay-score rows (10 variants × 97 sequences), 14 field-layout rows and 947 saved TRAIN/DEV snapshots. Raw magnetic frames, private sensor logs, the nine training checkpoints and complete historical screening records are retained in the project archive. Training and raw-signal replay require those upstream inputs. See the data dictionary for scope and metrics.
