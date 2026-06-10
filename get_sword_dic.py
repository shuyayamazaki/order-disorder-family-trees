import argparse
import os
from pathlib import Path

import pandas as pd
from pandarallel import pandarallel
from sword import SWORDFamilyMatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate SWORD family dictionaries for a reference dataframe with a 'cif' column."
        )
    )
    parser.add_argument(
        "--input-pkl",
        type=Path,
        required=True,
        help="Path to the preprocessed ICSD reference pickle containing a 'cif' column.",
    )
    parser.add_argument(
        "--output-pkl",
        type=Path,
        default=None,
        help=(
            "Destination pickle. Defaults to the input path with '_SWORD_family_dic' appended."
        ),
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


def resolve_output_path(input_path: Path, output_path: Path | None) -> Path:
    if output_path is not None:
        return output_path
    return input_path.with_name(f"{input_path.stem}_SWORD_family_dic.pkl")


def main():
    args = parse_args()
    initialize_parallelism(args.workers)

    input_pkl = args.input_pkl
    output_pkl = resolve_output_path(input_pkl, args.output_pkl)

    print(f"Loading reference database from {input_pkl}...")
    df_all = pd.read_pickle(input_pkl)

    if args.cif_column not in df_all.columns:
        raise KeyError(f"Column '{args.cif_column}' was not found in {input_pkl}.")

    print("Initializing SWORDFamilyMatcher...")
    matcher = SWORDFamilyMatcher(fill_vacancy=True)

    print("Generating SWORD dictionaries in parallel (this may take a while)...")
    df_all["SWORD_family_dic"] = df_all[args.cif_column].parallel_apply(matcher.get_sword_dic)
    
    print("Extracting SWORD labels...")
    df_all["SWORD_label"] = df_all["SWORD_family_dic"].apply(
        lambda dic: dic.get("child_label", "ERROR") if isinstance(dic, dict) else "ERROR"
    )

    print(f"Saving processed dataframe to {output_pkl}...")
    output_pkl.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_pickle(output_pkl)
    print(f"Successfully saved to {output_pkl}")

if __name__ == "__main__":
    main()