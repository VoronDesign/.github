from pathlib import Path
import os
import yaml
import json
import argparse
import textwrap
import logging
import subprocess

logging.basicConfig()
logger = logging.getLogger(__name__)

preamble = """# Mods

Printer mods for Voron 3D printers

## Legacy printers

Mods for legacy printers can be found [here](../legacy_printers/printer_mods).
If one of your legacy mods applies to a current Voron 3D printer and therefore should be included in this list,
contact the admins on Discord to have your mod moved to this folder.

---

"""

header = """
| Creator | Mod title | Description | Printer compatibility | Last Changed |
| --- | --- | ----- | --- | --- |
"""


def main(args: argparse.Namespace):

    if args.verbose:
        logger.setLevel("INFO")
    yaml_list = Path(args.input_dir).glob("**/.metadata.yml")
    mods = []
    for yml_file in sorted(yaml_list):
        with open(yml_file, "r") as f:
            content = yaml.safe_load(f)
            mods.append({
                "path": yml_file.relative_to(args.input_dir).parent.as_posix(),
                "title": textwrap.shorten(content["title"], width=35, placeholder="..."),
                "creator":  yml_file.relative_to(args.input_dir).parts[0],
                "description": textwrap.shorten(content["description"], width=70, placeholder="..."),
                "printer_compatibility": f'{", ".join(sorted(content["printer_compatibility"]))}',
                "last_changed": subprocess.run(['git', '-C', args.input_dir, 'log', '-n', '1', '--date=iso-local', '--format=%cd', '--', yml_file.relative_to(args.input_dir).parent.as_posix()], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
            })

    if args.json == 'true':
        with open(Path(args.input_dir, "mods.json"), "w", encoding='utf-8') as f:
            json.dump(mods, f)

    with open(os.environ["GITHUB_STEP_SUMMARY"], "w", encoding='utf-8') as f:
        f.write(header)
        prev_username = ""
        for mod in mods:
            f.write(f'| {mod["creator"] if mod["creator"] != prev_username else ""} | [{mod["title"]}]({mod["path"]}) | {mod["description"]} | {mod["printer_compatibility"]} | {mod["last_changed"]} |\n')
            prev_username = mod["creator"]
    if args.preview != "true":
        with open(Path(args.input_dir, "README.md"), "w", encoding='utf-8') as f:
            f.write(preamble)
            f.write(header)
            prev_username = ""
            for mod in mods:
                f.write(
                    f'| {mod["creator"] if mod["creator"] != prev_username else ""} '
                    f'| [{mod["title"]}]({mod["path"]}) '
                    f'| {mod["description"]} '
                    f'| {mod["printer_compatibility"]} '
                    f'| {mod["last_changed"]} '
                    '|\n'
                )
                prev_username = mod["creator"]


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="VoronDesign VoronUsers readme generator",
        description="This tool is used to generate the readme and json overview files for VORONUsers",
    )
    parser.add_argument(
        "-p",
        "--preview",
        required=True,
        action="store",
        type=str,
        help="Whether to preview or actually generate the readme",
    )
    parser.add_argument(
        "-i",
        "--input_dir",
        required=True,
        action="store",
        type=str,
        help="Base directory for generated files",
    )
    parser.add_argument(
        "-j",
        "--json",
        required=False,
        action="store",
        type=str,
        help="Whether to generate a json file as well",

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
