"""Single effect catalog shared by the bot, CLI, and persistent worker."""
from importlib import import_module
import secrets

DESCRIPTIONS = {
    "hornijail": "Put the image behind the window panes of the horny jail meme",
    "surveillance": "Face tracking locks, tactical status panels, REC, and UTC timestamp",
    "alienface": "Long gray alien face with large dark eyes and tiny features",
    "longface": "Stretch the face into a long narrow oval",
    "goblin": "Enlarge the nose and mouth and shrink the eyes",
    "giga": "Exaggerate the jaw width and chin",
    "meltface": "Let facial features melt downward",
    "combobreaker": "Add a large C-C-C-COMBOBREAKER wordmark",
    "youdied": "Darken the scene and add the supplied YOU DIED wordmark",
    "wasted": "Desaturate the scene and add the supplied wasted wordmark",
    "animerays": "Stretch the supplied anime action rays over the image",
    "achievement": "Steam-style achievement card; text requires a title and description",
    "chanpost": "Generate a fictional imageboard screenshot with repeated-digit post IDs",
    "hodl": "Orange Bitcoin hype, coins, rocket, and a rising green chart",
    "buythedip": "A collapsing red chart and irrationally optimistic Bitcoin slogans",
    "kaliyuga": "Breaking-news bars announcing 426,877 years left in the Kali Yuga",
    "censorface": "Frosted glass blur over every detected face",
    "censorbar": "A black eye bar following each detected head tilt",
    "redeyes": "Bloodshot sclera with fine red veins, preserving the iris",
    "lasereyes": "Glowing red eyes and bright laser beams",
    "firebreath": "Procedural flame jet from each detected mouth",
    "prismglow": "Saturated prism reflections, bokeh, warm/cool light leaks, and glow",
    "hellface": "Combine glowing laser eyes and fire breath",
    "rift": "Shatter the image into twisted mirrored shards around a neon dimensional rift",
    "tron": "Dark electric cyan contours with a bright neon glow",
    "thermal": "Simulated thermal camera colors from image brightness",
    "nightvision": "Green low-light vision with grain and scanlines",
    "thanos": "Disintegrate the image into drifting dust particles",
    "dealwithit": "Pixel sunglasses and a blunt aligned to every face",
    "numbers": "Rebuild the image from colored digits of varying size and density",
    "letters": "Rebuild the image from colored letters of varying size and density",
    "vortexcolumns": "Twisting 3D columns covered in repeated detected faces",
    "eyevortex": "Twisting 3D streams covered in repeated detected eyes",
    "mouthvortex": "Twisting 3D streams covered in repeated detected mouths",
    "halo": "A glowing golden halo aligned with each head",
    "devilhorns": "Glossy curved devil horns aligned with each head",
    "extrude": "Pull image contours into colored 3D sides and shadows",
    "emboss": "Turn the image into a lit metallic relief",
    "julia": "Julia fractal patterns colored with the original image",
    "newton": "Newton fractal basins with image-colored branching patterns",
    "glitch": "Digital tearing, displaced bands, and RGB errors",
    "crt": "Retro monitor scanlines, curved screen, and color fringes",
    "halftone": "Comic print dots with reduced colors",
    "fisheye": "Bulge the image through a wide-angle lens",
    "chudthor": "Surreal, angular face distortion",
    "warpface": "Enlarge the head and shrink facial features",
    "blockface": "Shrink the face and stretch the surrounding skin",
    "deepfry": "Extreme colors, JPEG artifacts, and random stickers",
    "fatmagic": "Broaden detected torsos smoothly with mild face widening",
    "tinyface": "Shrink the eyes, nose, and mouth together",
    "bigmouth": "Make the mouth much larger",
    "googly": "Make the eyes much larger",
    "wide": "Stretch the entire image to triple width",
    "eyeswap": "Replace the nose and mouth with eyes",
    "zoom": "Overlay zoomed ghost images",
    "tunnel": "Create a nested, rotating image tunnel",
    "kaleidoscope": "Mirror the image into six segments",
    "swirl": "Twist the image into a spiral",
    "rgbghost": "Offset the RGB color channels",
    "droste": "Repeat image copies along a logarithmic spiral",
    "complexsquare": "Square complex image coordinates and fold the scene",
    "complexexp": "Transform the image with the complex exponential function",
    "logpolar": "Unwrap circles into stripes",
    "inversion": "Invert the image center and surroundings",
    "sweat": "Add an anime sweat drop",
    "sparkle": "Add anime sparkle stars",
    "angry": "Add an anime anger symbol",
    "uwu": "Cute facial proportions with soft anime blush",
    "blush": "Soft cheek blush with anime hatch marks",
    "random": "Choose a random effect",
}

