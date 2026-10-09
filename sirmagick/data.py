"""Library-independent results in original image coordinates."""

from dataclasses import dataclass


class ImageError(ValueError):
    pass


class NoDetectionError(ValueError):
    pass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    visibility: float = 1.0
    presence: float = 1.0


@dataclass(frozen=True)
class Detection:
    width: int
    height: int
    detection_width: int
    detection_height: int
    faces: list[list[Point]]
    poses: list[list[Point]]
    elapsed_seconds: float

    def require(self, kind: str) -> None:
        if kind not in {"face", "body", "any"}:
            raise ValueError(f"Unknown detection type: {kind}")
        found = {"face": bool(self.faces), "body": bool(self.poses),
                 "any": bool(self.faces or self.poses)}[kind]
        if not found:
            raise NoDetectionError(f"No suitable detection ({kind}); job aborted.")


def original_points(landmarks, width: int, height: int) -> list[Point]:
    # Normalized coordinates refer to the entire image even after resizing.
    return [Point(float(p.x) * width, float(p.y) * height,
                  float(getattr(p, "visibility", None) or 0.0),
                  float(getattr(p, "presence", None) or 0.0)) for p in landmarks]
