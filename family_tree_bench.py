import argparse
import os
from pathlib import Path

import pandas as pd
from pandarallel import pandarallel
from sword import SWORDFamilyMatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark ordered query structures against a precomputed ICSD SWORD family reference."
        )
    )
    parser.add_argument(
        "--reference-pkl",
        type=Path,
        required=True,
        help="Path to the ICSD reference pickle containing a 'SWORD_family_dic' column.",
    )
    parser.add_argument(
        "--query-pkl",
        type=Path,
        nargs="+",
        required=True,
        help="One or more pickle files with a 'cif' column and generated structures to benchmark.",
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
        help="Name of the dataframe column containing CIF strings.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of pandarallel workers. Defaults to the NP environment variable or 1.",
    )
    return parser.parse_args()


def initialize_parallelism(workers: int | None) -> None:
    resolved_workers = workers if workers is not None else int(os.environ.get("NP", 1))
    print(f"Initializing pandarallel with {resolved_workers} workers...")
    pandarallel.initialize(nb_workers=resolved_workers, progress_bar=True)


def main():
    args = parse_args()
    initialize_parallelism(args.workers)

    reference_pkl = args.reference_pkl
    output_dir = args.output_dir

    print(f"Loading reference database from {reference_pkl}...")
    ref_df = pd.read_pickle(reference_pkl)

    if "SWORD_family_dic" not in ref_df.columns:
        raise KeyError(
            f"Column 'SWORD_family_dic' was not found in {reference_pkl}. Run get_sword_dic.py first."
        )

    print("Initializing SWORDFamilyMatcher...")
    matcher = SWORDFamilyMatcher(fill_vacancy=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"Files scheduled for processing: {[str(path) for path in args.query_pkl]}")
    print("=" * 60)

    for query_pkl in args.query_pkl:
        print("\n" + "-" * 60)
        print(f"Starting processing for: {query_pkl}")
        print("-" * 60)

        query_df = pd.read_pickle(query_pkl)

        if args.cif_column not in query_df.columns:
            raise KeyError(f"Column '{args.cif_column}' was not found in {query_pkl}.")

        print("Matching query structures against the reference database in parallel...")
        query_df["SWORD_family_dic"] = query_df[args.cif_column].parallel_apply(
            lambda cif: matcher.fit_many(cif, ref_df)
        )

        print("Extracting SWORD labels and family flags...")
        query_df["SWORD_label"] = query_df["SWORD_family_dic"].apply(
            lambda dic: dic.get("child_label", "ERROR") if isinstance(dic, dict) else "ERROR"
        )
        query_df["has_ordered_icsd_family"] = query_df["SWORD_family_dic"].apply(
            lambda dic: int(bool(dic.get("matched_ordered_ids", []))) if isinstance(dic, dict) else 0
        )
        query_df["has_disordered_icsd_family"] = query_df["SWORD_family_dic"].apply(
            lambda dic: int(bool(dic.get("matched_disordered_ids", []))) if isinstance(dic, dict) else 0
        )

        total = len(query_df)
        error_count = (query_df["SWORD_label"] == "ERROR").sum()
        ordered_count = query_df["has_ordered_icsd_family"].fillna(0).astype(int).sum()
        disordered_count = query_df["has_disordered_icsd_family"].fillna(0).astype(int).sum()

        ft_order = ordered_count / total if total > 0 else float("nan")
        ft_disorder = disordered_count / total if total > 0 else float("nan")
        error_frac = error_count / total if total > 0 else float("nan")

        print("\n" + "=" * 60)
        print(f"Summary statistics for: {query_pkl.name}")
        print("=" * 60)
        print(f"total       : {total}")
        print(f"errors      : {error_count} / {total} = {error_frac:.3f} ({error_frac:.1%})")
        print(f"FT_order    : {ordered_count} / {total} = {ft_order:.3f} ({ft_order:.1%})")
        print(f"FT_disorder : {disordered_count} / {total} = {ft_disorder:.3f} ({ft_disorder:.1%})")
        print("=" * 60)

        output_pkl = output_dir / f"{query_pkl.stem}_SWORD_family_dic.pkl"
        print(f"\nSaving match results to {output_pkl}...")
        query_df.to_pickle(output_pkl)
        print(f"SUCCESS: Finished processing and saved {query_pkl.name} to {output_pkl}")

    print("\n" + "=" * 60)
    print("All scheduled files have been successfully processed!")
    print("=" * 60)


if __name__ == "__main__":
    main()