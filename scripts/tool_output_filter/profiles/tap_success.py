"""Conservative compaction for valid, fully successful TAP output."""

from __future__ import annotations

PROFILE_ID = "tap-success"
PROFILE_VERSION = 1

_DIAGNOSTIC_COMMENT_PREFIXES = (
    "# error",
    "# stack",
    "# message",
    "# operator",
    "# expected",
    "# actual",
    "# severity",
    "# at ",
)


def _line_ending(lines: list[str]) -> str:
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def _parse_plan(line: str) -> int | None:
    content = line.strip()
    if not content.startswith("1.."):
        return None
    count_text = content[3:].split("#", 1)[0].strip()
    if not count_text.isdecimal():
        return None
    return int(count_text)


def _parse_ok_number(line: str) -> tuple[int, bool] | None:
    content = line.strip()
    if not content.startswith("ok "):
        return None
    remainder = content[3:]
    number_text = remainder.split(maxsplit=1)[0]
    if not number_text.isdecimal():
        return None
    has_directive = False
    if "#" in content:
        directive = content.rsplit("#", 1)[1].strip().upper()
        if not directive.startswith(("SKIP", "TODO")):
            return None
        has_directive = True
    return int(number_text), has_directive


def _has_nonzero_failure_summary(content: str) -> bool:
    lowered = content.lower()
    for prefix in ("# fail", "# cancel"):
        if not lowered.startswith(prefix):
            continue
        remainder = lowered[len(prefix):]
        # Accept spelling variants ("# failed", "# failures:") but treat any
        # non-zero or unparseable count as a failure signal.
        value = remainder.lstrip("abcdefghijklmnopqrstuvwxyz").strip(" :\t")
        return not value.isdecimal() or int(value) != 0
    return False


def _parse_success_summary(content: str) -> tuple[str, int] | None:
    lowered = content.lower()
    for name in ("tests", "pass"):
        prefix = f"# {name} "
        if not lowered.startswith(prefix):
            continue
        value = lowered[len(prefix):].strip()
        return name, int(value) if value.isdecimal() else -1
    return None


def transform(output: str) -> str | None:
    """Return compact TAP, or ``None`` when the stream is not strictly safe."""

    lines = output.splitlines(keepends=True)
    if not lines or any(
        "[ai-toolkit-output-filter " in line for line in lines
    ):
        return None

    plan_count: int | None = None
    result_numbers: list[int] = []
    summary_counts: dict[str, int] = {}
    omitted_count = 0
    transformed: list[str] = []
    newline = _line_ending(lines)

    def flush_omitted() -> None:
        nonlocal omitted_count
        if omitted_count:
            transformed.append(
                "[ai-toolkit-output-filter tap-success/v1: "
                f"{omitted_count} successful result lines omitted]"
                f"{newline}"
            )
            omitted_count = 0

    for line in lines:
        content = line.strip()
        if content == "TAP version 13":
            flush_omitted()
            transformed.append(line)
            continue
        parsed_plan = _parse_plan(line)
        if parsed_plan is not None:
            if plan_count is not None:
                return None
            plan_count = parsed_plan
            flush_omitted()
            transformed.append(line)
            continue
        parsed_ok = _parse_ok_number(line)
        if parsed_ok is not None:
            number, has_directive = parsed_ok
            result_numbers.append(number)
            if has_directive:
                flush_omitted()
                transformed.append(line)
            else:
                omitted_count += 1
            continue
        if content.lower().startswith(_DIAGNOSTIC_COMMENT_PREFIXES):
            return None
        if _has_nonzero_failure_summary(content):
            return None
        parsed_summary = _parse_success_summary(content)
        if parsed_summary is not None:
            name, value = parsed_summary
            if value < 0 or name in summary_counts:
                return None
            summary_counts[name] = value
        if not content or content.startswith("#"):
            flush_omitted()
            transformed.append(line)
            continue
        return None

    flush_omitted()
    if (
        plan_count is None
        or plan_count == 0
        or result_numbers != list(range(1, plan_count + 1))
        or any(count != plan_count for count in summary_counts.values())
    ):
        return None
    return "".join(transformed)
