# Order-(Dis)Order Family Tree Benchmark

This repository provides the small, reproducible Python entrypoints used in the paper:

> Yamazaki, Shuya, Huang, Yuyao, Petersen, Martin Hoffmann, Nong, Wei, and Hippalgaonkar, Kedar. *Navigating Order-(Dis)Order Family Trees via Group-Subgroup Transitions*.
> [arXiv:2604.21386](https://arxiv.org/abs/2604.21386)

The code is built on [SWORDlib](https://github.com/YuyaoHuang330/SWORD), which should be installed from PyPI with `pip install SWORDlib`.

## What this repo does

1. Prepare an ICSD-based reference table with SWORD family dictionaries.
2. Benchmark generated structures against that ICSD reference.
3. Report two family-tree metrics:
   - `FT_disorder`: asks whether an ordered prediction is just one possible ordering of a known disordered parent phase.
   - `FT_order`: asks whether an ordered prediction is a structural sibling of a known ordered crystal, i.e. whether it can be interpreted as a rearrangement or exchange of local motifs within a shared parent lattice.

## Installation

Create a Python 3.10+ environment and install the dependencies:

```bash
pip install -r requirements.txt
```

SWORDlib is imported as:

```python
from sword import SWORDFamilyMatcher
```

## Data preparation

ICSD data is not distributed in this repository because of licensing constraints.

1. Follow the ICSD preprocessing workflow described in the SWORD repository.
2. Produce a pickle file containing the preprocessed ICSD reference and a `cif` column with CIF strings.
3. Run `get_sword_dic.py` to compute the ICSD reference-side SWORD family dictionary.

Example:

```bash
python get_sword_dic.py \
  --input-pkl /path/to/ICSD_reference_preprocessed.pkl \
  --output-pkl /path/to/ICSD_reference_SWORD_family_dic.pkl
```

The output will include a `SWORD_family_dic` column and a compact `SWORD_label` column.

## Benchmarking generated structures

Prepare each generated-structure dataframe as a pickle file with a `cif` column containing CIF strings.

Run the benchmark against the precomputed ICSD reference:

```bash
python family_tree_bench.py \
  --reference-pkl /path/to/ICSD_reference_SWORD_family_dic.pkl \
  --query-pkl /path/to/generated_structures.pkl \
  --output-dir /path/to/output_dir
```

You can pass multiple query pickle files to `--query-pkl`.

Each output pickle includes:

- `SWORD_family_dic`
- `SWORD_label`
- `has_ordered_icsd_family`
- `has_disordered_icsd_family`

The script prints file-level summaries for `FT_order`, `FT_disorder`, and error rate.

## Citation

If you use this repository, please cite the paper below:

```bibtex
@article{yamazaki2026orderdisorder,
  title = {Navigating Order-(Dis)Order Family Trees via Group-Subgroup Transitions},
  author = {Yamazaki, Shuya and Huang, Yuyao and Petersen, Martin Hoffmann and Nong, Wei and Hippalgaonkar, Kedar},
  journal = {arXiv preprint arXiv:2604.21386},
  year = {2026},
  url = {https://arxiv.org/abs/2604.21386},
  doi = {10.48550/arXiv.2604.21386}
}
```

If you use SWORDlib directly, please also cite the SWORDlib paper described in the upstream repository.