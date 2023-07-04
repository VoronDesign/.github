import functools
import itertools
import logging
import os
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

file_handler = FileHandler.FileHandler()

try:
    imagekit: ImageKit | None = ImageKit(
        private_key=os.environ["IMAGEKIT_PRIVATE_KEY"],
        public_key=os.environ["IMAGEKIT_PUBLIC_KEY"],
        url_endpoint=os.environ["IMAGEKIT_URL_ENDPOINT"],
    )
    imagekit_options: UploadFileRequestOptions = UploadFileRequestOptions(
        use_unique_file_name=True,
        folder=os.environ["IMAGEKIT_SUBFOLDER"],
        is_private_file=False,
        overwrite_file=True,
        overwrite_ai_tags=True,
        overwrite_tags=True,
        overwrite_custom_metadata=True,
    )
except (KeyError, ValueError):
    imagekit = None


def make_image_url(stl_file_path: Path, input_args: argparse.Namespace) -> str:
    if imagekit is None:
        logger.warning("No suitable imagekit credentials were found. Skipping image creation!")
        return ""

    cmd = [
        "stl-thumb",
        stl_file_path.as_posix(),
        Path(input_args.temp_image_dir, stl_file_path.with_suffix(".png").name).as_posix(),
        "-a",
        "fxaa",
        "-s",
        "300",
    ]
    subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    with open(Path(input_args.temp_image_dir, stl_file_path.with_suffix(".png").name), "rb") as image:
        result: UploadFileResult = imagekit.upload_file(
            file=image, file_name=stl_file_path.with_suffix(".png").name, options=imagekit_options
        )
    Path(input_args.temp_image_dir, stl_file_path.with_suffix(".png").name).unlink()
    return result.url


def check_stl_rotation(input_args: argparse.Namespace, stl_file_path: Path) -> Tuple[bool, str]:
    logger.info(f"Checking {stl_file_path.as_posix()}")
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


def main(args: argparse.Namespace):
    input_path: Path = Path(args.input_dir)
    fail: bool = False

    if args.verbose:
        logger.setLevel("INFO")

    logger.info(f"Processing STL files in {str(input_path)}")
    stls: List[Path] = list(itertools.chain(input_path.glob("**/*.stl"), input_path.glob("**/*.STL")))
    if len(stls) == 0:
        return
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

    if args.fail_on_error and fail:
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
        "-t",
        "--temp_image_dir",
        required=False,
        action="store",
        type=str,
        help="Temporary image directory for storing images while uploading to imgur",
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
