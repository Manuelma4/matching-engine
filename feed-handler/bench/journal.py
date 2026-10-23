#!/usr/bin/env python3
"""Create and verify deterministic journals of observed Nasdaq BinaryFILE bytes.

The container preserves the input exactly, including unknown messages or malformed
wire framing. Protocol and book validation are separate replay responsibilities.
Each invocation writes one aggregate JSON object to stdout and exits zero only
after full verification. No market-data payload is printed.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import zlib


MAGIC = b"ITCHJNL\x00"
FOOTER_MAGIC = b"ITCHEND\x00"
VERSION = 1
BLOCK_LIMIT = 1 << 20
FLAGS = 1  # Observed Nasdaq BinaryFILE / TotalView-ITCH 5.0 wire bytes.
HEADER = struct.Struct(">8sHHII12s")
DATA = struct.Struct(">4sIQII")
FOOTER = struct.Struct(">8sQQ32sIIII")
FORMAT = "itch-observed-wire-journal"


class JournalError(ValueError):
    """The journal does not satisfy its versioned container contract."""


def identity(info):
    """Exclude access time: reading a file may legitimately update it."""
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def regular_file(stream, label):
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode):
        raise JournalError(f"{label} must be a regular file")
    return info


def open_regular(path, label):
    # O_NONBLOCK prevents a named pipe from waiting for a peer before fstat can
    # reject it. It has no effect on ordinary regular-file reads.
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise JournalError(f"{label} must be a regular file")
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise


def crc32(data, previous=0):
    return zlib.crc32(data, previous) & 0xffffffff


def verify(path):
    """Verify canonical packing and SHA-256 identity without decoding messages.

    Success fields are deliberately aggregate: schema_version, operation, passed,
    format, version, block_payload_limit, source_bytes, source_sha256, blocks,
    journal_bytes, journal_sha256, prefix_crc32, footer_crc32, canonical_packing,
    source_identity_verified, input_identity_stable, journal and errors.
    """
    path = Path(path).resolve(strict=True)
    with open_regular(path, "journal") as stream:
        before = regular_file(stream, "journal")
        journal_hash = hashlib.sha256()
        source_hash = hashlib.sha256()
        journal_bytes = 0

        def read_exact(length, label):
            nonlocal journal_bytes
            value = stream.read(length)
            journal_hash.update(value)
            journal_bytes += len(value)
            if len(value) != length:
                raise JournalError(f"truncated {label}")
            return value

        header = read_exact(HEADER.size, "journal header")
        magic, version, header_bytes, block_limit, flags, reserved = HEADER.unpack(header)
        if magic != MAGIC or version != VERSION or header_bytes != HEADER.size:
            raise JournalError("unsupported journal magic, version or header length")
        if block_limit != BLOCK_LIMIT or flags != FLAGS or reserved != b"\x00" * 12:
            raise JournalError("noncanonical block limit, flags or header reserved bytes")
        prefix_crc = crc32(header)
        source_bytes = blocks = 0
        previous_size = None
        while True:
            tag = read_exact(4, "DATA header or footer")
            if tag == b"DATA":
                if previous_size is not None and previous_size != BLOCK_LIMIT:
                    raise JournalError("a short DATA block must be the final DATA block")
                data_header = tag + read_exact(DATA.size - 4, "DATA header")
                _, payload_size, source_offset, payload_crc, reserved = DATA.unpack(data_header)
                if not 1 <= payload_size <= BLOCK_LIMIT or reserved != 0:
                    raise JournalError("invalid DATA payload length or reserved field")
                if source_offset != source_bytes:
                    raise JournalError("DATA source offset is not consecutive")
                payload = read_exact(payload_size, "DATA payload")
                if crc32(payload) != payload_crc:
                    raise JournalError("DATA payload CRC-32 mismatch")
                prefix_crc = crc32(data_header, prefix_crc)
                prefix_crc = crc32(payload, prefix_crc)
                source_hash.update(payload)
                source_bytes += payload_size
                blocks += 1
                previous_size = payload_size
                continue
            if tag != FOOTER_MAGIC[:4]:
                raise JournalError("unexpected record tag; a DATA record or footer is required")
            footer = tag + read_exact(FOOTER.size - 4, "journal footer")
            (magic, expected_bytes, expected_blocks, expected_sha256, expected_prefix_crc,
             reserved1, expected_footer_crc, reserved2) = FOOTER.unpack(footer)
            if magic != FOOTER_MAGIC or reserved1 != 0 or reserved2 != 0:
                raise JournalError("invalid footer magic or reserved fields")
            if crc32(footer[:64]) != expected_footer_crc:
                raise JournalError("footer CRC-32 mismatch")
            if prefix_crc != expected_prefix_crc:
                raise JournalError("journal prefix CRC-32 mismatch")
            if blocks == 0 or source_bytes == 0:
                raise JournalError("journal must contain at least one nonempty DATA block")
            if expected_bytes != source_bytes or expected_blocks != blocks:
                raise JournalError("footer source-byte or block count mismatch")
            if source_hash.digest() != expected_sha256:
                raise JournalError("observed source SHA-256 does not match the footer")
            if stream.read(1):
                raise JournalError("trailing bytes after the mandatory footer")
            if identity(os.fstat(stream.fileno())) != identity(before):
                raise JournalError("journal changed during verification")
            if journal_bytes != before.st_size:
                raise JournalError("journal byte count does not match its regular-file size")
            return {"schema_version": 1, "operation": "verify", "passed": True,
                "format": FORMAT, "version": VERSION, "block_payload_limit": BLOCK_LIMIT,
                "source_bytes": source_bytes, "source_sha256": source_hash.hexdigest(),
                "blocks": blocks, "journal_bytes": journal_bytes,
                "journal_sha256": journal_hash.hexdigest(), "prefix_crc32": f"{prefix_crc:08x}",
                "footer_crc32": f"{expected_footer_crc:08x}", "canonical_packing": True,
                "source_identity_verified": True, "input_identity_stable": True,
                "journal": str(path), "errors": []}


def remove_owned_output(path, owned):
    """Never remove another process's replacement for our failed output."""
    if owned is None:
        return
    try:
        current = path.lstat()
        if (current.st_dev, current.st_ino) == owned:
            path.unlink()
    except FileNotFoundError:
        pass


