import argparse
import logging
from typing import Any, Dict, List, Optional, Tuple
import os
import sys

from pathlib import Path

import requests

logging.basicConfig()
logger = logging.getLogger(__name__)

result_map: Dict[str, str] = {
    "success": "✅  Success",
    "cancelled": "🚫  Cancelled",
    "warning": "⚠️  Warning",
    "skipped": "⏩  Skipped",
    "failure": "❌  Failure",
    "exception": "❌  Exception",
    "": "⏩  Skipped",
}

preamble = """ Hi, thank you for submitting your PR.
Please find below the results of the automated PR checker:

| Task | Result | Summary Link | Logs |
| ------ | ---- | ---- | ---- |
"""


def build_summary_detail_url(repository: str, action_id: str, job_id: str) -> str:
    return f"[Summary](https://github.com/{repository}/actions/runs/{action_id}#summary-{job_id})"

def build_log_detail_url(repository: str, action_id: str, job_id: str) -> str:
    return f"[Logs](https://github.com/{repository}/actions/runs/{action_id}/job/{job_id})"

def get_results_from_folder(repository: str, action_id: str, folder: Path) -> Tuple[Optional[str], Optional[str]]:
    result_file: Path = Path(folder, "result")
    job_id_file: Path = Path(folder, "job_id")
    error_label_file: Path = Path(folder, "error_label")
    if (result_file.exists() and job_id_file.exists() and error_label_file.exists()):
        result: str = result_file.read_text()
        job_id: str = job_id_file.read_text()
        error_label: str = error_label_file.read_text()
        comment_line: str = f"| {folder.name} | {result_map[result]} | {build_summary_detail_url(repository, action_id, job_id)} | {build_log_detail_url(repository, action_id, job_id)} |\n"
        label = error_label if result != 'success' else None
        return comment_line, f'"{label}"'
    return None, None

def main(args: argparse.Namespace):
    try:
        ready_label: str = Path(args.input_folder, "ready_label").read_text()
        pr_number: str = Path(args.input_folder, "pr_number").read_text()
        action_run_id: str = Path(args.input_folder, "action_run_id").read_text()
        pr_comment: str = ""
        labels: List[str] = []
        success: bool = True

        folders: List[Path] = [x for x in Path(args.input_folder).iterdir() if x.is_dir()]

        for folder in folders:
            comment_line, label = get_results_from_folder(repository=args.repository, action_id=action_run_id, folder=folder)
            if comment_line is not None:
                pr_comment += f"{comment_line}"
            if label is not None:
                success = False
                labels.append(label)

        Path(args.out_file).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_file, "w", encoding="utf-8") as f:
            f.write(preamble)
            f.write(pr_comment)
            f.write("\n\n")
            if success:
                f.write("Congratulations, all checks have completed successfully! Your PR is now ready for review!")
            else:
                f.write("Some checks have failed or produced warnings for your PR. Please refer to the individual step summaries ")
                f.write("to find out what the errors were and how to fix them!")
            f.write("\n\nI am a 🤖, this comment was generated automatically!")

        if success:
            labels = [f'"{ready_label}"']

        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            print(f'labels-to-set={",".join(labels)}', file=fh)
            print(f'pr-number={pr_number}', file=fh)

    except (requests.RequestException, KeyError, ValueError, IOError) as e:
        logger.error("An Error occurred while generating the PR comment", exc_info=e)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="VoronDesign PR comment generator",
        description="This tool generates a PR comment with direct links to summaries",
    )
    parser.add_argument(
        "-r",
        "--repository",
        required=True,
        action="store",
        help="Repository name",
    )

    parser.add_argument(
        "-i",
        "--input_folder",
        required=True,
        action="store",
        type=str,
        help="Input folder containing all the PR metadata",
    )
    
    parser.add_argument(
        "-o",
        "--out_file",
        required=True,
        action="store",
        type=str,
        help="File to store the pr comment into",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        help="Print debug output to stdout",
    )

    args: argparse.Namespace = parser.parse_args()
    main(args=args)
