from pathlib import Path
import os
import yaml
import textwrap

preamble = """# Mods

Printer mods for Voron 3D printers

## Legacy printers

Mods for legacy printers can be found [here](../legacy_printers/printer_mods).
If one of your legacy mods applies to a current Voron 3D printer and therefore should be included in this list,
contact the admins on Discord to have your mod moved to this folder.

---

"""

header = """
| Creator | Mod title | Description | Printer compatibility |
| --- | --- | --- | --- |
"""


def main():
    yaml_list = Path(".").glob("**/.metadata.yml")
    prev_username = ""
    final_readme = header
    for yml in sorted(yaml_list):
        with open(yml, "r") as f:
            content = yaml.safe_load(f)
            title = textwrap.shorten(content["title"], width=35, placeholder="...")
            creator = yml.parts[0] if yml.parts[0] != prev_username else ""
            description = textwrap.shorten(content["description"], width=70, placeholder="...")
            final_readme += (
                f'| {creator} | [{title}]({yml.relative_to(".").parent}) | {description} | '
                f'{", ".join(sorted(content["printer_compatibility"]))} |\n'
            )
            prev_username = yml.parts[0]
    with open(os.environ["GITHUB_STEP_SUMMARY"], 'w') as f:
       f.write(final_readme)
    if os.environ["PREVIEW"] == "false":
        with open("README.md", "w") as f:
            f.write(preamble)
            f.write(final_readme)


if __name__ == "__main__":
    main()
