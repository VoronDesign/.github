import argparse
from concurrent.futures import ThreadPoolExecutor
import functools
import itertools
import logging
import os
from pathlib import Path
import sys
from typing import List
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from imagekitio.models.results import UploadFileResult

logging.basicConfig()
logger = logging.getLogger(__name__)

try:
    imagekit: ImageKit | None = ImageKit(
        private_key=os.environ["IMAGEKIT_PRIVATE_KEY"],
        public_key=os.environ["IMAGEKIT_PUBLIC_KEY"],
        url_endpoint=os.environ["IMAGEKIT_URL_ENDPOINT"],
    )
    imagekit_options_common: UploadFileRequestOptions = UploadFileRequestOptions(
        is_private_file=False,
        overwrite_file=True,
        overwrite_ai_tags=True,
        overwrite_tags=True,
        overwrite_custom_metadata=True,
    )
except (KeyError, ValueError):
    imagekit = None
    imagekit_options_common = None

def upload_image(input_args: argparse.Namespace, image_path: Path) -> bool:
    if imagekit is None or imagekit_options is None:
        logger.warning("No suitable imagekit credentials were found. Skipping image creation!")
        return False

    with open(image_path, "rb") as image:
        imagekit_options: UploadFileRequestOptions = imagekit_options_common
        imagekit_options.folder = image_path.relative_to(Path(input_args.input_folder))
        result: UploadFileResult = imagekit.upload_file(
            file=image, file_name=image_path.name, options=imagekit_options
        )
    print(result)
    return result.url != ""

def main(args: argparse.Namespace):
    input_path: Path = Path(args.input_folder)

    logger.info(f"Processing Image files in {str(input_path)}")
    images: List[Path] = list(input_path.glob("**/*.png"))
    if len(images) == 0:
        return
    with ThreadPoolExecutor() as pool:
        results = pool.map(functools.partial(upload_image, args), images)

    if args.fail_on_error and not all(results):
        sys.exit(255)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="VoronDesign STL rotation checker & fixer",
        description="This tool can be used to check the rotation of STLs in a folder and potentially fix them",
    )
    parser.add_argument(
        "-i",
        "--input_folder",
        required=True,
        action="store",
        type=str,
        help="Directory containing STL files to be checked",
    )
    args: argparse.Namespace = parser.parse_args()
    main(args=args)