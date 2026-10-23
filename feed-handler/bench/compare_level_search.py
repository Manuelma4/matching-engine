#!/usr/bin/env python3
"""Run the frozen, paired price-level search experiment after its prerequisites.

Only reverse_linear versus binary is varied. Both measured builds use the flat
reference index. Retained ordered-state exports and all eight small correctness
builds must already pass; this program never builds or executes a proof's commands.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import stat
import subprocess
import sys

# Also support direct importlib loading by the independently frozen private tests.
BENCH = Path(__file__).resolve().parent
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))
import compare_storage as base


ROOT = BENCH.parent
WORK = ROOT.parent
ENGINE = WORK / "matching-engine"
POLICIES = ("reverse_linear", "binary")
GROUPS = (("nasdaq", "default"), ("nasdaq", "fit"), ("bx", "default"), ("bx", "fit"))
PAIRS = (POLICIES, POLICIES[::-1], POLICIES[::-1], POLICIES, POLICIES, POLICIES[::-1])
EVERY = 1_000_000
TIMEOUT = 1800
MAX_METADATA = 16 << 20
MAX_REPORT = 8 << 20
DESIGN_COMMIT = "2b7e8b26e04314ce0e24b5d12887619ff84e118f"
DESIGN_PATH = "docs/validation/2026-10-23-level-search-design/design.json"
DESIGN_SHA = "eb68558aee6a5cb054541ca9eb262f89f9d95e17f1416248c9fb8ff8a0349d15"
CONTRACT_SHA = "6551554e3b4c96b2802dfeed14932dfdb6d0e4f619ada61acdbbc41f25325a79"
ACCEPTANCE_PATH = "docs/validation/2026-10-23-level-search/prerequisites.json"
CASES = {
    "nasdaq": {"path": ROOT / "data/12302019.NASDAQ_ITCH50.itch", "bytes": 8251407909,
        "sha256": "5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f",
        "fit_orders": 2097152, "checkpoints": 269, "nonempty": 268},
    "bx": {"path": ROOT / "data/20190730.BX_ITCH_50.itch", "bytes": 837472908,
        "sha256": "6741035beda0c237fc2d30e03756f30449791844f372de955a29da32a4b842e5",
        "fit_orders": 131072, "checkpoints": 29, "nonempty": 28},
}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def equal(actual, expected, context):
    """JSON equality with exact scalar types, including bool versus integer."""
    if type(actual) is not type(expected):
        raise ValueError(f"{context}: type differs")
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise ValueError(f"{context}: object fields differ")
        for key in expected:
            equal(actual[key], expected[key], f"{context}.{key}")
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(f"{context}: list length differs")
        for index, item in enumerate(expected):
            equal(actual[index], item, f"{context}[{index}]")
    elif actual != expected:
        raise ValueError(f"{context}: value differs")


def schedule():
    result = []
    for phase in ("correctness", "memory"):
        for index, (case, profile) in enumerate(GROUPS):
            pair = POLICIES if phase == "correctness" else PAIRS[index]
            result.extend(dict(phase=phase, case=case, profile=profile,
                               level_search=policy, round=None) for policy in pair)
    for round_index, pair in enumerate(PAIRS):
        rotation = round_index % len(GROUPS)
        for case, profile in GROUPS[rotation:] + GROUPS[:rotation]:
            result.extend(dict(phase="timing", case=case, profile=profile,
                               level_search=policy, round=round_index) for policy in pair)
    return result


def check_schedule(rows):
    keys = ("phase", "case", "profile", "level_search", "round")
    projected = [{key: row.get(key) for key in keys} for row in rows]
    equal(projected, schedule(), "actual launch schedule")


def capacities(case, profile):
    if case not in CASES or profile not in ("default", "fit"):
        raise ValueError("unknown fixed flow/capacity profile")
    orders = base.DEFAULT_ORDERS if profile == "default" else CASES[case]["fit_orders"]
    return orders, min(orders, base.DEFAULT_LEVELS)


def policy_summary(summary, source_bytes, policy, orders, levels):
    if policy not in POLICIES or summary.get("level_search") != policy:
        raise ValueError("tool level_search differs from the requested search policy")
    return base.semantic(summary, source_bytes, "open_addressed", orders, levels)


def validate_definitions(policy, tokens):
    if policy not in POLICIES:
        raise ValueError("unknown search policy")
    for name, value in (("ITCH_STD_REFERENCE_INDEX", 0),
                        ("ITCH_BINARY_LEVEL_SEARCH", int(policy == "binary"))):
        definitions = [token for token in tokens if token.startswith(f"-D{name}")]
        if definitions != [f"-D{name}={value}"] or any(token.startswith(f"-U{name}") for token in tokens):
            raise ValueError(f"actual compiler definitions do not uniquely select {name}={value}")


def reject_sanitizers(tokens):
    if any("sanitize" in token.lower() for token in tokens):
        raise ValueError("sanitizer compile/link flags are forbidden in measured builds")


def require_reference(actual, expected):
    for ref in (actual, expected):
        if (not isinstance(ref, dict) or set(ref) != {"path", "bytes", "sha256"} or
                not isinstance(ref["path"], str) or not base.uint(ref["bytes"]) or
                not isinstance(ref["sha256"], str) or SHA.fullmatch(ref["sha256"]) is None):
            raise ValueError("invalid retained file identity")
    equal(actual, expected, "accepted retained identity")


def compare_export(actual, reference, summary, expected):
    if actual != reference:
        raise ValueError("ordered independent inventory CSV differs")
    if summary.get("passed") is not True or summary.get("validation_scope") != "full_prefix_all_symbols":
        raise ValueError("local export did not validate the complete prefix")
    equal(summary, expected, "retained full-state local summary")


def validate_unit_matrix(document):
    if not isinstance(document, dict) or document.get("passed") is not True:
        raise ValueError("small correctness matrix did not pass")
    rows = document.get("rows")
    expected = {(p, i, f) for p in POLICIES for i in ("open_addressed", "std_unordered")
                for f in ("Release", "ASan/UBSan")}
    if not isinstance(rows, list) or len(rows) != 8 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("small correctness matrix requires eight explicit rows")
    actual = [(row.get("policy"), row.get("reference_index"), row.get("profile")) for row in rows]
    if any(row.get("passed") is not True for row in rows) or len(set(actual)) != 8 or set(actual) != expected:
        raise ValueError("small correctness matrix is incomplete or duplicated")


def validate_tested_tools(document, builds):
    """Measured files must be the exact Release/flat files in the unit matrix."""
    validate_unit_matrix(document)
    for policy in POLICIES:
        row = next(row for row in document["rows"] if (row["policy"], row["reference_index"], row["profile"])
                   == (policy, "open_addressed", "Release"))
        for current, original in (("itch_journal_replay", "itch_journal_replay"),
                                  ("itch_storage_bench", "itch_storage_bench"), ("independent_l3_local", "helper")):
            require_reference(row["binaries"][original], builds[policy]["binaries"][current])
        require_reference(row["cache"], builds[policy]["cache"])
        require_reference(row["compile_commands"], builds[policy]["compile_commands"])


def distinct_exports(actual, retained):
    """Fresh export roles cannot reuse retained files or each other's inodes."""
    occupied = set()
    for ref in retained:
        info = Path(ref["path"]).lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("retained export role is not a regular file")
        occupied.add((info.st_dev, info.st_ino))
    for ref in actual:
        info = Path(ref["path"]).lstat()
        inode = (info.st_dev, info.st_ino)
        if not stat.S_ISREG(info.st_mode) or inode in occupied:
            raise ValueError("fresh export aliases a retained or another actual export")
        occupied.add(inode)


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def checked_bytes(path, maximum, expected_inode=None):
    """Read a regular file through one nonblocking descriptor and stable path."""
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb", buffering=0) as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_size > maximum or
                (expected_inode is not None and (before.st_dev, before.st_ino) != expected_inode)):
            raise ValueError(f"nonregular, changed or oversized file: {path}")
        data = stream.read(maximum + 1)
        if len(data) > maximum or len(data) != before.st_size or stamp(os.fstat(stream.fileno())) != stamp(before):
            raise ValueError(f"file changed during bounded read: {path}")
    if stamp(path.stat(follow_symlinks=False)) != stamp(before):
        raise ValueError(f"file path changed during bounded read: {path}")
    return data, stamp(before)


