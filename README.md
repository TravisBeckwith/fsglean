# fsglean

[![DOI](https://zenodo.org/badge/1253788057.svg)](https://doi.org/10.5281/zenodo.20452279)

**Tidy, BIDS-aware extraction of FreeSurfer stats files into analysis-ready tabular datasets.**

FreeSurfer ships `aparcstats2table` and `asegstats2table`, but they require you to enumerate subject IDs manually, don't understand BIDS session structure, and produce flat tables that need further wrangling before they're usable in longitudinal mixed-effects models. Every lab ends up writing the same one-off parsing script. `fsglean` replaces that script with a documented, tested, reusable tool.

---

## The problem

After running FreeSurfer (or Infant FreeSurfer, or the dHCP pipeline) on a longitudinal cohort, you have per-subject stats files:

```
derivatives/freesurfer/
  sub-01/ses-V1/stats/lh.aparc.stats
  sub-01/ses-V1/stats/rh.aparc.stats
  sub-01/ses-V1/stats/aseg.stats
  sub-01/ses-V2/stats/lh.aparc.stats
  ...
  sub-87/ses-V3/stats/aseg.stats
```

To get from those files to a table you can actually model, you need to:

1. Find every subject and session directory
2. Parse the `# ColHeaders` line from each file to get column names
3. Handle left and right hemispheres separately but consistently
4. Merge across subjects and sessions with `sub_id` and `ses_id` keys
5. Handle missing files without silent data loss
6. Produce both long format (for `lme4` in R) and wide format (for cross-sectional analyses)
7. Document what every column means

`fsglean` does all of this in one command.

---

## Features

- **BIDS-aware directory traversal** — finds all subjects and sessions automatically; handles both nested (`sub-01/ses-V1/`) and flat (`sub-01_ses-V1/`) layouts
- **Long and wide format output** — long format is ready for `lme4`/`nlme` in R or `statsmodels` in Python; wide format is ready for cross-sectional analyses
- **Auto-generated data dictionary** — one row per variable documenting name, description, units, atlas, and source file
- **Subject-session manifest** — records which files were found, which are missing, and why
- **QC-flag column** — sessions with suspiciously extreme values (>4 SD from cohort mean per metric) are flagged for review; final inclusion decisions remain yours
- **Hemisphere handling** — left and right are kept as separate rows (long) or prefixed columns (`lh_`, `rh_`) (wide); aseg structures labeled `bilateral`
- **Multiple atlases** — supports `aparc.stats` (Desikan-Killiany), `aparc.a2009s.stats` (Destrieux), `aparc.DKTatlas.stats` (DKT), `aseg.stats`, and `wmparc.stats`
- **Infant FreeSurfer compatible** — output format is identical to standard FreeSurfer; no special handling required

---

## Installation

```From source:

git clone https://github.com/TravisBeckwith/fsglean
cd fsglean
pip install -e .
```

**Dependencies:** Python >= 3.9, pandas >= 1.3, click >= 8.0

---

## Quick start

```bash
fsglean /path/to/derivatives/freesurfer/ \
  --stats aparc --stats aseg \
  --metrics ThickAvg --metrics GrayVol --metrics SurfArea --metrics Volume_mm3 \
  --output ./tables/
```

> Repeat multi-value options rather than space-separating values after one
> flag (`--stats aparc --stats aseg`, not `--stats aparc aseg`) — this is
> standard `click` behavior for options that can be given more than once.

This produces five files in `./tables/`:

| File | Contents |
|------|----------|
| `cortical_long.csv` | Long-format cortical stats (aparc) |
| `subcortical_long.csv` | Long-format subcortical volumes (aseg) |
| `merged_wide.csv` | Wide-format merged table, one row per sub-ses |
| `data_dictionary.csv` | Variable documentation |
| `manifest.csv` | Subject-session inventory with missing-file flags |

---

## Supported input files

| File | Atlas | Structure |
|------|-------|-----------|
| `lh.aparc.stats` | Desikan-Killiany | Left hemisphere cortical ROIs |
| `rh.aparc.stats` | Desikan-Killiany | Right hemisphere cortical ROIs |
| `lh.aparc.a2009s.stats` | Destrieux | Left hemisphere cortical ROIs |
| `rh.aparc.a2009s.stats` | Destrieux | Right hemisphere cortical ROIs |
| `lh.aparc.DKTatlas.stats` | DKT | Left hemisphere cortical ROIs |
| `rh.aparc.DKTatlas.stats` | DKT | Right hemisphere cortical ROIs |
| `aseg.stats` | Subcortical segmentation | Bilateral subcortical volumes |
| `wmparc.stats` | White matter parcellation | White matter ROI volumes |

> **Note:** `wmparc.stats` extraction is supported but the metrics table below covers only `aparc.stats` and `aseg.stats`. `wmparc.stats` columns follow the same format as `aseg.stats` (NVoxels, Volume_mm3, normMean, normStd, normMin, normMax, normRange).

---

## Output format examples

### Long format (`cortical_long.csv`)

One row per subject × session × hemisphere × region × metric:

```
sub_id,ses_id,hemi,atlas,region,metric,value,units
sub-01,ses-V1,lh,desikan-killiany,bankssts,ThickAvg,2.571,mm
sub-01,ses-V1,lh,desikan-killiany,bankssts,SurfArea,1088,mm2
sub-01,ses-V1,lh,desikan-killiany,bankssts,GrayVol,3000,mm3
sub-01,ses-V1,rh,desikan-killiany,bankssts,ThickAvg,2.643,mm
sub-01,ses-V2,lh,desikan-killiany,bankssts,ThickAvg,2.489,mm
```

Load directly into `lme4`:

```r
library(tidyverse)
library(lme4)

df <- read_csv("cortical_long.csv") |>
  filter(atlas == "desikan-killiany", metric == "ThickAvg") |>
  left_join(demographics, by = c("sub_id", "ses_id"))

model <- lmer(value ~ age_at_scan * group + (1 + age_at_scan | sub_id),
              data = df)
```

### Long format (`subcortical_long.csv`)

One row per subject × session × structure × metric:

```
sub_id,ses_id,hemi,atlas,region,metric,value,units
sub-01,ses-V1,bilateral,aseg,Left-Hippocampus,Volume_mm3,4128.5,mm3
sub-01,ses-V1,bilateral,aseg,Right-Hippocampus,Volume_mm3,4052.1,mm3
sub-01,ses-V1,bilateral,aseg,Left-Amygdala,Volume_mm3,1643.2,mm3
```

### Wide format (`merged_wide.csv`)

One row per subject × session, all regions as columns. Structure names are sanitized for R and Python compatibility: hyphens are replaced with underscores (e.g., `Left-Hippocampus` → `Left_Hippocampus`):

```
sub_id,ses_id,lh_bankssts_ThickAvg,lh_bankssts_SurfArea,rh_bankssts_ThickAvg,...,Left_Hippocampus_Volume_mm3,...
sub-01,ses-V1,2.571,1088,2.643,...,4128.5,...
sub-01,ses-V2,2.489,1071,2.601,...,4089.3,...
```

### Data dictionary (`data_dictionary.csv`)

Descriptions are generated from the metric definition plus the raw
FreeSurfer structure code — `fsglean` doesn't ship a hand-curated anatomical
name lookup table (e.g. translating `bankssts` to "banks of the superior
temporal sulcus"), so it doesn't fabricate anatomical prose it can't verify:

```
column_name,description,units,atlas,source_file,freesurfer_metric
lh_bankssts_ThickAvg,Mean cortical thickness for left hemisphere region 'bankssts' (desikan-killiany atlas),mm,desikan-killiany,lh.aparc.stats,ThickAvg
lh_bankssts_SurfArea,Surface area for left hemisphere region 'bankssts' (desikan-killiany atlas),mm2,desikan-killiany,lh.aparc.stats,SurfArea
Left_Hippocampus_Volume_mm3,Volume of the structure for structure 'Left-Hippocampus' (aseg),mm3,aseg,aseg.stats,Volume_mm3
```

### Manifest (`manifest.csv`)

```
sub_id,ses_id,lh_aparc_found,rh_aparc_found,aseg_found,notes,qc_flag_metrics,qc_flag
sub-01,ses-V1,True,True,True,,,False
sub-01,ses-V2,True,True,False,aseg.stats missing,,False
sub-03,ses-V1,True,False,True,rh.aparc.stats missing,,False
```

`qc_flag` is True when any variable for that sub-ses was more than
`--qc-threshold` standard deviations from the cohort mean; `qc_flag_metrics`
lists which ones.

---

## FreeSurfer stats file metrics

### aparc.stats (cortical, per hemisphere)

| Metric | Description | Units |
|--------|-------------|-------|
| `NumVert` | Number of vertices in the ROI | vertices |
| `SurfArea` | Surface area | mm² |
| `GrayVol` | Gray matter volume | mm³ |
| `ThickAvg` | Mean cortical thickness | mm |
| `ThickStd` | Standard deviation of cortical thickness | mm |
| `MeanCurv` | Mean curvature | mm⁻¹ |
| `GausCurv` | Gaussian curvature | mm⁻² |
| `FoldInd` | Folding index | unitless |
| `CurvInd` | Intrinsic curvature index | unitless |

### aseg.stats (subcortical segmentation)

| Metric | Description | Units |
|--------|-------------|-------|
| `NVoxels` | Number of voxels in the structure | voxels |
| `Volume_mm3` | Volume of the structure | mm³ |
| `normMean` | Mean intensity of normalized volume | unitless |
| `normStd` | Standard deviation of intensity | unitless |
| `normMin` | Minimum intensity | unitless |
| `normMax` | Maximum intensity | unitless |

---

## CLI reference

```
Usage: fsglean [OPTIONS] DERIVATIVES_DIR

  Extract FreeSurfer stats files from a BIDS derivatives directory into tidy
  tabular datasets.

  DERIVATIVES_DIR is the path to the FreeSurfer BIDS derivatives directory.

Options:
  --stats [aparc|aparc.DKTatlas|aparc.a2009s|aseg|wmparc]
                                  Stats files to extract. Repeat for multiple,
                                  e.g. --stats aparc --stats aseg.  [default:
                                  aparc, aseg]
  --metrics TEXT                  Restrict to these metrics (e.g. --metrics
                                  ThickAvg --metrics GrayVol). Default: all
                                  metrics for the requested stats.
  --subjects TEXT                 Restrict to these subject IDs (e.g.
                                  --subjects sub-01 --subjects sub-02).
                                  Default: all discovered subjects.
  --sessions TEXT                 Restrict to these session IDs (e.g.
                                  --sessions ses-V1). Default: all discovered
                                  sessions.
  --output DIRECTORY              Output directory. Created if it does not
                                  exist.  [default: ./fsglean_output/]
  --format [long|wide|both]       Output format.  [default: both]
  --no-dict                       Skip data dictionary generation.
  --no-manifest                   Skip manifest generation.
  --qc-threshold FLOAT            Flag values more than N standard deviations
                                  from the cohort mean. Set to 0 to disable.
                                  [default: 4.0]
  --no-session-fallback           Leave ses_id empty for cross-sectional
                                  subjects instead of defaulting to ses-01.
  --help                          Show this message and exit.
```

---

## Python API

```python
from fsglean import FSGlean

extractor = FSGlean(
    derivatives_dir="/path/to/derivatives/freesurfer/",
    stats=["aparc", "aseg"],
    metrics=["ThickAvg", "GrayVol", "Volume_mm3"],
)

long_df = extractor.to_long()
wide_df = extractor.to_wide()
dictionary = extractor.data_dictionary()
manifest = extractor.manifest()

long_df.to_csv("cortical_long.csv", index=False)
```

---

## BIDS directory layout

`fsglean` expects FreeSurfer output organized under a BIDS derivatives root. Both nested and flat session layouts are supported:

**Nested (preferred):**
```
derivatives/freesurfer/
  sub-01/
    ses-V1/
      stats/
        lh.aparc.stats
        rh.aparc.stats
        aseg.stats
    ses-V2/
      stats/
        ...
  sub-02/
    ...
```

**Flat (also supported):**
```
derivatives/freesurfer/
  sub-01_ses-V1/
    stats/
      lh.aparc.stats
      ...
  sub-01_ses-V2/
    ...
```

**Cross-sectional (no session level):**
```
derivatives/freesurfer/
  sub-01/
    stats/
      lh.aparc.stats
      ...
```

In the cross-sectional case, `ses_id` is set to `ses-01` in all output tables. If you prefer `NA`, pass `--no-session-fallback` and the column will be empty.

---

## Notes on Infant FreeSurfer and the dHCP pipeline

The stats file format produced by [Infant FreeSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/infantFS) and the [dHCP structural pipeline](https://github.com/BioMedIA/dhcp-structural-pipeline) is identical to standard FreeSurfer. `fsglean` parses these outputs without modification.

One practical note for infant data: cortical thickness, surface area, and subcortical volumes change rapidly across the first two years of life. When modeling these trajectories, age at scan (in days or weeks post-menstrual age for preterm infants) is a more appropriate time variable than session label. The manifest output includes `ses_id` but does not attempt to extract age — that should come from your participants.tsv or REDCap export and be merged on `sub_id` × `ses_id` keys.

---

## Comparison with existing tools

| Feature | `aparcstats2table` | `asegstats2table` | `fsglean` |
|---------|-------------------|------------------|-------------|
| BIDS directory traversal | ✗ | ✗ | ✓ |
| Longitudinal session handling | ✗ | ✗ | ✓ |
| Long format output | ✗ | ✗ | ✓ |
| Wide format output | ✓ (limited) | ✓ (limited) | ✓ |
| Data dictionary | ✗ | ✗ | ✓ |
| Subject-session manifest | ✗ | ✗ | ✓ |
| Missing file handling | ✗ | ✗ | ✓ |
| Python API | ✗ | ✗ | ✓ |
| Multi-atlas in one call | ✗ | ✗ | ✓ |

---

## Roadmap

`fsglean` is the first module in a planned suite of infant neuroimaging output extractors. Upcoming modules follow the same design: BIDS-aware input, tidy output, auto-generated data dictionaries.

- **v0.2** — MRIQC output extractor (`group_T1w.tsv`, `group_bold.tsv`, individual JSON IQMs)
- **v0.3** — QSIRecon/NODDI extractor (NDI, ODI, FWF, FA, MD per bundle; tract profiles; infant diffusivity parameter logging)
- **v0.4** — NiBabies/xcp-d functional connectivity extractor (connectivity matrices using Myers-Labonte, Gordon, and Glasser parcellations; QC summaries from confounds TSV)
- **v0.5** — DESPOT/QUIT quantitative MRI extractor (T1, T2, myelin water fraction per atlas ROI)
- **v1.0** — Unified CLI that orchestrates all modules and merges outputs into a single analysis-ready dataset

---

## Contributing

Contributions welcome. Please open an issue before submitting a pull request for new features. Bug reports with a minimal reproducible example are especially helpful.

```bash
git clone https://github.com/TravisBeckwith/fsglean
cd fsglean
pip install -e ".[dev]"
pytest tests/
```

---

## License

MIT