FACE_MODES = frozenset({"fatmagic", "tinyface", "bigmouth", "googly", "eyeswap"})
TRIPPY = frozenset({"zoom", "tunnel", "kaleidoscope", "swirl", "rgbghost", "fisheye"})
RETRO = frozenset({"glitch", "crt", "halftone"})
FRACTAL = frozenset({"julia", "newton"})
DEPTH = frozenset({"extrude", "emboss"})
TYPOGRAPHY = frozenset({"numbers", "letters"})
EULER = frozenset({"droste", "complexsquare", "complexexp", "logpolar", "inversion"})
ANIME = frozenset({"uwu", "blush", "sweat", "sparkle", "angry"})
VORTEX = frozenset({"vortexcolumns", "eyevortex", "mouthvortex"})
TRANSFORMERS = frozenset({'alienface','longface','goblin','giga','meltface','fatmagic'})
FACE_MASKS = frozenset({'censorface','censorbar','redeyes','lasereyes','firebreath','hellface'})
MEMES = frozenset({'combobreaker','youdied','wasted','animerays','achievement','chanpost','hodl','buythedip','kaliyuga','hornijail'})
STYLIZED = frozenset({'prismglow'})
FACE_EFFECTS = FACE_MODES | ANIME | VORTEX | TRANSFORMERS | FACE_MASKS | {"surveillance", "blockface", "warpface", "chudthor", "halo", "devilhorns", "dealwithit"}
DETECTION_EFFECTS = FACE_EFFECTS | {"tron"}
EFFECTS = frozenset(DESCRIPTIONS)


def resolve_effect(name):
    if name not in EFFECTS:
        raise ValueError("Unknown effect. Use @sirmagick help to list commands.")
    return secrets.choice(sorted(EFFECTS-{"random", "achievement"})) if name == "random" else name


def apply_effect(image, detection, name, text=None):
    if name not in EFFECTS or name == "random":
        raise ValueError("Select an effect before processing.")
    if name in FACE_EFFECTS:
        if detection is None:
            raise ValueError("Face detection is required.")
        detection.require("face")
        if image.size != (detection.width, detection.height):
            raise ValueError("Detection dimensions do not match the image.")
    if name == "wide":
        from .images import MAX_PIXELS
        if image.width*image.height*3 > MAX_PIXELS:
            raise ValueError("The ultrawide result would exceed 24 million pixels.")
    if name == "surveillance":
        from .surveillance import apply_effect as surveillance
        return surveillance(image,detection)
    if name in TRANSFORMERS:
        from .face_transformers import apply_effect as transform
        return transform(image,detection,name)
    if name in FACE_MASKS:
        from .face_masks import apply_effect as face_mask
        return face_mask(image,detection,name)
    if name in MEMES:
        from .meme_frames import apply_effect as meme
        return meme(image,name,text)
    if name in STYLIZED:
        from .stylized import apply_effect as stylized
        return stylized(image,name)
    if name in {"tron"}:
        from .neon import apply_effect as neon_effect
        if detection is not None and image.size != (detection.width, detection.height):
            raise ValueError("Detection dimensions do not match the image.")
        return neon_effect(image, name, detection)
    if name == "rift":
        from .rift import apply_rift
        return apply_rift(image)
    if name in TYPOGRAPHY:
        from .typography import apply_effect as typography_effect
        return typography_effect(image, name)
    if name in {"thermal", "nightvision", "thanos"}:
        from .cinematic import apply_effect as cinematic_effect
        return cinematic_effect(image, name)
    if name in VORTEX:
        from .vortexcolumns import apply_vortexcolumns
        feature = {"vortexcolumns": "face", "eyevortex": "eye", "mouthvortex": "mouth"}[name]
        return apply_vortexcolumns(image, detection, feature)
    if name in {"halo", "devilhorns"}:
        from .headgear import apply_effect as headgear_effect
        return headgear_effect(image, detection, name)
    if name in DEPTH:
        from .depth import apply_effect as depth_effect
        return depth_effect(image, name)
    if name in FRACTAL:
        from .fractal import apply_effect as fractal_effect
        return fractal_effect(image, name)
    if name in RETRO | {"fisheye"}:
        from .retro import apply_effect as retro_effect
        return retro_effect(image, name, detection)
    if name in FACE_MODES or name == "wide":
        from .face_modes import apply_mode
        return apply_mode(image, detection, name)
    if name in TRIPPY or name in EULER:
        module = import_module("sirmagick.trippy" if name in TRIPPY else "sirmagick.euler")
        return module.apply_effect(image, name)
    if name in ANIME:
        from .anime import apply_effect as anime_effect
        return anime_effect(image, detection, name, pass_number=secrets.randbelow(2)+1)
    module = import_module("sirmagick."+name)
    effect = getattr(module, "apply_"+name)
    return effect(image) if name == "deepfry" else effect(image, detection)
