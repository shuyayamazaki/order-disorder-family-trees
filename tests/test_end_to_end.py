"""End-to-end smoke coverage for the published command-line workflow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
from pymatgen.core import Lattice, Structure

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def test_reference_preparation_and_benchmark_round_trip(tmp_path: Path) -> None:
    """Both CLIs process a minimal Cu-Au mixed-occupancy structure end to end."""
    structure = Structure(
        Lattice.cubic(3.75),
        [{"Cu": 0.5, "Au": 0.5}],
        [[0, 0, 0]],
    )
    cif = structure.to(fmt="cif")
    reference_input = tmp_path / "reference.pkl"
    query_input = tmp_path / "query.pkl"
    reference_output = tmp_path / "reference_sword.pkl"
    results_dir = tmp_path / "results"

    pd.DataFrame({"cif": [cif], "source_id": ["cuau-disordered-reference"]}).to_pickle(
        reference_input
    )
    pd.DataFrame({"cif": [cif], "candidate_id": ["cuau-disordered-query"]}).to_pickle(
        query_input
    )

    run_cli(
        "get_sword_dic.py",
        "--input-pkl",
        str(reference_input),
        "--output-pkl",
        str(reference_output),
        "--workers",
        "1",
        cwd=REPOSITORY_ROOT,
    )
    benchmark = run_cli(
        "family_tree_bench.py",
        "--reference-pkl",
        str(reference_output),
        "--query-pkl",
        str(query_input),
        "--output-dir",
        str(results_dir),
        "--workers",
        "1",
        cwd=REPOSITORY_ROOT,
    )

    assert "FT_order" in benchmark.stdout
    result = pd.read_pickle(results_dir / "query_SWORD_family_dic.pkl")
    assert len(result) == 1
    assert result.loc[0, "has_disordered_icsd_family"] == 1
    assert {
        "cif",
        "candidate_id",
        "SWORD_family_dic",
        "SWORD_label",
        "has_ordered_icsd_family",
        "has_disordered_icsd_family",
    } <= set(result.columns)
