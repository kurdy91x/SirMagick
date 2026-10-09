"""Twisting cylindrical streams textured with detected faces, eyes, or mouths."""
import cv2
import numpy as np
from PIL import Image

from .chudthor import OVAL
from .warpface import EYES, MOUTH


def apply_vortexcolumns(image, detection, feature="face"):
    detection.require("face")
    if feature not in {"face", "eye", "mouth"}:
        raise ValueError("Unknown vortex texture.")
    groups = (OVAL,) if feature == "face" else EYES if feature == "eye" else (MOUTH,)
    tile_height = 320 if feature == "face" else 160
    patches = []
    rgba = image.convert("RGBA")
    for face in detection.faces:
        for indices in groups:
            contour = np.array([(face[i].x, face[i].y) for i in indices])
            low, high = contour.min(axis=0), contour.max(axis=0)
            if feature == "face":
                padding = (high-low)*.12
                low, high = low-padding, high+padding
            else:
                center = (low+high)/2
                extent = np.maximum(high-low, 2)
                # Include surrounding skin without turning the crop into a full face.
                crop_width = extent[0]*1.45
                crop_height = max(extent[1]*1.5, crop_width*.50)
                low = center-np.array([crop_width, crop_height])/2
                high = center+np.array([crop_width, crop_height])/2
            x0, y0 = np.maximum(0, np.floor(low)).astype(int)
            x1, y1 = np.minimum(image.size, np.ceil(high)).astype(int)
            if x1 <= x0 or y1 <= y0:
                raise ValueError("Face feature lies outside the image.")
            patches.append(rgba.crop((x0, y0, x1, y1)).resize((256, tile_height), Image.Resampling.LANCZOS))
    texture = Image.new("RGBA", (256, tile_height*len(patches)))
    for index, patch in enumerate(patches):
        texture.paste(patch, (0, index*tile_height))
    atlas = np.asarray(texture, np.float32).copy()
    atlas[..., :3] *= atlas[..., 3:4]/255
    pixels = np.array(image.convert("RGBA"))
    height, width = pixels.shape[:2]
    output = pixels[..., :3].astype(np.float32)*.22
    columns = 3
    yy, xx = np.mgrid[:height, :width].astype(np.float32)
    v = yy/max(1, height-1)
    for column in range(columns):
        phase = column*2.1
        center = (column+.5)*width/columns+np.sin(v*7+phase)*width*.055
        radius = width/columns*.48*(.80+.20*np.cos(v*8+phase))
        x = (xx-center)/np.maximum(1., radius)
        inside = np.abs(x) < 1
        curved = np.arcsin(np.clip(x, -1, 1))/np.pi+.5
        u = (curved+v*1.25+column*.23+.09*np.sin(v*18)) % 1
        repeats = max(4 if feature == "face" else 7, len(patches))
        source_v = (v*repeats+column*.71+.22*np.sin(curved*6.28+v*9)) % len(patches)
        sampled = cv2.remap(atlas, (u*255).astype(np.float32),
                            (source_v*tile_height).astype(np.float32), cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_WRAP)
        np.divide(sampled[..., :3]*255, sampled[..., 3:4], out=sampled[..., :3],
                  where=sampled[..., 3:4]>0)
        roundness = np.sqrt(np.maximum(0, 1-x*x))
        light = .25+.75*roundness
        shine = .18*np.exp(-((x+.35)/.16)**2)
        color = sampled[..., :3]*light[..., None]+shine[..., None]*np.array([100, 155, 190])
        blend = np.clip((1-np.abs(x))/.035, 0, 1)*inside*(sampled[..., 3]/255)
        output = output*(1-blend[..., None])+color*blend[..., None]
    result = pixels.copy()
    result[..., :3] = np.clip(np.rint(output), 0, 255).astype(np.uint8)
    return Image.fromarray(result)
