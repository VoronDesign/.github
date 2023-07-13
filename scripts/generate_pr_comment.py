import argparse
import logging
from typing import Any, Dict
import os
import sys

import requests

logging.basicConfig()
logger = logging.getLogger(__name__)

result_map: Dict[str, str] = {
    "success": "✅  Success",
    "cancelled": "🚫  Cancelled",
    "skipped": "⏩  Skipped",
    "failure": "❌  Failure",
    "": "❔  Unknown",
}

preamble = """ Hi, thank you for submitting your PR.
Please find below the results of the automated PR checker:

| Task | Result | Summary Link |
| ------ | ---- | ---- |
"""


def build_api_url(repository: str, action_id: str) -> str:
    return f"https://api.github.com/repos/{repository}/actions/runs/{action_id}/jobs"


def build_summary_detail_url(repository: str, action_id: str, job_id: str) -> str:
    return f"[Summary](https://github.com/{repository}/actions/runs/{action_id}#summary-{job_id})"


def main(args: argparse.Namespace):
    try:
        json_response: requests.Response = requests.get(
            build_api_url(repository=args.repository, action_id=args.action_id)
        )
        response_dict: Dict[str, Any] = json_response.json()
        pr_comment: str = ""
        success: bool = True

        for job in response_dict.get("jobs", []):
            job_id: str = str(job.get("id", ""))
            job_name: str = job.get("name", "").split("/")[0]
            job_summary_url: str = build_summary_detail_url(
                repository=args.repository, action_id=args.action_id, job_id=job_id
            )
            if job.get("conclusion", "") == "failure":
                success = False
            if job.get("conclusion", "") in [None, "None"]:  # Job is still running, e.g. this job
                continue
            job_result: str = result_map[job.get("conclusion", "")]
            pr_comment += f"| {' | '.join([job_name, job_result, job_summary_url])} |\n"

        with open(args.out_file, "w") as f:
            f.write(preamble)
            f.write(pr_comment)
            f.write("\n\n")
            if success:
                f.write("Congratulations, all checks have completed successfully! Your PR is now ready for review!")
            else:
                f.write("Some checks have failed for your PR. Please refer to the individual step summaries ")
                f.write("to find out what the errors were and how to fix them!")
            f.write("\n\nI am a 🤖, this comment was generated automatically!")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            if success:
                fh.write(f'ALL_STEPS_OK=true')
            else:
                fh.write(f'ALL_STEPS_OK=false')
    except (requests.RequestException, KeyError, ValueError, IOError) as e:
        logger.error("An Error occurred while generating the PR comment", exc_info=e)
        if args.fail_on_error:
            sys.exit(255)


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
        "-a", "--action_id", required=True, type=str, action="store", help="ID of the action to create a PR for"
    )
    parser.add_argument(
        "-o",
        "--out_file",
        required=False,
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
    parser.add_argument(
        "-f",
        "--fail_on_error",
        required=False,
        action="store_true",
        help="Whether to return an error exit code if something goes wrong",
    )

    args: argparse.Namespace = parser.parse_args()
    main(args=args)
