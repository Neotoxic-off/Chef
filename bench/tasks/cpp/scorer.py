"""Score the cpp task: CMake build, CTest count, cppcheck, the hidden test plain and under ASan and UBSan, in Docker."""

from pathlib import Path

from score import Metrics
from scorer_lib import CmakeTask, score_cmake_library

TASK: CmakeTask = CmakeTask(
    standard="cxx_std_20",
    target="lru_cache",
    hidden_test=Path(__file__).resolve().parent / "hidden_test.cpp",
)


def score(workspace: Path) -> Metrics:
    return score_cmake_library(workspace, TASK)
