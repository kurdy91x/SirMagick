"""Single effect catalog shared by the bot, CLI, and persistent worker."""
from importlib import import_module
import secrets

DESCRIPTIONS = {
    "chudthor": "Skurrile, kantigere Gesichtsverformung",
    "warpface": "Kopf vergrößern und Gesichtszüge verkleinern",
    "blockface": "Gesicht verkleinern und äußeren Hautstreifen strecken",
    "deepfry": "Farben, JPEG-Artefakte und zufällige Sticker",
    "fatmagic": "Gesicht und erkannten Oberkörper verbreitern",
    "tinyface": "Augen, Nase und Mund zusammen verkleinern",
    "bigmouth": "Mund stark vergrößern",
    "googly": "Augen stark vergrößern",
    "wide": "Das gesamte Bild auf dreifache Breite ziehen",
    "eyeswap": "Nase und Mund jeweils durch ein Auge ersetzen",
    "zoom": "Zoom-Geisterbilder übereinanderlegen",
    "tunnel": "Verschachtelten, gedrehten Bildtunnel erzeugen",
    "kaleidoscope": "Bild sechsfach spiegeln",
    "swirl": "Bild zu einem Spiralwirbel drehen",
    "rgbghost": "Farbkanäle gegeneinander verschieben",
    "droste": "Wiederholte Bildkopien in einer logarithmischen Spirale",
    "complexsquare": "Bildkoordinaten quadrieren und Motive falten",
    "complexexp": "Bild durch die komplexe Exponentialfunktion verformen",
    "logpolar": "Kreise zu Streifen abwickeln",
    "inversion": "Bildmitte und Außenbereich komplex invertieren",
    "sweat": "Anime-Schweißtropfen hinzufügen",
    "sparkle": "Anime-Glitzersterne hinzufügen",
    "angry": "Anime-Wutsymbol hinzufügen",
    "random": "Einen zufälligen Effekt auswählen",
}

FACE_MODES = frozenset({"fatmagic", "tinyface", "bigmouth", "googly", "eyeswap"})
TRIPPY = frozenset({"zoom", "tunnel", "kaleidoscope", "swirl", "rgbghost"})
EULER = frozenset({"droste", "complexsquare", "complexexp", "logpolar", "inversion"})
ANIME = frozenset({"sweat", "sparkle", "angry"})
FACE_EFFECTS = FACE_MODES | ANIME | {"blockface", "warpface", "chudthor"}
EFFECTS = frozenset(DESCRIPTIONS)


def resolve_effect(name):
    if name not in EFFECTS:
        raise ValueError("Unbekannter Effekt. @sirmagick help zeigt alle Befehle.")
    return secrets.choice(sorted(EFFECTS-{"random"})) if name == "random" else name


def apply_effect(image, detection, name):
    if name not in EFFECTS or name == "random":
        raise ValueError("Effekt muss vor der Verarbeitung ausgewählt werden.")
    if name in FACE_EFFECTS:
        if detection is None:
            raise ValueError("Gesichtserkennung fehlt.")
        detection.require("face")
        if image.size != (detection.width, detection.height):
            raise ValueError("Erkennungsdaten passen nicht zur Bildgröße.")
    if name == "wide":
        from .images import MAX_PIXELS
        if image.width*image.height*3 > MAX_PIXELS:
            raise ValueError("Ultrawide-Ergebnis würde 24 Millionen Pixel überschreiten.")
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
