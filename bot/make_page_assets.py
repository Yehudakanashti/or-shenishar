"""מייצר את תמונת הכיסוי ותמונות הפרופיל לדף הפייסבוק.

הרצה:  python make_page_assets.py
התוצרים נשמרים ב-assets/page/ ומוכנים להעלאה לדף.
"""
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from app.config import BASE_DIR

SRC = BASE_DIR / "assets" / "products"
OUT = BASE_DIR / "assets" / "page"
FONTS = BASE_DIR / "assets" / "fonts"

# מידות שפייסבוק ממליצה עליהן
COVER = (1640, 856)
PROFILE = (500, 500)

NAME = "מתנות לכל גיל"
TAGLINE = "מוצרי חג מודפסים בתלת־ממד · הכיתוב נקבע לפי ההזמנה"

INK = (16, 24, 32)
WHITE = (255, 255, 255)


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / ("heebo-bold.ttf" if bold else "heebo-regular.ttf")), size)


def fill_crop(path, size: tuple[int, int], centering=(0.5, 0.5)) -> Image.Image:
    """חותך וממלא את המסגרת בלי לעוות."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return ImageOps.fit(img, size, method=Image.LANCZOS, centering=centering)


def vignette(img: Image.Image, strength: int = 90) -> Image.Image:
    """מכהה את הפינות כדי שהרקע מאחורי המוצרים לא יבלוט."""
    width, height = img.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([-width * 0.25, -height * 0.55, width * 1.25, height * 1.55], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(width, height) // 8))
    mask = ImageOps.invert(mask).point(lambda v: int(v * strength / 255))
    dark = Image.new("RGB", (width, height), (5, 7, 12))
    return Image.composite(dark, img, mask)


def bottom_gradient(size: tuple[int, int], start: float = 0.28, strength: int = 238) -> Image.Image:
    """שכבה כהה שמתחזקת כלפי מטה, כדי שהטקסט ייקרא."""
    width, height = size
    overlay = Image.new("L", (1, height), 0)
    pixels = overlay.load()
    begin = int(height * start)
    for y in range(height):
        if y <= begin:
            pixels[0, y] = 0
        else:
            ratio = (y - begin) / max(1, height - begin)
            pixels[0, y] = int(strength * ratio ** 1.5)
    return overlay.resize((width, height))


def make_cover() -> None:
    base = fill_crop(SRC / "trio-lit.jpg", COVER, centering=(0.46, 0.62))
    base = ImageEnhance.Color(base).enhance(1.08)
    base = ImageEnhance.Brightness(base).enhance(0.94)
    base = vignette(base, strength=120)

    shade = Image.new("RGB", COVER, (6, 8, 14))
    base = Image.composite(shade, base, bottom_gradient(COVER))

    draw = ImageDraw.Draw(base)
    center_x = COVER[0] // 2
    draw.text((center_x, 666), NAME, font=font(True, 96), fill=WHITE, anchor="mm")
    draw.text((center_x, 754), TAGLINE, font=font(False, 38), fill=(226, 222, 240), anchor="mm")

    # קו קטן מתחת לכותרת, בצבע המותג
    draw.rounded_rectangle([center_x - 95, 798, center_x + 95, 804], radius=3, fill=(160, 150, 255))

    base.save(OUT / "cover.jpg", "JPEG", quality=90, optimize=True)
    print(f"  ✓ cover.jpg  {COVER[0]}×{COVER[1]}")


def make_profile(source: str, name: str, zoom: float = 1.0, focus=(0.5, 0.42)) -> None:
    img = ImageOps.exif_transpose(Image.open(SRC / source)).convert("RGB")
    side = int(min(img.size) / zoom)
    left = int((img.width - side) * focus[0])
    top = int((img.height - side) * focus[1])
    img = img.crop((left, top, left + side, top + side)).resize(PROFILE, Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    img = ImageEnhance.Color(img).enhance(1.1)

    # טשטוש עדין של הפינות כדי שהעיגול ייראה נקי
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    img.save(OUT / name, "JPEG", quality=92, optimize=True)
    print(f"  ✓ {name}  {PROFILE[0]}×{PROFILE[1]}")


def make_profile_preview() -> None:
    """איך תמונות הפרופיל ייראו בעיגול הקטן שפייסבוק מציגה."""
    options = ["profile-etrog.jpg", "profile-sukkah.jpg", "profile-pomegranate.jpg"]
    canvas = Image.new("RGB", (760, 300), (245, 245, 250))
    draw = ImageDraw.Draw(canvas)
    for index, name in enumerate(options):
        img = Image.open(OUT / name).resize((170, 170), Image.LANCZOS)
        mask = Image.new("L", (170, 170), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 169, 169], fill=255)
        x = 60 + index * 230
        canvas.paste(img, (x, 40), mask)
        small = img.resize((56, 56), Image.LANCZOS)
        small_mask = mask.resize((56, 56), Image.LANCZOS)
        canvas.paste(small, (x + 57, 224), small_mask)
        draw.text((x + 85, 292), name.replace("profile-", "").replace(".jpg", ""),
                  font=font(False, 20), fill=(100, 108, 118), anchor="mm")
    canvas.save(OUT / "profile-preview.jpg", "JPEG", quality=92)
    print("  ✓ profile-preview.jpg  (השוואה בגודל אמיתי)")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not (FONTS / "heebo-bold.ttf").exists():
        print("  ✗ חסרים קבצי הפונט ב-assets/fonts")
        return 1
    print("\n  מייצר נכסים לדף:\n")
    make_cover()
    make_profile("etrog-lit.jpg", "profile-etrog.jpg", zoom=1.3, focus=(0.5, 0.36))
    make_profile("sukkah-green.jpg", "profile-sukkah.jpg", zoom=1.2, focus=(0.5, 0.42))
    make_profile("trio-lit.jpg", "profile-pomegranate.jpg", zoom=2.15, focus=(0.09, 0.42))
    make_profile_preview()
    print(f"\n  הכול ב-{OUT}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
