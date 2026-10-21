# Order-Disorder Family Tree Benchmark

Reference implementation for **“Navigating Order-Disorder Family Trees via Group-Subgroup Transitions.”**

> Yamazaki, Shuya; Huang, Yuyao; Petersen, Martin Hoffmann; Nong, Wei; and
> Hippalgaonkar, Kedar. *Navigating Order-Disorder Family Trees via Group-Subgroup
> Transitions.* [arXiv:2604.21386](https://arxiv.org/abs/2604.21386).

This repository uses [SWORDlib](https://github.com/YuyaoHuang330/SWORD) to attach
SWORD family-tree labels to crystal structures and to benchmark generated structures
against an ICSD-derived reference set.

## Scope

The workflow has two explicit stages:

1. **Reference preparation**: calculate a SWORD family dictionary and child label for
every structure in a preprocessed ICSD reference dataframe.
2. **Benchmarking**: match each query structure to that reference and report whether
its family contains known ordered and/or disordered ICSD members.

The scripts do not distribute ICSD data, infer experimental existence, calculate
thermodynamic stability, or relax structures. ICSD-derived inputs must be obtained and
used in accordance with the applicable license.

## Installation

```bash
uv sync --python 3.11
```

## Input data contract

> **Security note:** pandas pickle files are executable serialization formats. Only
> read pickle files from trusted sources.

### Reference dataframe

`get_sword_dic.py` accepts a pandas pickle containing one row per reference structure
and a CIF-string column named `cif` by default. Use `--cif-column` if your column has
a different name. The script writes the original dataframe plus:

- `SWORD_family_dic`: full dictionary returned by SWORDlib;
- `SWORD_label`: compact child label extracted from that dictionary, or `ERROR` when
  SWORDlib did not return a dictionary.

### Query dataframe

`family_tree_bench.py` accepts one or more pandas pickles, each with the same
CIF-string column. Stable input identifiers and other metadata are retained unchanged.
The reference dataframe must already contain `SWORD_family_dic`.

For reproducible runs, preserve the exact input pickle files, their hashes, the command
line, Python version, and `uv.lock` alongside every result.

## Run the workflow

### 1. Build the reference family dictionary

Prepare an ICSD dataframe according to the upstream
[SWORD preprocessing workflow](https://github.com/YuyaoHuang330/SWORD), then run:

```bash
python get_sword_dic.py \
  --input-pkl /path/to/ICSD_reference_preprocessed.pkl \
  --output-pkl /path/to/ICSD_reference_SWORD_family_dic.pkl \
  --workers 1
```

The default output path is
`<input-stem>_SWORD_family_dic.pkl` next to the input. Existing outputs are protected
from accidental replacement; pass `--overwrite` only when replacement is intentional.

### 2. Benchmark generated structures

```bash
python family_tree_bench.py \
  --reference-pkl /path/to/ICSD_reference_SWORD_family_dic.pkl \
  --query-pkl /path/to/generated_structures.pkl \
  --output-dir /path/to/family_tree_results \
  --workers 1
```

Multiple query files can be benchmarked in one call:

```bash
python family_tree_bench.py \
  --reference-pkl /path/to/ICSD_reference_SWORD_family_dic.pkl \
  --query-pkl /path/to/run_a.pkl /path/to/run_b.pkl \
  --output-dir /path/to/family_tree_results \
  --workers 4
```

Each query result is written as
`<query-stem>_SWORD_family_dic.pkl`. Query filenames must have unique stems so output
names cannot collide. Existing result files require `--overwrite` to be replaced.

`--workers` controls `pandarallel`; if it is omitted, the scripts use `NP` from the
environment or fall back to one worker. Use one worker for the most conservative,
easiest-to-reproduce execution.

## Output fields and benchmark metrics

Each result pickle preserves every query column and adds:

- `SWORD_family_dic`: SWORDlib matching result for the query structure;
- `SWORD_label`: query child label, or `ERROR` if the matcher returned no dictionary;
- `has_ordered_icsd_family`: `1` when `matched_ordered_ids` is non-empty, otherwise `0`;
- `has_disordered_icsd_family`: `1` when `matched_disordered_ids` is non-empty,
  otherwise `0`.

For each query file, the command prints:

- **FT_order**: fraction of all query rows with `has_ordered_icsd_family == 1`;
- **FT_disorder**: fraction of all query rows with `has_disordered_icsd_family == 1`;
- **error rate**: fraction of rows whose `SWORD_label` is `ERROR`.

These are reference-coverage metrics under the chosen ICSD preprocessing and SWORDlib
version.

## Citation

If you use this repository, please cite:

```bibtex
@article{yamazaki2026orderdisorder,
  title = {Navigating Order-Disorder Family Trees via Group-Subgroup Transitions},
  author = {Yamazaki, Shuya and Huang, Yuyao and Petersen, Martin Hoffmann and Nong, Wei and Hippalgaonkar, Kedar},
  journal = {arXiv preprint arXiv:2604.21386},
  year = {2026},
  url = {https://arxiv.org/abs/2604.21386},
  doi = {10.48550/arXiv.2604.21386}
}
```

If you use SWORDlib directly, also cite the SWORDlib paper specified by the upstream
project.
