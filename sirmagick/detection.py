from contextlib import ExitStack
from pathlib import Path
from time import perf_counter

from .data import Detection, original_points
from .images import detection_image


class Detector:
    """Create once per worker and reuse sequentially for multiple images."""

    def __init__(self, model_dir: Path, max_side: int = 1024, max_people: int = 20):
        if max_side < 128 or max_people < 1:
            raise ValueError("max_side must be >= 128 and max_people must be >= 1.")
        for name in ("face_landmarker.task", "pose_landmarker_lite.task"):
            if not (model_dir / name).is_file():
                raise FileNotFoundError(f"Model missing: {model_dir / name}. Run download-models first.")
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        self.mp = mp
        self.max_side = max_side
        self._stack = ExitStack()
        try:
            def base(name):
                return python.BaseOptions(model_asset_path=str(model_dir / name),
                                          delegate=python.BaseOptions.Delegate.CPU)
            self.face = self._stack.enter_context(vision.FaceLandmarker.create_from_options(
                vision.FaceLandmarkerOptions(base_options=base("face_landmarker.task"),
                    running_mode=vision.RunningMode.IMAGE, num_faces=max_people)))
            self._pose_options = vision.PoseLandmarkerOptions(base_options=base("pose_landmarker_lite.task"),
                running_mode=vision.RunningMode.IMAGE, num_poses=max_people)
            self.pose = self._stack.enter_context(vision.PoseLandmarker.create_from_options(self._pose_options))
            self._segmented_pose = None
        except Exception:
            self._stack.close()
            raise

    def detect(self, image, segmentation=False) -> Detection:
        import numpy as np

        started = perf_counter()
        reduced = detection_image(image, self.max_side)
        data = np.asarray(reduced,dtype=np.uint8)
        if segmentation:
            # MediaPipe float-mask bindings can abort on non-contiguous row strides.
            # https://github.com/google-ai-edge/mediapipe/issues/6331
            data = np.pad(data,((0,0),(0,(-data.shape[1])%4),(0,0)),mode='edge')
        frame = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,data=np.ascontiguousarray(data))
        coordinate_width = image.width*data.shape[1]/reduced.width
        faces = self.face.detect(frame).face_landmarks
        pose_model = self.pose
        if segmentation:
            if self._segmented_pose is None:
                from dataclasses import replace
                from mediapipe.tasks.python import vision
                options = replace(self._pose_options,output_segmentation_masks=True)
                self._segmented_pose = self._stack.enter_context(vision.PoseLandmarker.create_from_options(options))
            pose_model = self._segmented_pose
        pose_result = pose_model.detect(frame)
        poses = pose_result.pose_landmarks
        mask = None
        if segmentation and pose_result.segmentation_masks:
            masks = []
            for item in pose_result.segmentation_masks:
                if not item.is_contiguous():
                    raise ValueError('Person mask has an unsupported memory layout; job aborted safely.')
                masks.append(np.asarray(item.numpy_view()).reshape(item.height,item.width)[:,:reduced.width])
            mask = np.uint8(np.clip(np.maximum.reduce(masks)*255,0,255))
        return Detection(*image.size, *reduced.size,
                         [original_points(face, coordinate_width, image.height) for face in faces],
                         [original_points(pose, coordinate_width, image.height) for pose in poses],
                         perf_counter() - started,mask)

    def close(self):
        self._stack.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
