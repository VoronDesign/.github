import itertools
import logging
import os
import sys
import argparse
from pathlib import Path
from typing import List

from admesh import Stl
from enum import IntEnum
from typing import Dict


class ReturnStatus(IntEnum):
    SUCCESS = 0
    WARNING = 1
    FAILURE = 2
    EXCEPTION = 3

return_status_string_map: Dict[ReturnStatus, str] = {
    ReturnStatus.SUCCESS: 'success',
    ReturnStatus.WARNING: 'warning',
    ReturnStatus.FAILURE: 'failure',
    ReturnStatus.EXCEPTION: 'exception'
}

RESULT_SUCCESS = "✅ PASSED"
RESULT_WARNING = "⚠️ WARNING"
RESULT_FAILURE = "❌ FAILURE"
RESULT_EXCEPTION = "❌ EXCEPTION"

logging.basicConfig()
logger = logging.getLogger(__name__)



STEP_SUMMARY_PREAMBLE = """## STL corruption check summary

| Filename | Result | Edges Fixed | Backwards Edges | Degenerate Facets | Facets Removed | Facets Added | Facets Reversed |
| ----- | --- | --- | --- | --- | --- | --- | --- |
"""


def process_stl(stl_file: Path, args: argparse.Namespace) -> ReturnStatus:
    logger.info(f"Checking {stl_file}")
    try:
        stl: Stl = Stl(stl_file.as_posix())
        stl.repair(verbose_flag=False)
        if (
            stl.stats["edges_fixed"] > 0
            or stl.stats["backwards_edges"] > 0
            or stl.stats["degenerate_facets"] > 0
            or stl.stats["facets_removed"] > 0
            or stl.stats["facets_added"] > 0
            or stl.stats["facets_reversed"] > 0
        ):
            logger.error(f"Corrupt STL detected! Please fix {stl_file.as_posix()}!")
            if args.github_step_summary:
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as gh_step_summary:
                    cell_contents: str = " | ".join(
                        [
                            stl_file.name,
                            RESULT_FAILURE,
                            str(stl.stats["edges_fixed"]),
                            str(stl.stats["backwards_edges"]),
                            str(stl.stats["degenerate_facets"]),
                            str(stl.stats["facets_removed"]),
                            str(stl.stats["facets_added"]),
                            str(stl.stats["facets_reversed"]),
                        ]
                    )
                    gh_step_summary.write(f"| {cell_contents} |\n")
            if args.output_dir is not None:
                out_stl_path: Path = Path(args.output_dir, stl_file.relative_to(args.input_dir))
                out_stl_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Saving fixed STL to: {out_stl_path}")
                stl.write_ascii(out_stl_path.as_posix())
            return ReturnStatus.FAILURE
        else:
            logger.info(f"STL {stl_file.as_posix()} does not contain any errors!")
            if args.github_step_summary:
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as gh_step_summary:
                    cell_contents: str = " | ".join(
                        [
                            stl_file.name,
                            RESULT_SUCCESS,
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                            "0",
                        ]
                    )
                    gh_step_summary.write(f"| {cell_contents} |\n")
        return ReturnStatus.SUCCESS
    except Exception as e:
        logger.error("A fatal error occurred during rotation checking", exc_info=e)
        if args.github_step_summary:
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as gh_step_summary:
                cell_contents: str = " | ".join(
                    [
                        stl_file.name,
                        RESULT_EXCEPTION,
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                    ]
                )
                gh_step_summary.write(f"| {cell_contents} |\n")
        return ReturnStatus.EXCEPTION

def main(args: argparse.Namespace):
    input_path: Path = Path(args.input_dir)
    return_status: ReturnStatus = ReturnStatus.SUCCESS

    if args.verbose:
        logger.setLevel("INFO")

    logger.info(f"Processing STL files in {str(input_path)}")
    stls: List[Path] = list(itertools.chain(input_path.glob("**/*.stl"), input_path.glob("**/*.STL")))
    if len(stls) == 0:
        return
    if len(stls) > 40:
        logger.warning(f"Excessive amount of STLs ({len(stls)}) detected. I am only going to check 40!")
        stls = stls[:40]
    
    if args.github_step_summary:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "w") as gh_step_summary:
            gh_step_summary.write(STEP_SUMMARY_PREAMBLE)

    for stl in stls:
        return_status = max(process_stl(stl_file=stl, args=args), return_status)

    with open(os.environ["GITHUB_OUTPUT"], 'a') as f:
        f.write(f"extended_outcome={return_status_string_map[return_status]}\n")

    if return_status > ReturnStatus.SUCCESS and args.fail_on_error:
        logger.error("Error detected during STL checking!")
        sys.exit(255)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="VoronDesign STL checker & fixer",
        description="This tool can be used to check a provided folder of STLs and potentially fix them",
    )
    parser.add_argument(
        "-i",
        "--input_dir",
        required=True,
        action="store",
        type=str,
        help="Directory containing STL files to be checked",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        required=False,
        action="store",
        type=str,
        help="Directory to store the fixed STL files into",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        help="Print debug output to stdout",
    )
    parser.add_argument(
        "-f",
        "--fail_on_error",
        required=False,
        action="store_true",
        help="Whether to return an error exit code if one of the STLs is faulty",
    )
    parser.add_argument(
        "-g",
        "--github_step_summary",
        required=False,
        action="store_true",
        help="Whether to output a step summary when running inside a github action",
    )
    args: argparse.Namespace = parser.parse_args()
    main(args)
