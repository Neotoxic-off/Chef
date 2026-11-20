"""Score the c task: CMake build, CTest count, cppcheck, the hidden test plain and under ASan and UBSan, in Docker."""

from pathlib import Path

from score import Metrics
from scorer_lib import CmakeTask, score_cmake_library

TASK: CmakeTask = CmakeTask(standard="c_std_17", target="ringbuf", hidden_test=Path(__file__).resolve().parent / "hidden_test.c")


def score(workspace: Path) -> Metrics:
    return score_cmake_library(workspace, TASK)
