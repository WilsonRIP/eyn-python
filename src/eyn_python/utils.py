from __future__ import annotations

import shutil
import subprocess
from typing import Iterable, List

class ShellError(RuntimeError):
    pass

def which(binary: str) -> str | None:
    return shutil.which(binary)

def run(
    args: Iterable[str],
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        list(args),
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if check and cp.returncode != 0:
        stdout = cp.stdout.strip() if cp.stdout else ""
        stderr = cp.stderr.strip() if cp.stderr else ""
        raise ShellError(f"Command failed ({cp.returncode}): {' '.join(args)}\n{stderr or stdout}")
    return cp

def flatten(items: Iterable[Iterable[str]]) -> List[str]:
    return [x for sub in items for x in sub]


