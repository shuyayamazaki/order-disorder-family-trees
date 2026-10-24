"""Benchmark query structures against a precomputed ICSD SWORD family reference."""

import argparse
import os
from pathlib import Path

import pandas as pd
from pandarallel import pandarallel
from sword import SWORDFamilyMatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark query structures against a precomputed ICSD SWORD family reference."
    )
    parser.add_argument(
        "--reference-pkl",
        type=Path,
        required=True,
        help="Reference pickle containing a SWORD_family_dic column.",
    )
    parser.add_argument(
        "--query-pkl",
        type=Path,
        nargs="+",
        required=True,
        help="One or more query pickles containing the CIF column and generated structures.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where benchmark result pickles will be written.",
    )
    parser.add_argument(
        "--cif-column",
        default="cif",
        help="Name of the dataframe column containing CIF strings (default: %(default)s).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="pandarallel worker count. Defaults to the NP environment variable or 1.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing result pickles.",
    )
    return parser.parse_args()


def resolve_workers(workers: int | None) -> int:
    resolved_workers = workers if workers is not None else int(os.environ.get("NP", "1"))
    if resolved_workers < 1:
        raise ValueError("Worker count must be at least 1. Set --workers or NP accordingly.")
    return resolved_workers


def initialize_parallelism(workers: int | None) -> None:
    resolved_workers = resolve_workers(workers)
    print(f"Initializing pandarallel with {resolved_workers} worker(s)...")
    pandarallel.initialize(nb_workers=resolved_workers, progress_bar=True)


def output_path_for(query_pkl: Path, output_dir: Path) -> Path:
    return output_dir / f"{query_pkl.stem}_SWORD_family_dic.pkl"


def validate_inputs(args: argparse.Namespace) -> None:
    if not args.reference_pkl.is_file():
        raise FileNotFoundError(
            f"Reference pickle does not exist or is not a file: {args.reference_pkl}"
        )
    duplicate_stems = {
        query_pkl.stem for query_pkl in args.query_pkl if sum(
            candidate.stem == query_pkl.stem for candidate in args.query_pkl
        ) > 1
    }
    if duplicate_stems:
        raise ValueError(
            "Query pickles must have unique filenames because output names are stem-based: "
            f"{', '.join(sorted(duplicate_stems))}"
        )
    for query_pkl in args.query_pkl:
        if not query_pkl.is_file():
            raise FileNotFoundError(f"Query pickle does not exist or is not a file: {query_pkl}")
        output_pkl = output_path_for(query_pkl, args.output_dir)
        if output_pkl.exists() and not args.overwrite:
            raise FileExistsError(
                f"Output already exists: {output_pkl}. Use --overwrite to replace it deliberately."
            )


def family_label(family: object) -> str:
    return family.get("child_label", "ERROR") if isinstance(family, dict) else "ERROR"


def has_family_match(family: object, match_key: str) -> int:
    return int(bool(family.get(match_key, []))) if isinstance(family, dict) else 0


def main() -> None:
    args = parse_args()
    validate_inputs(args)
    initialize_parallelism(args.workers)

    print(f"Loading reference dataframe from {args.reference_pkl}...")
    reference_df = pd.read_pickle(args.reference_pkl)
    if "SWORD_family_dic" not in reference_df.columns:
        raise KeyError(
            f"Column 'SWORD_family_dic' was not found in {args.reference_pkl}. "
            "Run scripts/get_sword_dic.py first."
        )

    print("Initializing SWORDFamilyMatcher (fill_vacancy=True)...")
    matcher = SWORDFamilyMatcher(fill_vacancy=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"Files scheduled for processing: {[str(path) for path in args.query_pkl]}")
    print("=" * 60)

    for query_pkl in args.query_pkl:
        print("\n" + "-" * 60)
        print(f"Processing: {query_pkl}")
        print("-" * 60)
        query_df = pd.read_pickle(query_pkl)
        if args.cif_column not in query_df.columns:
            raise KeyError(f"Column '{args.cif_column}' was not found in {query_pkl}.")

        print("Matching query structures against the reference dataframe in parallel...")
        query_df["SWORD_family_dic"] = query_df[args.cif_column].parallel_apply(
            lambda cif: matcher.fit_many(cif, reference_df)
        )
        query_df["SWORD_label"] = query_df["SWORD_family_dic"].apply(family_label)
        query_df["has_ordered_icsd_family"] = query_df["SWORD_family_dic"].apply(
            has_family_match, args=("matched_ordered_ids",)
        )
        query_df["has_disordered_icsd_family"] = query_df["SWORD_family_dic"].apply(
            has_family_match, args=("matched_disordered_ids",)
        )

        total = len(query_df)
        error_count = (query_df["SWORD_label"] == "ERROR").sum()
        ordered_count = query_df["has_ordered_icsd_family"].sum()
        disordered_count = query_df["has_disordered_icsd_family"].sum()
        ft_order = ordered_count / total if total else float("nan")
        ft_disorder = disordered_count / total if total else float("nan")
        error_fraction = error_count / total if total else float("nan")

        print("\n" + "=" * 60)
        print(f"Summary statistics for: {query_pkl.name}")
        print("=" * 60)
        print(f"total       : {total}")
        print(
            f"errors      : {error_count} / {total} = "
            f"{error_fraction:.3f} ({error_fraction:.1%})"
        )
        print(f"FT_order    : {ordered_count} / {total} = {ft_order:.3f} ({ft_order:.1%})")
        print(f"FT_disorder : {disordered_count} / {total} = {ft_disorder:.3f} ({ft_disorder:.1%})")
        print("=" * 60)

        output_pkl = output_path_for(query_pkl, args.output_dir)
        print(f"Saving {total} benchmark rows to {output_pkl}...")
        query_df.to_pickle(output_pkl)
        print(f"SUCCESS: wrote {output_pkl}")

    print("\nAll scheduled files were processed successfully.")


if __name__ == "__main__":
    main()
