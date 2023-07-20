import functools
import itertools
import logging
import os
import random
import string
import subprocess
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, List, Tuple

from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio.models.results import UploadFileResult
from tweaker3 import FileHandler
from tweaker3.MeshTweaker import Tweak
from imagekitio import ImageKit

logging.basicConfig()
logger = logging.getLogger(__name__)

STEP_SUMMARY_PREAMBLE = """## STL rotation check summary

| Filename | Result | Current orientation | Suggested orientation | 
| ----- | --- | --- | --- |
"""

RESULT_OK = "✅ PASSED"
RESULT_WARNING = "⚠️ WARNING"
RESULT_ERROR = "❌ FAILED"

file_handler = FileHandler.FileHandler()

critical_error: bool = False

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase + string.ascii_uppercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def make_image_url(stl_file_path: Path, input_args: argparse.Namespace) -> str:
    image_file_name = stl_file_path.with_stem(stl_file_path.stem + "_" + get_random_string(8)).with_suffix(".png").name
    image_out_folder = Path(input_args.output_dir, "img", input_args.imagekit_subfolder)
    image_out_path = Path(image_out_folder, image_file_name)
    image_out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "stl-thumb",
        stl_file_path.as_posix(),
        image_out_path.as_posix(),
        "-a",
        "fxaa",
        "-s",
        "300",
    ]

    subprocess.check_output(cmd, stderr=subprocess.DEVNULL)

    return f"{input_args.url_endpoint}/{input_args.imagekit_subfolder}/{image_file_name}"


def check_stl_rotation(input_args: argparse.Namespace, stl_file_path: Path) -> Tuple[bool, str]:
    logger.info(f"Checking {stl_file_path.as_posix()}")
    try:
        stl_has_bad_rotation: bool = False
        rotated_image_url: str = ""
        original_image_url: str = make_image_url(stl_file_path=stl_file_path, input_args=input_args)

        objs: Dict[int, Any] = file_handler.load_mesh(inputfile=stl_file_path.as_posix())
        if len(objs.items()) > 1:
            logger.warning(f"{stl_file_path.as_posix()} contains multiple objects and is therefore skipped.!")
            return False, ""
        x: Tweak = Tweak(objs[0]["mesh"], extended_mode=True, verbose=False, min_volume=True)

        if x.rotation_angle >= 0.1:
            if input_args.output_dir is not None:
                out_stl_path: Path = Path(
                    input_args.output_dir,
                    stl_file_path.relative_to(input_args.input_dir).with_stem(f"{stl_file_path.stem}_rotated"),
                )
                out_stl_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Saving rotated STL to: {out_stl_path}")
                file_handler.write_mesh(
                    objects=objs, info={0: {"matrix": x.matrix, "tweaker_stats": x}}, outputfile=out_stl_path.as_posix()
                )
                rotated_image_url = make_image_url(stl_file_path=out_stl_path, input_args=input_args)
            stl_has_bad_rotation = True
        else:
            logger.info(f"STL {stl_file_path.as_posix()} does not contain any errors!")
        github_summary_table_contents: str = " | ".join(
            [
                stl_file_path.name,
                RESULT_WARNING if stl_has_bad_rotation else RESULT_OK,
                f'[<img src="{original_image_url}" width="100" height="100">]({original_image_url})',
                f'[<img src="{rotated_image_url}" width="100" height="100">]({rotated_image_url})'
                if rotated_image_url != ""
                else "",
            ]
        )
        github_summary_table = f"| {github_summary_table_contents} |\n"
        return stl_has_bad_rotation, github_summary_table
    except Exception as e:
        logger.error("A fatal error occurred during rotation checking", exc_info=e)
        global critical_error
        critical_error = True
        return True, f'| {" | ".join([ stl_file_path.name, RESULT_ERROR, "", ""])} |\n'

def main(args: argparse.Namespace):
    global critical_error
    input_path: Path = Path(args.input_dir)
    fail: bool = False

    if args.verbose:
        logger.setLevel("INFO")

    logger.info(f"Processing STL files in {str(input_path)}")
    stls: List[Path] = list(itertools.chain(input_path.glob("**/*.stl"), input_path.glob("**/*.STL")))
    if len(stls) == 0:
        return
    if len(stls) > 40:
        logger.warning(f"Excessive amount of STLs ({len(stls)}) detected. I am only going to check 40!")
        stls = stls[:40]
    with ThreadPoolExecutor() as pool:
        results = pool.map(functools.partial(check_stl_rotation, args), stls)

    summaries: List[str] = []
    for result_fail, summary in results:
        summaries.append(summary)
        fail = result_fail or fail

    if args.github_step_summary:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "w") as gh_step_summary:
            gh_step_summary.write(STEP_SUMMARY_PREAMBLE)
            for summary in summaries:
                gh_step_summary.write(summary)

    with open(os.environ["GITHUB_OUTPUT"], 'a') as f:
        if fail:
            f.write("ROTATION_SUGGESTED=true")
        else:
            f.write("ROTATION_SUGGESTED=false")

    if (args.fail_on_error and fail) or critical_error:
        sys.exit(255)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="VoronDesign STL rotation checker & fixer",
        description="This tool can be used to check the rotation of STLs in a folder and potentially fix them",
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
        "-u",
        "--url_endpoint",
        required=True,
        action="store",
        type=str,
        help="Imagekit endpoint",

    )
    parser.add_argument(
        "-c",
        "--imagekit_subfolder",
        required=True,
        action="store",
        type=str,
        help="Image subfolder within the imagekit storage",
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
        help="Whether to return an error exit code if one of the STLs is badly oriented",
    )
    parser.add_argument(
        "-g",
        "--github_step_summary",
        required=False,
        action="store_true",
        help="Whether to output a step summary when running inside a github action",
    )
    args: argparse.Namespace = parser.parse_args()
    main(args=args)
