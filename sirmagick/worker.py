"""Persistent CPU worker; killing its process enforces real job deadlines."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys


class ProcessWorker:
    def __init__(self):
        self.process = None

    async def close(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                process.kill()
            await asyncio.to_thread(process.wait)
            process.stdin.close()
            await asyncio.to_thread(process.stdout.close)

    async def run(self, request, timeout):
        try:
            if self.process is None or self.process.poll() is not None:
                env = dict(os.environ)
                env.pop("DISCORD_TOKEN", None)
                self.process = subprocess.Popen(
                    [sys.executable, "-m", "sirmagick.worker"], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            async with asyncio.timeout(timeout):
                self.process.stdin.write((json.dumps(request) + "\n").encode())
                self.process.stdin.flush()
                line = await asyncio.to_thread(self.process.stdout.readline)
                if not line:
                    raise RuntimeError("Image processing stopped unexpectedly.")
                result = json.loads(line)
                if "error" in result:
                    raise ValueError(result["error"])
                return Path(result["output"])
        except (TimeoutError, asyncio.CancelledError, RuntimeError, BrokenPipeError):
            await self.close()
            raise


def serve():
    from contextlib import redirect_stdout
    from .images import load_image
    from .effects import EFFECTS, FACE_EFFECTS, DETECTION_EFFECTS, resolve_effect, apply_effect
    detector = None
    protocol = sys.stdout
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                with redirect_stdout(sys.stderr):
                    effect = request["effect"]
                    if effect not in EFFECTS:
                        raise ValueError("Unknown effect.")
                    was_random = effect == "random"
                    effect = resolve_effect(effect)
                    image = load_image(Path(request["source"]))
                    detection = None
                    if effect in DETECTION_EFFECTS:
                        if detector is None:
                            from .detection import Detector
                            detector = Detector(Path(request["models"]), request["max_side"], request["max_people"])
                        detection = detector.detect(image)
                        if effect in FACE_EFFECTS:
                            detection.require("face")
                    result = apply_effect(image, detection, effect)
                    output = Path(request["destination"]).with_suffix(".png")
                    if was_random:
                        output = output.with_name(output.stem+"-random-"+effect+output.suffix)
                    result.save(output)
                    if output.stat().st_size > request["max_output"]:
                        if result.convert("RGBA").getchannel("A").getextrema() == (255, 255):
                            output.unlink()
                            output = output.with_suffix(".jpg")
                            for quality in (90, 75, 55, 35):
                                result.convert("RGB").save(output, quality=quality)
                                if output.stat().st_size <= request["max_output"]:
                                    break
                        if output.stat().st_size > request["max_output"]:
                            raise ValueError("The result is too large to upload.")
                response = {"output": str(output)}
            except Exception as exc:
                from .data import NoDetectionError
                response = {"error": "No face detected." if isinstance(exc, NoDetectionError)
                            else "Could not process the image. Check its format, the models, and the size limit."}
            protocol.write(json.dumps(response) + "\n")
            protocol.flush()
    finally:
        if detector is not None:
            detector.close()


if __name__ == "__main__":
    serve()