class Inputs:
    """Protected identities; only the two full raw files use streaming hashing."""
    def __init__(self):
        self.entries = {}

    def read(self, path, maximum=MAX_METADATA):
        path = Path(path).absolute()
        blob, identity = checked_bytes(path, maximum)
        ref = {"path": str(path), "bytes": len(blob), "sha256": digest(blob)}
        self.remember(path, identity, ref, False)
        return blob, ref

    def remember(self, path, identity, ref, raw):
        previous = self.entries.get(str(path))
        entry = (path, identity, ref, raw)
        if previous is not None and previous != entry:
            raise ValueError(f"protected input identity changed: {path}")
        self.entries[str(path)] = entry

    def file(self, path, maximum=1 << 30, raw=False):
        path = Path(path).absolute()
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb", buffering=0) as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
                raise ValueError(f"nonregular or oversized identified file: {path}")
            hashed = hashlib.sha256()
            count = 0
            while True:
                block = stream.read(8 << 20)
                if not block:
                    break
                count += len(block)
                if count > maximum:
                    raise ValueError("identified file exceeds its byte bound")
                hashed.update(block)
            if count != before.st_size or stamp(os.fstat(stream.fileno())) != stamp(before):
                raise ValueError(f"identified file changed during hashing: {path}")
        if stamp(path.stat(follow_symlinks=False)) != stamp(before):
            raise ValueError(f"identified path changed during hashing: {path}")
        ref = {"path": str(path), "bytes": count, "sha256": hashed.hexdigest()}
        self.remember(path, stamp(before), ref, raw)
        return ref

    def reference(self, ref, maximum=MAX_METADATA):
        require_reference(ref, ref)
        blob, actual = self.read(ref["path"], maximum)
        require_reference(actual, ref)
        return blob

    def stable(self, full_raw=False):
        for path, identity, ref, raw in list(self.entries.values()):
            if stamp(path.stat(follow_symlinks=False)) != identity:
                raise ValueError(f"protected file metadata changed: {path}")
            if raw and not full_raw:
                continue
            if raw:
                actual = self.file(path, maximum=ref["bytes"], raw=True)
            else:
                actual = self.file(path, maximum=max(ref["bytes"], 1))
            require_reference(actual, ref)


def output_inode(path):
    info = path.lstat()
    return (info.st_dev, info.st_ino) if stat.S_ISREG(info.st_mode) else None


def remove_owned(path, inode):
    try:
        if output_inode(path) == inode:
            path.unlink()
    except FileNotFoundError:
        pass


