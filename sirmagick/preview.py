from PIL import ImageDraw

from .data import Detection

POSE_EDGES = ((11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
              (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
              (24, 26), (26, 28), (27, 29), (29, 31), (28, 30), (30, 32))


def render_preview(image, result: Detection):
    output = image.copy()
    draw = ImageDraw.Draw(output)
    radius = max(1, round(min(image.size) / 350))
    for face in result.faces:
        for point in face:
            draw.ellipse((point.x-radius, point.y-radius, point.x+radius, point.y+radius),
                         fill="#00ff80")
    for pose in result.poses:
        for a, b in POSE_EDGES:
            if min(pose[a].visibility, pose[b].visibility,
                   pose[a].presence, pose[b].presence) >= 0.5:
                draw.line((pose[a].x, pose[a].y, pose[b].x, pose[b].y),
                          fill="#ffb000", width=radius * 2)
        for point in pose:
            if min(point.visibility, point.presence) >= 0.5:
                draw.ellipse((point.x-radius*2, point.y-radius*2,
                              point.x+radius*2, point.y+radius*2), fill="#ffb000")
    draw.rectangle((0, 0, min(image.width, 340), 22), fill="black")
    draw.text((5, 5), f"Faces: {len(result.faces)} | Bodies: {len(result.poses)}", fill="white")
    return output