def create(input_path, output_path):
    """Write fixed byte blocks, then independently verify the completed file.

    Binary output contains no paths, clocks or process-specific metadata. A failed
    creation removes only the fresh file owned by this invocation. A crash may
    leave a partial file, which mandatory footer verification will reject.
    """
    input_path = Path(input_path).resolve(strict=True)
    requested_output = Path(output_path).absolute()
    # Resolve the parent, preserving the leaf: exclusive creation must reject an
    # existing dangling symlink as well as an existing ordinary output file.
    output_path = requested_output.parent.resolve(strict=True) / requested_output.name
    owned = None
    with open_regular(input_path, "raw input") as source:
        before = regular_file(source, "raw input")
        if before.st_size == 0:
            raise JournalError("raw input must contain at least one observed byte")
        source_hash = hashlib.sha256()
        source_bytes = blocks = 0
        try:
            with output_path.open("xb") as output:
                info = os.fstat(output.fileno())
                owned = (info.st_dev, info.st_ino)

                def write_all(data):
                    if output.write(data) != len(data):
                        raise OSError("short journal write")

                header = HEADER.pack(MAGIC, VERSION, HEADER.size, BLOCK_LIMIT, FLAGS, b"\x00" * 12)
                write_all(header)
                prefix_crc = crc32(header)
                while payload := source.read(BLOCK_LIMIT):
                    data_header = DATA.pack(b"DATA", len(payload), source_bytes, crc32(payload), 0)
                    write_all(data_header)
                    write_all(payload)
                    prefix_crc = crc32(data_header, prefix_crc)
                    prefix_crc = crc32(payload, prefix_crc)
                    source_hash.update(payload)
                    source_bytes += len(payload)
                    blocks += 1
                if identity(os.fstat(source.fileno())) != identity(before) or source_bytes != before.st_size:
                    raise JournalError("raw input changed during journal creation")
                footer_prefix = struct.pack(">8sQQ32sII", FOOTER_MAGIC, source_bytes, blocks,
                    source_hash.digest(), prefix_crc, 0)
                write_all(footer_prefix + struct.pack(">II", crc32(footer_prefix), 0))
                output.flush()
                os.fsync(output.fileno())
            report = verify(output_path)
            if identity(os.fstat(source.fileno())) != identity(before):
                raise JournalError("raw input changed before journal verification completed")
            if report["source_bytes"] != source_bytes or report["source_sha256"] != source_hash.hexdigest():
                raise JournalError("verified journal does not match the observed input bytes")
            report.update(operation="create", input=str(input_path))
            return report
        except BaseException:
            remove_owned_output(output_path, owned)
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    creator = subparsers.add_parser("create", help="create a fresh deterministic journal and verify it")
    creator.add_argument("input", type=Path, help="nonempty regular raw file; no protocol normalisation")
    creator.add_argument("output", type=Path, help="new output file in an existing directory")
    verifier = subparsers.add_parser("verify", help="verify container structure, CRC-32 and source SHA-256")
    verifier.add_argument("journal", type=Path)
    args = parser.parse_args(argv)
    try:
        report = create(args.input, args.output) if args.operation == "create" else verify(args.journal)
    except (OSError, ValueError, RuntimeError, zlib.error) as exc:
        report = {"schema_version": 1, "operation": args.operation, "passed": False,
            "format": FORMAT, "version": VERSION, "errors": [f"{type(exc).__name__}: {exc}"]}
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
