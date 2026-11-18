#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Translate Devin CLI file events into one shared hook invocation per target."""

import json
import subprocess
import sys
from pathlib import Path


HANDLERS = {"guard-path.sh", "guard-config.sh", "post-tool-use.sh",
            "governance-capture.sh", "test-cohesion.sh"}
GUARDS = {"guard-config.sh", "guard-path.sh"}
PATCH_HEADERS = ("*** Add File: ", "*** Update File: ", "*** Delete File: ")


def file_path(value: object) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(c) < 32 for c in value)):
        raise ValueError("expected a file path")
    return value


def patch_inputs(patch: str):
    """Recognize the CLI's patch headers at column zero. Body lines have a prefix."""
    lines = patch.replace("\r\n", "\n").strip("\n").split("\n")
    if lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("expected Devin patch envelope")
    targets: list[str] = []
    body: list[str] = []
    for line in lines[1:-1]:
        if line.startswith(PATCH_HEADERS):
            for target in targets:
                yield {"file_path": target, "content": "\n".join(body)}
            targets = [file_path(line.partition(": ")[2])]
            body = []
        elif line.startswith("*** Move to: ") and targets:
            targets.append(file_path(line.removeprefix("*** Move to: ")))
        elif targets and (line.startswith((" ", "+", "-", "@@")) or line == "*** End of File"):
            body.append(line)
        else:
            raise ValueError("unrecognized Devin patch section")
    if not targets:
        raise ValueError("expected patch file headers")
    for target in targets:
        yield {"file_path": target, "content": "\n".join(body)}


def file_inputs(tool: str, args: object):
    if tool == "apply_patch":
        patch = args if isinstance(args, str) else None
        if isinstance(args, dict):
            fields = [args[key] for key in ("input", "patch") if key in args]
            if len(fields) == 1:
                patch = fields[0]
        if not isinstance(patch, str):
            raise ValueError("expected patch text")
        return patch_inputs(patch)
    if not isinstance(args, dict):
        raise ValueError("expected tool arguments")
    if tool in ("grep", "glob"):
        # The search root is optional. Its default is the working directory.
        root = file_path(args.get("path") or ".")
        pattern = args.get("pattern")
        if tool == "glob" and isinstance(pattern, str) and Path(pattern).is_absolute():
            return [{"file_path": root}, {"file_path": file_path(pattern)}]
        return [{"file_path": root}]
    path = args.get("notebook_path") if tool.startswith("notebook_") else None
    return [{**args, "file_path": file_path(path or args.get("file_path") or args.get("path"))}]


def run(handler: str, payload: dict) -> int:
    if not isinstance(payload, dict) or not isinstance(payload.get("tool_name"), str):
        raise ValueError("expected a Devin tool event")
    response = payload.get("tool_response")
    if handler not in GUARDS and isinstance(response, dict) and response.get("success") is False:
        return 0
    tool = payload["tool_name"]
    command = ["bash", str(Path(__file__).with_name(handler))]
    contexts = []
    metadata = {key: payload[key] for key in ("hook_event_name", "session_id", "cwd", "prompt_id")
                if key in payload}
    # Validate the complete patch before reporting any of its files as changed.
    inputs = list(file_inputs(tool, payload["tool_input"]))
    for arguments in inputs:
        # governance-capture classifies edits using the shared hook names.
        name = "Edit" if handler == "governance-capture.sh" else tool
        # Only config protection examines edits. Observers receive the path,
        # without the original diff, file contents or tool response.
        fields = arguments if handler == "guard-config.sh" else {"file_path": arguments["file_path"]}
        event = {**metadata, "tool_name": name, "tool_input": fields}
        result = subprocess.run(command, input=json.dumps(event), text=True, stdout=subprocess.PIPE)
        if result.returncode or handler != "post-tool-use.sh":
            sys.stdout.write(result.stdout)
        elif result.stdout.strip():
            contexts.append(json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])
        if result.returncode:
            return 2 if handler in GUARDS else result.returncode
    if contexts:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                          "additionalContext": "\n".join(contexts)}, "suppressOutput": True}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in HANDLERS:
        sys.exit(2)
    try:
        sys.exit(run(sys.argv[1], json.load(sys.stdin)))
    except (KeyError, TypeError, ValueError, OSError):
        print("Devin file hook could not process the file event.", file=sys.stderr)
        # PreToolUse guards must prevent an unchecked edit. After the tool ran,
        # a malformed observation warrants a diagnostic, not a denial.
        sys.exit(2 if sys.argv[1] in GUARDS else 0)
