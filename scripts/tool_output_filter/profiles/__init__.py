"""Built-in deterministic output profiles."""

from .repeat_lines import PROFILE_ID as REPEAT_LINES_ID
from .repeat_lines import PROFILE_VERSION as REPEAT_LINES_VERSION
from .repeat_lines import transform as transform_repeat_lines
from .tap_success import PROFILE_ID as TAP_SUCCESS_ID
from .tap_success import PROFILE_VERSION as TAP_SUCCESS_VERSION
from .tap_success import transform as transform_tap_success


class ProfileTransform:
    __slots__ = ("accepted", "output", "profile_id", "profile_version")

    def __init__(
        self,
        profile_id: str,
        profile_version: int,
        output: str,
        accepted: bool,
    ) -> None:
        self.profile_id = profile_id
        self.profile_version = profile_version
        self.output = output
        self.accepted = accepted

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProfileTransform):
            return NotImplemented
        return (
            self.profile_id == other.profile_id
            and self.profile_version == other.profile_version
            and self.output == other.output
            and self.accepted == other.accepted
        )


def apply_profile(
    profile_id: str,
    output: str,
) -> ProfileTransform | None:
    if profile_id == REPEAT_LINES_ID:
        return ProfileTransform(
            profile_id,
            REPEAT_LINES_VERSION,
            transform_repeat_lines(output),
            True,
        )
    if profile_id == TAP_SUCCESS_ID:
        transformed = transform_tap_success(output)
        return ProfileTransform(
            profile_id,
            TAP_SUCCESS_VERSION,
            transformed if transformed is not None else output,
            transformed is not None,
        )
    return None


__all__ = [
    "ProfileTransform",
    "REPEAT_LINES_ID",
    "REPEAT_LINES_VERSION",
    "TAP_SUCCESS_ID",
    "TAP_SUCCESS_VERSION",
    "apply_profile",
    "transform_repeat_lines",
    "transform_tap_success",
]
