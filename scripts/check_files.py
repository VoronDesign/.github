from pathlib import Path
import os
import sys
import yaml
from typing import Any, Dict, Iterable

header = """
| File type | File | Exists |
| --- | --- | --- |
"""


def main():
    yaml_list: Iterable[Path] = Path(".").glob("**/.metadata.yml")
    result_error: bool = False
    step_summary: str = ""
    for yml in sorted(yaml_list):
        with open(yml, "r") as f:
            content: Dict[str, Any] = yaml.safe_load(f)
            step_summary += f"## Checking {yml.as_posix()}\n"
            step_summary += header
            for cad_file in content["cad"]:
                if Path(yml.parent, cad_file).exists():
                    step_summary += f"| CAD | {cad_file} | ✅ |\n"
                else:
                    step_summary += f"| CAD | {cad_file} | ❌ |\n"
                    result_error = True
            for img_file in content.get("images", list()):
                if Path(yml.parent, img_file).exists():
                    step_summary += f"| IMG | {img_file} | ✅ |\n"
                else:
                    step_summary += f"| IMG | {img_file} | ❌ |\n"
                    result_error = True
            step_summary += "\n"
    with open(os.environ["GITHUB_STEP_SUMMARY"], "w") as f:
        f.write(step_summary)
    if result_error:
        return sys.exit(255)


if __name__ == "__main__":
    main()
