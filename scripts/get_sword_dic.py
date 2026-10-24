"""Build SWORD family dictionaries for an ICSD-style reference dataframe."""

import argparse
import os
from pathlib import Path

import pandas as pd
from pandarallel import pandarallel
from sword import SWORDFamilyMatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate SWORD family dictionaries for a reference dataframe with a CIF column."
        )
    )
    parser.add_argument(
        "--input-pkl",
        type=Path,
        required=True,
        help="Preprocessed reference pickle containing the CIF column (for example, 'cif').",
    )
    parser.add_argument(
        "--output-pkl",
        type=Path,
        default=None,
        help="Destination pickle. Defaults to INPUT_STEM_SWORD_family_dic.pkl beside the input.",
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
        help="Allow replacing an existing output pickle.",
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


def resolve_output_path(input_path: Path, output_path: Path | None) -> Path:
    if output_path is not None:
        return output_path
    return input_path.with_name(f"{input_path.stem}_SWORD_family_dic.pkl")


def validate_paths(input_path: Path, output_path: Path, overwrite: bool) -> None:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input pickle does not exist or is not a file: {input_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output pickles must be different paths.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {output_path}. Use --overwrite to replace it deliberately."
        )


def main() -> None:
    args = parse_args()
    input_pkl = args.input_pkl
    output_pkl = resolve_output_path(input_pkl, args.output_pkl)
    validate_paths(input_pkl, output_pkl, args.overwrite)
    initialize_parallelism(args.workers)

    print(f"Loading reference dataframe from {input_pkl}...")
    reference_df = pd.read_pickle(input_pkl)
    if args.cif_column not in reference_df.columns:
        raise KeyError(f"Column '{args.cif_column}' was not found in {input_pkl}.")

    print("Initializing SWORDFamilyMatcher (fill_vacancy=True)...")
    matcher = SWORDFamilyMatcher(fill_vacancy=True)
    print("Generating SWORD family dictionaries in parallel; this may take a while...")
    reference_df["SWORD_family_dic"] = reference_df[args.cif_column].parallel_apply(
        matcher.get_sword_dic
    )
    reference_df["SWORD_label"] = reference_df["SWORD_family_dic"].apply(
        lambda family: family.get("child_label", "ERROR")
        if isinstance(family, dict)
        else "ERROR"
    )

    output_pkl.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving {len(reference_df)} processed reference rows to {output_pkl}...")
    reference_df.to_pickle(output_pkl)
    print(f"SUCCESS: wrote {output_pkl}")


if __name__ == "__main__":
    main()
