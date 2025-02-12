#!/usr/bin/env python3
# Copyright lowRISC contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

import logging
from pathlib import Path
from pprint import pformat
from typing import List

from device_profile_data import extract_profile_data
from common import (
    LLD_TARGET,
    BazelTestType,
    CoverageParams,
    run,
)

# Commands that this script uses
LLVM_PROFDATA = "llvm-profdata"


def handle_libs(device_libs_all: List[str]) -> List[str]:
    """Filter device libraries that are not compatible with the target.

    Args:
        device_libs_all: A list of device libraries.

    Returns:
        `device_libs_all` with incompatible libraries filtered out.
    """
    # Remove on_host libs
    device_libs_incompat = [lib for lib in device_libs_all if "on_host" in lib]
    logging.info(f"incompatible libraries: {pformat(device_libs_incompat)}")
    # TODO: may want to add the coverage runtime to avoid undefined symbol warnings
    return sorted(list(set(device_libs_all) - set(device_libs_incompat)))


def handle_objs(merged_library: Path, obj_files: List[str]) -> None:
    """Create a library from the given object files.

    Args:
        merged_library: Path where to save the merged library.
        obj_files: A list of object files.
    """
    # Note: We allow unresolved symbols and multiple definitions because this library is
    # used only for generating a coverage report and we link only and all intrumented
    # object files.
    # TODO(#16761): Try to remove these flags.
    run(LLD_TARGET, "--warn-unresolved-symbols", "-zmuldefs", "-o",
        str(merged_library), *obj_files)


def handle_test_targets(test_targets: List[str]) -> List[str]:
    """Choose cw310_test_rom tests from the given list of tests.

    This function also filters wycheproof tests since they take a long time to run.

    Args:
        test_targets: A list of test targets.

    Returns:
        cw310_test_rom tests without wycheproof tests.
    """
    return [
        t for t in test_targets
        if "cw310_test_rom" in t and "wycheproof" not in t
    ]


def handle_test_log_dirs(test_log_dirs: List[Path]) -> List[Path]:
    """Get coverage profiles.

    This function processes the logs in the given list of test log directories to
    produce raw profiles and returns their paths. These profiles can then be indexed and
    merged to produce a single profile file.

    Args:
        test_log_dirs: A list of test log directories.

    Returns:
        Paths of individual raw coverage profiles.

    """
    raw_profiles = []
    for d in test_log_dirs:
        with (Path(d) / "test.log").open("rb") as test_log, (
                Path(d) / "prof.raw").open("wb") as raw_profile:
            raw_profile.write(
                extract_profile_data(test_log.read().decode("ascii",
                                                            "ignore")))
            raw_profiles += [Path(raw_profile.name)]
    logging.info(f"raw profiles: {pformat(raw_profiles)}")
    return raw_profiles


PARAMS = CoverageParams(
    bazel_test_type=BazelTestType.SH_TEST,
    config="ot_coverage_on_target",
    libs_fn=handle_libs,
    objs_fn=handle_objs,
    test_targets_fn=handle_test_targets,
    test_log_dirs_fn=handle_test_log_dirs,
    report_title="OpenTitan Functional Test Coverage",
)