def publish_success(path, document, guard):
    """Exclusive checked publication; never leave owned success after a guard fails."""
    path = Path(path)
    payload = (json.dumps(document, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    if len(payload) > MAX_REPORT:
        raise ValueError("aggregate report exceeds its publication byte bound")
    inode = None
    try:
        with path.open("xb") as stream:
            info = os.fstat(stream.fileno())
            inode = (info.st_dev, info.st_ino)
            if stream.write(payload) != len(payload):
                raise OSError("short aggregate write")
            stream.flush()
        readback, _ = checked_bytes(path, MAX_REPORT, inode)
        if readback != payload:
            raise ValueError("aggregate readback differs")
        guard()
        readback, _ = checked_bytes(path, MAX_REPORT, inode)
        if readback != payload:
            raise ValueError("aggregate changed during final guards")
        return inode
    except BaseException:
        if inode is not None:
            remove_owned(path, inode)
        raise


def git_blob(path, revision):
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{revision}:{path}"],
                            capture_output=True, timeout=30, check=False)
    if result.returncode != 0 or result.stderr or len(result.stdout) > MAX_METADATA:
        raise ValueError("accepted Git blob is missing or exceeds its bound")
    return result.stdout


def accepted(path, expected_sha, inputs):
    current, ref = inputs.read(ROOT / path)
    if ref["sha256"] != expected_sha:
        raise ValueError(f"accepted evidence digest changed: {path}")
    if current != git_blob(path, DESIGN_COMMIT) or current != git_blob(path, "HEAD"):
        raise ValueError(f"accepted historical/current Git evidence differs: {path}")
    return current, ref


def trusted_metadata(inputs):
    blob, design_ref = accepted(DESIGN_PATH, DESIGN_SHA, inputs)
    design = base.strict_json(blob)
    _, contract_ref = accepted("docs/LEVEL_SEARCH.md", CONTRACT_SHA, inputs)
    if design.get("status") != "approved_design_only" or design.get("gate") != 17:
        raise ValueError("unexpected accepted design status")
    inherited = {}
    for path, ref in design["inherited_records"].items():
        if path not in {"docs/STORAGE.md", "docs/validation/2026-10-22-storage/comparison.json",
                "docs/validation/2026-10-22-storage/build-info.txt", "docs/validation/2026-10-22-l3/canonical.json",
                "docs/validation/2026-10-22-l3/verification.json",
                "docs/validation/2026-10-23-l3-transitions/verification.json"}:
            raise ValueError("unexpected inherited record role")
        if ref["path"] != f"itch-feed-handler/{path}":
            raise ValueError("inherited record path does not match its role")
        data, actual = accepted(path, ref["sha256"], inputs)
        if len(data) != ref["bytes"]:
            raise ValueError("inherited record byte extent changed")
        inherited[path] = base.strict_json(data) if path.endswith(".json") else None
    old = inherited["docs/validation/2026-10-22-storage/comparison.json"]
    expected_raw = [{"case": case, "fit_orders": CASES[case]["fit_orders"],
        "path": str(CASES[case]["path"]), "bytes": CASES[case]["bytes"], "sha256": CASES[case]["sha256"]}
        for case in CASES]
    equal(old["inputs"], expected_raw, "accepted Gate3 raw identities")
    equal(design["inherited_raw_identities_metadata_only"], expected_raw, "design raw identities")
    if old.get("passed") is not True:
        raise ValueError("accepted previous full-day experiment did not pass")
    earlier = inherited["docs/validation/2026-10-22-l3/canonical.json"]
    later = inherited["docs/validation/2026-10-23-l3-transitions/verification.json"]
    if earlier.get("passed") is not True or later.get("passed") is not True:
        raise ValueError("retained independent L3 records did not pass")
    selection_blob = inputs.reference(later["selection"])
    selection = base.strict_json(selection_blob)
    checkpoint20 = selection["artifacts"]["checkpoints"]
    requests20 = {"path": str(ROOT / "out/l3-transition-verification-v3/selection/checkpoints.csv"),
                  "bytes": checkpoint20["bytes"], "sha256": checkpoint20["sha256"]}
    references = {
        15: {"requests": earlier["checkpoints"],
             "reference_orders": earlier["artefacts"]["reference.orders.csv"],
             "expected_local_summary": earlier["artefacts"]["local.summary.json"]},
        20: {"requests": requests20,
             "reference_orders": later["artifacts"]["reference-1"]["orders"],
             "expected_local_summary": later["artifacts"]["local-1"]["summary"]},
    }
    # The authenticated records must still describe these fixed retained roles.
    for count, roles in references.items():
        directory = ROOT / ("out/l3-canonical-v2" if count == 15 else "out/l3-transition-verification-v3")
        expected_names = ({"requests": "checkpoints.csv", "reference_orders": "reference.orders.csv",
                           "expected_local_summary": "local.summary.json"} if count == 15 else
                          {"requests": "selection/checkpoints.csv", "reference_orders": "reference-1.orders.csv",
                           "expected_local_summary": "local-1.summary.json"})
        for role, ref in roles.items():
            if ref["path"] != str(directory / expected_names[role]):
                raise ValueError("retained export role/path differs from the accepted request set")
            data = inputs.reference(ref)
            if role == "expected_local_summary":
                summary = base.strict_json(data)
                end = 273665559 if count == 15 else 284563784
                if len(summary.get("states", [])) != count or summary.get("consumed_prefix_bytes") != end:
                    raise ValueError("retained request count or prefix extent differs")
    old_states = {}
    for case in CASES:
        rows = [r for r in old["correctness"] if r["case"] == case and r["profile"] == "default"
                and r["reference_index"] == "open_addressed"]
        if len(rows) != 1:
            raise ValueError("accepted full-day correctness baseline is ambiguous")
        cap, levels = capacities(case, "default")
        old_states[case] = base.semantic(rows[0]["summary"], CASES[case]["bytes"], "open_addressed", cap, levels)
    helper = design["inspected_private_harness"]["independent_l3_local.cpp"]
    helper = dict(helper, path=str(WORK / helper["path"]))
    inputs.reference(helper)
    return {"design": design_ref, "contract": contract_ref, "retained": references,
            "old_states": old_states, "helper_source": helper}


def clean_snapshot(path, inputs):
    snapshot = base.source_snapshot(path)
    if snapshot.get("git_dirty") is not False or (base.git(path, "branch", "--show-current") or "").strip() != "main":
        raise ValueError("measurement requires unchanged clean main checkouts")
    for name, expected in snapshot["file_sha256"].items():
        _, ref = inputs.read(path / name, 1 << 20)
        if ref["sha256"] != expected:
            raise ValueError("implementation changed while source identity was captured")
    return snapshot


def normalise(value, build_root):
    return value.replace(str(build_root), "<BUILD>").replace("-DITCH_BINARY_LEVEL_SEARCH=0",
        "-DITCH_BINARY_LEVEL_SEARCH=<POLICY>").replace("-DITCH_BINARY_LEVEL_SEARCH=1",
        "-DITCH_BINARY_LEVEL_SEARCH=<POLICY>")


def required_compile_sources():
    return {str(ROOT / name) for name in ("src/book.cpp", "src/framing.cpp", "src/replay.cpp",
        "src/journal.cpp", "tools/journal_replay.cpp", "tools/storage_bench.cpp")} | {
        str(WORK / "itch-feed-handler-tests/independent_l3_local.cpp"),
        str(ENGINE / "src/book.cpp"), str(ENGINE / "src/book_v1.cpp")}


def validate_compile_coverage(compiled):
    if not required_compile_sources().issubset(compiled):
        raise ValueError("compiler database lacks core, engine, tool or unchanged retained-state helper commands")


def build_metadata(directory, policy, inputs):
    """Validate actual Makefile/compile DB/link metadata, including nested builds."""
    directory = directory.resolve(strict=True)
    cache_path = next((p for p in (directory / "CMakeCache.txt", directory.parent / "CMakeCache.txt")
                       if p.is_file()), None)
    if cache_path is None:
        raise ValueError("Release build cache is required")
    raw, cache_ref = inputs.read(cache_path)
    build_root = cache_path.parent
    values = {}
    for line in raw.decode("utf-8").splitlines():
        if line and not line.startswith(("#", "//")) and ":" in line and "=" in line:
            key, value = line.split("=", 1)
            key = key.split(":", 1)[0]
            if key in values:
                raise ValueError("duplicate CMake cache key")
            values[key] = value
    if (values.get("CMAKE_BUILD_TYPE") != "Release" or values.get("ITCH_LEVEL_SEARCH") != policy or
            values.get("ITCH_REFERENCE_INDEX") != "open_addressed" or
            values.get("ITCH_SANITIZE", "OFF").upper() not in {"OFF", "FALSE", "0"}):
        raise ValueError("measured cache must select Release, fixed flat index and requested level search")
    dependency = values.get("FETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE") or values.get("matching_engine_SOURCE_DIR")
    if not dependency or Path(dependency).resolve(strict=True) != ENGINE.resolve(strict=True):
        raise ValueError("both builds must use the fixed local matching-engine checkout")
    compiler = Path(values.get("CMAKE_CXX_COMPILER", "")).resolve(strict=True)
    compiler_ref = inputs.file(compiler)
    flags_blob, flags_ref = inputs.read(directory / "CMakeFiles/itch.dir/flags.make")
    flags_text = flags_blob.decode("utf-8")
    definitions = next((line.split("=", 1)[1].strip() for line in flags_text.splitlines()
                        if line.startswith("CXX_DEFINES =")), None)
    flags = next((line.split("=", 1)[1].strip() for line in flags_text.splitlines()
                  if line.startswith("CXX_FLAGS =")), None)
    if definitions is None or flags is None:
        raise ValueError("generated core flags are missing")
    validate_definitions(policy, shlex.split(definitions))
    reject_sanitizers(shlex.split(flags_text.replace("\n", " ")))
    reject_sanitizers([values.get(key, "") for key in values if "FLAGS" in key])
    database_path = build_root / "compile_commands.json"
    database_blob, database_ref = inputs.read(database_path)
    # strict_json's duplicate-key/numeric checks also apply to this array wrapper.
    database = base.strict_json(b'{"rows":' + database_blob + b'}')["rows"]
    required = required_compile_sources()
    consumers = {name for name in required if ENGINE not in Path(name).parents}
    compiled = {}
    for row in database:
        if not isinstance(row, dict) or not isinstance(row.get("file"), str):
            raise ValueError("invalid actual compiler database row")
        filename = str(Path(row["file"]).resolve(strict=True))
        args = row.get("arguments") if "arguments" in row else shlex.split(row.get("command", ""))
        if not isinstance(args, list) or not args or any(not isinstance(token, str) for token in args):
            raise ValueError("invalid actual compiler command")
        # Engine library commands also participate in the matched flag comparison;
        # generic engine/Mold units need not carry the L3 consumer's definitions.
        engine_unit = (ENGINE in Path(filename).parents and any("CMakeFiles/me.dir/" in x for x in args))
        if filename not in required and not engine_unit:
            continue
        if filename in compiled:
            raise ValueError("duplicate measured compiler database translation unit")
        reject_sanitizers(args)
        if filename in consumers:
            validate_definitions(policy, args)
        if Path(args[0]).resolve(strict=True) != compiler or "-O3" not in args or "-DNDEBUG" not in args:
            raise ValueError("actual commands must use the identified Release compiler/optimisation")
        if any(re.fullmatch(r"-O(?:[0-9sgz]|fast)", arg) and arg != "-O3" for arg in args):
            raise ValueError("conflicting actual optimisation flags")
        inputs.read(Path(filename), 1 << 20)
        compiled[filename] = {"directory": row["directory"], "arguments": args}
    validate_compile_coverage(compiled)
    links, binaries = {}, {}
    for role in ("itch_journal_replay", "itch_storage_bench", "independent_l3_local"):
        role_directory = build_root if role == "independent_l3_local" else directory
        link_path = role_directory / "CMakeFiles" / f"{role}.dir/link.txt"
        data, link_ref = inputs.read(link_path)
        tokens = shlex.split(data.decode("utf-8"))
        reject_sanitizers(tokens)
        if not tokens or Path(tokens[0]).resolve(strict=True) != compiler:
            raise ValueError("actual linker command uses a different compiler")
        archives = [Path(token) for token in tokens if token.endswith(".a")]
        if not archives:
            raise ValueError("actual tool/helper link command lacks its core archives")
        linked = [p if p.is_absolute() else role_directory / p for p in archives]
        if directory / "libitch.a" not in [p.resolve(strict=True) for p in linked]:
            raise ValueError("actual tool/helper does not link this measured core archive")
        for archive in linked:
            inputs.file(archive.resolve(strict=True))
        links[role] = {"file": link_ref, "arguments": tokens}
        binary_path = role_directory / role
        if not os.access(binary_path, os.X_OK):
            raise ValueError("measured executable is missing or not executable")
        binaries[role] = inputs.file(binary_path)
        if binaries[role]["bytes"] == 0:
            raise ValueError("measured executable is empty")
    comparable_cache = {key: normalise(value, build_root) for key, value in values.items()
                        if key != "ITCH_LEVEL_SEARCH"}
    comparable = {"cache": comparable_cache, "definitions": normalise(definitions, build_root),
        "flags": normalise(flags, build_root),
        "compile": {key: {"directory": normalise(row["directory"], build_root),
                          "arguments": [normalise(token, build_root) for token in row["arguments"]]}
                    for key, row in compiled.items()},
        "link": {key: [normalise(token, build_root) for token in row["arguments"]]
                 for key, row in links.items()}}
    return {"tool_directory": str(directory), "build_root": str(build_root), "cache": cache_ref,
        "cache_values": values, "generated_flags": flags_ref, "definitions": definitions, "flags": flags,
        "compile_commands": database_ref, "actual_compile_commands": compiled, "actual_link_commands": links,
        "compiler": compiler_ref, "binaries": binaries}, comparable


def accepted_prerequisites(inputs, snapshots, builds):
    """A reviewed, committed receipt authorises the finite prerequisite evidence.

    File hashes supplied by an arbitrary proof are insufficient authority. This
    fixed current-HEAD document binds the original C++ matrix and the separately
    reviewed Python-only follow-up without relabelling the original source snapshot.
    """
    blob, ref = inputs.read(ROOT / ACCEPTANCE_PATH, 1 << 20)
    if blob != git_blob(ACCEPTANCE_PATH, "HEAD"):
        raise ValueError("prerequisite acceptance must match its committed current HEAD blob")
    document = base.strict_json(blob)
    if set(document) != {"schema_version", "model", "passed", "errors", "source_file_sha256",
            "prerequisite_evidence", "unit_evidence", "execution_receipt", "producer", "measured_binaries", "python_followup"}:
        raise ValueError("unexpected prerequisite acceptance fields")
    if (type(document["schema_version"]) is not int or document["schema_version"] != 1 or
            document["model"] != "level_search_prerequisite_acceptance_v1" or
            document["passed"] is not True or document["errors"] != []):
        raise ValueError("committed prerequisite acceptance did not pass")
    equal(document["source_file_sha256"], {key: value["file_sha256"] for key, value in snapshots.items()},
          "committed accepted implementation")
    equal(document["measured_binaries"], {policy: builds[policy]["binaries"] for policy in POLICIES},
          "committed accepted measured executables")
    if document["producer"]["path"] != str(WORK / "itch-feed-handler-tests/record_level_search_prerequisites.py"):
        raise ValueError("prerequisite recorder identity has an unexpected role/path")
    inputs.reference(document["producer"])
    unit = base.strict_json(inputs.reference(document["unit_evidence"]))
    if (type(unit.get("schema_version")) is not int or unit["schema_version"] != 1 or
            unit.get("model") != "level_search_unit_matrix_v1" or unit.get("errors") != []):
        raise ValueError("accepted original unit matrix has an unexpected version/status")
    validate_tested_tools(unit, builds)
    followup = base.strict_json(inputs.reference(document["python_followup"]))
    if (type(followup.get("schema_version")) is not int or followup["schema_version"] != 1 or
            followup.get("model") != "level_search_python_followup_v1" or followup.get("passed") is not True or
            followup.get("errors") != [] or followup.get("allowed_public_source_changes") != ["bench/compare_level_search.py"] or
            followup.get("original_methods_unchanged") is not True or followup.get("runner_controls_passed") is not True):
        raise ValueError("accepted Python-only follow-up did not pass its fixed scope")
    require_reference(followup["original_unit_aggregate"], document["unit_evidence"])
    for role in ("original_runner", "current_runner"):
        inputs.reference(followup[role])
    if followup["current_runner"]["path"] != str(ROOT / "bench/compare_level_search.py"):
        raise ValueError("Python follow-up current runner path differs")
    source_maps = unit.get("source", {})
    if set(source_maps) != {"itch", "engine"}:
        raise ValueError("accepted original unit source coverage differs")
    for label in snapshots:
        original = source_maps[label]["file_sha256"]
        current = snapshots[label]["file_sha256"]
        if set(original) != set(current):
            raise ValueError("unit/current implementation membership differs")
        allowed = {"bench/compare_level_search.py"} if label == "itch" else set()
        changed = {name for name in current if current[name] != original[name]}
        if not changed.issubset(allowed):
            raise ValueError("untested C++/other implementation source changed after original matrix")
        if label == "itch" and (original["bench/compare_level_search.py"] != followup["original_runner"]["sha256"] or
                current["bench/compare_level_search.py"] != followup["current_runner"]["sha256"]):
            raise ValueError("Python-only source transition differs from its accepted follow-up")
    execution = base.strict_json(inputs.reference(document["execution_receipt"]))
    if (type(execution.get("schema_version")) is not int or execution["schema_version"] != 1 or
            execution.get("passed") is not True or execution.get("errors") != []):
        raise ValueError("accepted prerequisite execution did not pass")
    return document, ref, execution


def prerequisites(path, inputs, snapshots, builds, retained):
    acceptance, acceptance_ref, execution = accepted_prerequisites(inputs, snapshots, builds)
    data, proof_ref = inputs.read(path)
    require_reference(proof_ref, acceptance["prerequisite_evidence"])
    proof = base.strict_json(data)
    if set(proof) != {"schema_version", "model", "passed", "errors", "source", "inputs", "policies", "exports", "unit_matrix"}:
        raise ValueError("prerequisite evidence has unexpected root fields")
    if (type(proof["schema_version"]) is not int or proof["schema_version"] != 1 or
            proof["model"] != "level_search_prerequisites_v1" or proof["passed"] is not True or proof["errors"] != []):
        raise ValueError("required retained-state/small-matrix prerequisite proof did not pass")
    if set(proof["source"]) != set(snapshots):
        raise ValueError("prerequisite implementation coverage differs")
    for label, snapshot in snapshots.items():
        source = proof["source"][label]
        # Committing the acceptance document changes HEAD without changing code.
        if source.get("path") != snapshot["path"] or source.get("git_dirty") is not False:
            raise ValueError("prerequisite implementation was not recorded from clean fixed checkouts")
        equal(source.get("file_sha256"), snapshot["file_sha256"], "prerequisite implementation files")
    equal(execution.get("source_before"), proof["source"], "accepted prerequisite starting source")
    equal(execution.get("source_after"), proof["source"], "accepted prerequisite ending source")
    if set(proof["inputs"]) != set(CASES) or set(proof["policies"]) != set(POLICIES):
        raise ValueError("prerequisite input/policy coverage differs")
    for case, values in CASES.items():
        expected = {"path": str(values["path"]), "bytes": values["bytes"], "sha256": values["sha256"]}
        require_reference(proof["inputs"][case], expected)
    for policy in POLICIES:
        expected = {"helper": builds[policy]["binaries"]["independent_l3_local"],
            "build_cache": builds[policy]["cache"], "compile_commands": builds[policy]["compile_commands"]}
        equal(proof["policies"][policy], expected, "prerequisite measured helper/build identity")
    exports = proof["exports"]
    if not isinstance(exports, list) or len(exports) != 4:
        raise ValueError("prerequisite proof requires four retained-state exports")
    actual_refs = []
    commands = execution.get("commands")
    if not isinstance(commands, list) or len(commands) != 4:
        raise ValueError("accepted prerequisite execution requires four prefix children")
    for index, (row, (policy, count)) in enumerate(zip(exports, ((p, n) for p in POLICIES for n in (15, 20)))):
        if set(row) != {"policy", "request_set", "requests", "orders", "reference_orders", "summary", "expected_local_summary"}:
            raise ValueError("unexpected prerequisite export fields")
        if row["policy"] != policy or type(row["request_set"]) is not int or row["request_set"] != count:
            raise ValueError("prerequisite exports are missing, reordered or duplicated")
        for role in ("requests", "reference_orders", "expected_local_summary"):
            require_reference(row[role], retained[count][role])
        actual_refs.extend((row["orders"], row["summary"]))
        actual = inputs.reference(row["orders"])
        reference = inputs.reference(row["reference_orders"])
        summary = base.strict_json(inputs.reference(row["summary"]))
        expected = base.strict_json(inputs.reference(row["expected_local_summary"]))
        compare_export(actual, reference, summary, expected)
        inputs.reference(row["requests"])
        command = commands[index]
        expected_command = [builds[policy]["binaries"]["independent_l3_local"]["path"], str(CASES["nasdaq"]["path"]),
                            row["requests"]["path"], row["orders"]["path"], row["summary"]["path"]]
        if (command.get("policy") != policy or type(command.get("request_set")) is not int or command["request_set"] != count or
                command.get("passed") is not True or type(command.get("exit_code")) is not int or command["exit_code"] != 0 or
                command.get("timed_out") is not False):
            raise ValueError("accepted prerequisite process status differs")
        equal(command.get("command"), expected_command, "accepted prerequisite process command")
        for stream in ("stdout", "stderr"):
            if inputs.reference(command[stream]) != b"":
                raise ValueError("accepted prerequisite child produced unexpected diagnostics")
    distinct_exports(actual_refs, [ref for roles in retained.values() for ref in roles.values()])
    unit = proof["unit_matrix"]
    if set(unit) != {"aggregate", "builds", "passed"} or type(unit["builds"]) is not int or unit["builds"] != 8 or unit["passed"] is not True:
        raise ValueError("prerequisite small-build coverage differs")
    require_reference(unit["aggregate"], acceptance["unit_evidence"])
    inputs.reference(unit["aggregate"])
    return {"proof": proof_ref, "committed_acceptance": acceptance_ref,
            "original_unit_matrix": acceptance["unit_evidence"], "python_followup": acceptance["python_followup"],
            "execution_receipt": acceptance["execution_receipt"]}


def host_observation(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=10, check=False)
        if len(result.stdout) + len(result.stderr) > 65536:
            raise ValueError("host observation exceeds its output bound")
        return {"command": command, "exit_code": result.returncode,
                "stdout": result.stdout.decode("utf-8", errors="replace"),
                "stderr": result.stderr.decode("utf-8", errors="replace")}
    except OSError as exc:
        return {"command": command, "unavailable": str(exc)}


def fresh_path(path, directory=False):
    if os.path.lexists(path):
        raise ValueError("output directory/report must be fresh, including dangling symlinks")
    resolved = path.absolute().resolve(strict=False)
    if ROOT / "out" not in resolved.parents:
        raise ValueError("all experiment outputs/reports must be under ignored out/")
    ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", str(resolved)],
                             capture_output=True, timeout=30, check=False)
    if ignored.returncode != 0:
        raise ValueError("experiment output/report is not ignored by Git")
    if directory:
        resolved.mkdir(parents=True)
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reverse-linear-dir", type=Path, required=True)
    parser.add_argument("--binary-dir", type=Path, required=True)
    parser.add_argument("--prerequisite-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Check both original lexical paths before resolving or creating either.
        output = fresh_path(args.output)
        report = fresh_path(args.report)
        if output == report or output in report.parents or report in output.parents:
            raise ValueError("private directory and aggregate report must be separate fresh siblings")
        output.mkdir(parents=True)
        report.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"level-search comparison rejected: {exc}", file=sys.stderr)
        return 1
    evidence = {"schema_version": 1, "model": "price_level_search_comparison_v1", "passed": False,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "errors": [], "checks": {},
        "source_before": {}, "source_after": {}, "inputs": {}, "builds": {}, "correctness": [],
        "memory": [], "timings": [], "execution_order": [], "statistics": [], "paired_ratios": [],
        "protocol": {"reference_index": "open_addressed", "rounds": 6, "checkpoint_every": EVERY,
            "scheduled_full_day_children": 64, "prerequisite_prefix_children": 4, "historical_children_total": 68,
            "pair_order": [list(pair) for pair in PAIRS], "group_order": [list(group) for group in GROUPS],
            "group_rotation": "round modulo four", "timeout_seconds": TIMEOUT, "concurrent_children": 1,
            "fresh_process_per_child": True, "rss_samples_per_configuration": 1,
            "correctness_scope": "sampled ordered fingerprints plus 35 previously independent complete states",
            "timing_scope": "separate constructor, prefaulted mapped-input replay and teardown; final state walks outside replay",
            "rss_scope": "separate streaming whole-process high-water, never subtraction or isolated directory memory"},
        "environment": {"platform": platform.platform(), "python": platform.python_version(),
            "machine": platform.machine(), "processor": platform.processor()},
        "limitations": ["One host and two days; six timings and one streaming RSS sample per configuration.",
            "No new independent historical/reference sample; 35 retained ordered states are reused.",
            "Fingerprint checkpoints omit some directory state and do not certify all intervening inventories.",
            "No cache/thermal/frequency/affinity control, isolated memory, hardware-counter, live latency or fill claim."]}
    inputs = Inputs()
    snapshots = {}
    builds = {}
    completed = False

    def guard(full_raw=False):
        inputs.stable(full_raw)
        for name, snapshot in snapshots.items():
            equal(base.source_snapshot(Path(snapshot["path"])), snapshot, f"unchanged {name} implementation")
            if (base.git(Path(snapshot["path"]), "branch", "--show-current") or "").strip() != "main":
                raise ValueError("source branch changed during experiment")

    try:
        metadata = trusted_metadata(inputs)
        evidence["accepted_design"] = {"commit": DESIGN_COMMIT, "design": metadata["design"], "contract": metadata["contract"]}
        snapshots = {"itch": clean_snapshot(ROOT, inputs), "engine": clean_snapshot(ENGINE, inputs)}
        evidence["source_before"] = snapshots.copy()
        comparable = {}
        for policy, directory in zip(POLICIES, (args.reverse_linear_dir, args.binary_dir)):
            builds[policy], comparable[policy] = build_metadata(directory, policy, inputs)
        equal(comparable[POLICIES[0]], comparable[POLICIES[1]], "actual build flags/commands (only search macro/build paths may differ)")
        for role in ("itch_journal_replay", "itch_storage_bench", "independent_l3_local"):
            if builds[POLICIES[0]]["binaries"][role]["sha256"] == builds[POLICIES[1]]["binaries"][role]["sha256"]:
                raise ValueError("baseline and candidate executable bytes are identical")
        evidence["builds"] = builds
        evidence["prerequisite_evidence"] = prerequisites(args.prerequisite_evidence, inputs, snapshots, builds, metadata["retained"])
        evidence["checks"]["all_eight_small_builds_and_four_exact_independent_exports_passed"] = True
        evidence["checks"]["fixed_index_and_actual_build_commands_verified"] = True
        for case, expected in CASES.items():
            ref = inputs.file(expected["path"], maximum=expected["bytes"], raw=True)
            require_reference(ref, {key: str(value) if key == "path" else value
                                   for key, value in expected.items() if key in ("path", "bytes", "sha256")})
            evidence["inputs"][case] = ref
        compiler = builds[POLICIES[0]]["compiler"]["path"]
        evidence["environment"]["compiler_version"] = host_observation([compiler, "--version"])
        if evidence["environment"]["compiler_version"].get("exit_code") != 0:
            raise ValueError("identified compiler version could not be recorded")
        if sys.platform == "darwin":
            evidence["environment"]["host"] = host_observation(["/usr/sbin/sysctl", "hw.model", "hw.memsize", "hw.ncpu", "machdep.cpu.brand_string"])
            evidence["environment"]["power"] = host_observation(["/usr/bin/pmset", "-g", "batt"])
            evidence["environment"]["thermal_before"] = host_observation(["/usr/bin/pmset", "-g", "therm"])
        else:
            evidence["environment"]["cpu"] = host_observation(["lscpu"])
            evidence["environment"]["ram"] = host_observation(["free", "-b"])
        evidence["environment"]["load_before"] = host_observation(["uptime"])
        baselines = {}
        checkpoint_baselines = {}
        for launch in schedule():
            phase, case, profile, policy = (launch[key] for key in ("phase", "case", "profile", "level_search"))
            # This boundary cannot be reached without complete correctness passes.
            if phase != "correctness" and evidence["checks"].get("all_eight_full_day_correctness_passed") is not True:
                raise ValueError("measurement attempted before complete correctness acceptance")
            cap, level_cap = capacities(case, profile)
            label = f"{len(evidence['execution_order']):03d}-{phase}-{case}-{profile}-{policy}"
            checkpoint = output / f"{label}.csv"
            tool = "itch_journal_replay" if phase == "correctness" else "itch_storage_bench"
            command = [builds[policy]["binaries"][tool]["path"]]
            if phase == "correctness":
                command += ["--raw", "--max-orders", cap, "--checkpoint-every", EVERY, "--checkpoints", checkpoint]
            else:
                if phase == "memory":
                    command += ["--memory"]
                command += ["--max-orders", cap, "--max-levels", level_cap]
            command += [CASES[case]["path"]]
            # Metadata-only raw checks between children; complete hashes are fresh
            # once before the matrix and once after its last child.
            for path, identity, _, raw in inputs.entries.values():
                if raw and stamp(path.stat(follow_symlinks=False)) != identity:
                    raise ValueError("raw input metadata changed between children")
            entry = dict(index=len(evidence["execution_order"]), **launch)
            evidence["execution_order"].append(entry)
            print(f"{label}" + (f" round {launch['round'] + 1}/6" if launch["round"] is not None else ""), flush=True)
            summary = base.run(command, output, label, entry, TIMEOUT)
            for suffix in (".json", ".stderr"):
                inputs.read(output / f"{label}{suffix}", 1 << 20)
            state = policy_summary(summary, CASES[case]["bytes"], policy, cap, level_cap)
            equal(state, metadata["old_states"][case], "accepted full-day semantics")
            row = dict(case=case, profile=profile, level_search=policy, max_orders=cap, max_levels=level_cap, summary=summary)
            if phase == "correctness":
                if (summary.get("format") != "raw" or summary.get("source_sha256", "missing") is not None or
                        summary.get("source_identity_verified") is not False or summary.get("allow_partial") is not False or
                        type(summary.get("journal_blocks")) is not int or summary["journal_blocks"] != 0 or
                        type(summary.get("checkpoint_every")) is not int or summary["checkpoint_every"] != EVERY):
                    raise ValueError("raw correctness replay metadata differs")
                inputs.read(checkpoint, 1 << 20)
                coverage = base.checkpoints(checkpoint, summary, EVERY)
                if coverage["rows"] != CASES[case]["checkpoints"] or coverage["nonempty_book_rows"] != CASES[case]["nonempty"]:
                    raise ValueError("populated complete checkpoint coverage differs")
                if case in checkpoint_baselines and coverage["sha256"] != checkpoint_baselines[case]:
                    raise ValueError("ordered checkpoint CSV differs across search/capacity configurations")
                checkpoint_baselines[case] = coverage["sha256"]
                baselines[case] = state
                if CASES[case]["fit_orders"] < summary["peak_orders"]:
                    raise ValueError("fitted capacity has no observed-order headroom")
                row["checkpoints"] = coverage
                evidence["correctness"].append(row)
                if len(evidence["correctness"]) == 8:
                    evidence["checks"]["all_eight_full_day_correctness_passed"] = True
            else:
                base.validate_benchmark(summary, phase, entry["wall_seconds"])
                equal(state, baselines[case], "benchmark/correctness replay semantics")
                if phase == "timing":
                    row["round"] = launch["round"]
                    evidence["timings"].append(row)
                else:
                    evidence["memory"].append(row)
        check_schedule(evidence["execution_order"])
        if len(evidence["memory"]) != 8 or len(evidence["timings"]) != 48 or any(row.get("passed") is not True for row in evidence["execution_order"]):
            raise ValueError("requested fresh-process measurement matrix is incomplete")
        for case, profile in GROUPS:
            for policy in POLICIES:
                rows = [row["summary"] for row in evidence["timings"] if
                        (row["case"], row["profile"], row["level_search"]) == (case, profile, policy)]
                if len(rows) != 6:
                    raise ValueError("six timing repetitions per configuration are required")
                evidence["statistics"].append(dict(case=case, profile=profile, level_search=policy,
                    **{stage: {"values": [row[stage] for row in rows], **base.distribution([row[stage] for row in rows])}
                       for stage in base.STAGES}))
            ratios = []
            for round_index in range(6):
                pair = {row["level_search"]: row["summary"]["replay_seconds"] for row in evidence["timings"]
                        if (row["case"], row["profile"], row["round"]) == (case, profile, round_index)}
                ratio = pair["binary"] / pair["reverse_linear"]
                if not math.isfinite(ratio) or ratio <= 0:
                    raise ValueError("invalid paired candidate/baseline ratio")
                ratios.append(ratio)
            evidence["paired_ratios"].append(dict(case=case, profile=profile, interpretation="binary/reverse_linear; less than one is faster",
                values=ratios, pair_orders=[list(pair) for pair in PAIRS], **base.distribution(ratios)))
        evidence["environment"]["load_after"] = host_observation(["uptime"])
        if sys.platform == "darwin":
            evidence["environment"]["power_after"] = host_observation(["/usr/bin/pmset", "-g", "batt"])
            evidence["environment"]["thermal_after"] = host_observation(["/usr/bin/pmset", "-g", "therm"])
        evidence["checks"]["all_64_children_complete_in_frozen_order"] = True
        completed = True
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, UnicodeError, csv.Error, subprocess.SubprocessError) as exc:
        evidence["errors"].append(f"comparison failed: {type(exc).__name__}: {exc}")
    try:
        guard(full_raw=True)
        evidence["source_after"] = {name: base.source_snapshot(Path(value["path"])) for name, value in snapshots.items()}
        evidence["checks"]["protected_files_sources_and_full_raw_hashes_unchanged"] = bool(snapshots)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        evidence["errors"].append(f"final identity guard failed: {type(exc).__name__}: {exc}")
        evidence["checks"]["protected_files_sources_and_full_raw_hashes_unchanged"] = False
    evidence["protected_inputs"] = [entry[2] for _, entry in sorted(inputs.entries.items())]
    evidence["passed"] = completed and not evidence["errors"] and all(value is True for value in evidence["checks"].values())
    published_inode = None
    try:
        published_inode = publish_success(report, evidence, guard if evidence["passed"] else lambda: None)
        print(f"{'PASS' if evidence['passed'] else 'FAIL'}: {report}", flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        # Publication failures retain private child logs and a separate failure,
        # but no owned apparently successful aggregate.
        if published_inode is not None:
            remove_owned(report, published_inode)
        evidence["passed"] = False
        evidence["errors"].append(f"publication failed: {type(exc).__name__}: {exc}")
        failure = output / "failure.json"
        if not os.path.lexists(failure):
            publish_success(failure, evidence, lambda: None)
        print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
