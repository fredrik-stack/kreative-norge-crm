from __future__ import annotations

from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .core import FixtureSpec, safe_declared_pixel_bomb


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _save_jpeg(image: Image.Image, path: Path, *, quality: int = 88, exif=None) -> None:
    image.convert("RGB").save(
        path,
        format="JPEG",
        quality=quality,
        subsampling=0,
        optimize=False,
        progressive=False,
        exif=exif or b"",
    )


def _photo_like(size: tuple[int, int], *, seed: int, portrait: bool = False) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, (36, 62, 89))
    draw = ImageDraw.Draw(image)

    # Deterministic bands and shapes create detail without external images.
    for y in range(0, height, max(1, height // 80)):
        ratio = y / max(1, height - 1)
        color = (
            int(28 + 100 * ratio),
            int(75 + 90 * ratio),
            int(110 + 70 * ratio),
        )
        draw.rectangle((0, y, width, min(height, y + height // 80 + 1)), fill=color)

    rng = random.Random(seed)
    for index in range(48):
        x = rng.randrange(0, width)
        y = rng.randrange(0, height)
        radius = rng.randrange(max(8, min(size) // 80), max(16, min(size) // 15))
        color = (
            rng.randrange(45, 240),
            rng.randrange(45, 220),
            rng.randrange(45, 210),
        )
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    subject_x = int(width * (0.72 if not portrait else 0.36))
    subject_y = int(height * (0.46 if not portrait else 0.35))
    subject_radius = max(45, min(size) // 7)
    draw.ellipse(
        (
            subject_x - subject_radius,
            subject_y - subject_radius,
            subject_x + subject_radius,
            subject_y + subject_radius,
        ),
        fill=(245, 195, 81),
        outline=(255, 246, 210),
        width=max(4, subject_radius // 18),
    )
    draw.text(
        (max(24, width // 25), max(24, height // 18)),
        "SYNTHETIC PHOTO",
        font=_font(max(24, min(size) // 24)),
        fill=(255, 255, 255),
    )
    return image


def _logo(
    size: tuple[int, int],
    *,
    label: str,
    vertical: bool = False,
    small_text: bool = False,
) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = max(12, min(size) // 18)
    draw.rounded_rectangle(
        (inset, inset, width - inset, height - inset),
        radius=max(14, min(size) // 12),
        fill=(21, 91, 73, 230),
        outline=(115, 225, 177, 255),
        width=max(4, min(size) // 90),
    )
    mark_radius = max(20, min(size) // 7)
    mark_x = width // 2 if vertical else max(inset + mark_radius + 12, width // 5)
    mark_y = max(inset + mark_radius + 12, height // 3 if vertical else height // 2)
    draw.ellipse(
        (
            mark_x - mark_radius,
            mark_y - mark_radius,
            mark_x + mark_radius,
            mark_y + mark_radius,
        ),
        fill=(245, 195, 81, 255),
    )
    font_size = max(12, min(size) // (17 if small_text else 8))
    text_anchor = (width // 2, int(height * (0.73 if vertical else 0.5)))
    draw.text(text_anchor, label, font=_font(font_size), fill="white", anchor="mm")
    if small_text:
        draw.text(
            (width // 2, int(height * 0.72)),
            "SMALL LETTERING · 2026",
            font=_font(max(10, font_size // 2)),
            fill=(222, 246, 235, 255),
            anchor="mm",
        )
    return image


def generate_fixtures(root: Path) -> list[FixtureSpec]:
    root.mkdir(parents=True, exist_ok=True)

    fixtures = [
        FixtureSpec("square_transparent_logo", "square-logo.png", "image/png", "logo"),
        FixtureSpec("wide_logo", "wide-logo.png", "image/png", "logo"),
        FixtureSpec("tall_logo", "tall-logo.png", "image/png", "logo"),
        FixtureSpec("small_text_logo", "small-text-logo.png", "image/png", "logo"),
        FixtureSpec("landscape_photo", "landscape-photo.jpg", "image/jpeg", "photo"),
        FixtureSpec("portrait_photo", "portrait-photo.jpg", "image/jpeg", "photo"),
        FixtureSpec("exif_orientation", "exif-orientation.jpg", "image/jpeg", "photo"),
        FixtureSpec("metadata_photo", "metadata-photo.jpg", "image/jpeg", "photo"),
        FixtureSpec("small_image", "small-image.png", "image/png", "photo", note="must not upscale"),
        FixtureSpec("very_wide", "very-wide.jpg", "image/jpeg", "photo"),
        FixtureSpec("very_tall", "very-tall.jpg", "image/jpeg", "photo"),
        FixtureSpec("blurry", "blurry.jpg", "image/jpeg", "photo"),
        FixtureSpec("strongly_compressed", "compressed.jpg", "image/jpeg", "photo"),
        FixtureSpec("corrupt", "corrupt.png", "image/png", "invalid", expected="reject"),
        FixtureSpec(
            "mime_mismatch",
            "mime-mismatch.jpg",
            "image/jpeg",
            "invalid",
            expected="reject",
        ),
        FixtureSpec("pixel_bomb", "pixel-bomb.png", "image/png", "invalid", expected="reject"),
        FixtureSpec(
            "generic_platform_icon",
            "generic-platform-icon.png",
            "image/png",
            "invalid",
            expected="reject",
            semantic_flags=("generic_platform_icon",),
        ),
        FixtureSpec("alpha_png", "alpha.png", "image/png", "logo"),
        FixtureSpec("jpeg_without_alpha", "opaque.jpg", "image/jpeg", "photo"),
        FixtureSpec(
            "synthetic_svg",
            "synthetic.svg",
            "image/svg+xml",
            "vector",
            expected="reject",
            note="SVG is detected but rejected by the phase 3B.1 policy",
        ),
    ]

    _logo((900, 900), label="KN").save(root / "square-logo.png", format="PNG", compress_level=9)
    _logo((1800, 520), label="KREATIVE NORGE").save(
        root / "wide-logo.png", format="PNG", compress_level=9
    )
    _logo((620, 1600), label="KREATIV", vertical=True).save(
        root / "tall-logo.png", format="PNG", compress_level=9
    )
    _logo((1800, 520), label="KREATIVE NORGE", small_text=True).save(
        root / "small-text-logo.png", format="PNG", compress_level=9
    )

    landscape = _photo_like((2400, 1600), seed=20260731)
    portrait = _photo_like((1600, 2400), seed=20260732, portrait=True)
    _save_jpeg(landscape, root / "landscape-photo.jpg")
    _save_jpeg(portrait, root / "portrait-photo.jpg")

    exif = Image.Exif()
    exif[274] = 6
    exif[315] = "Kreative Norge synthetic fixture"
    _save_jpeg(_photo_like((1800, 1200), seed=20260733), root / "exif-orientation.jpg", exif=exif)

    metadata_exif = Image.Exif()
    metadata_exif[270] = "Metadata must not survive into public renditions"
    metadata_exif[315] = "Synthetic Fixture Author"
    _save_jpeg(landscape, root / "metadata-photo.jpg", exif=metadata_exif)

    small = _photo_like((120, 80), seed=20260734)
    small.save(root / "small-image.png", format="PNG", compress_level=9)
    _save_jpeg(_photo_like((3000, 500), seed=20260735), root / "very-wide.jpg")
    _save_jpeg(_photo_like((500, 3000), seed=20260736, portrait=True), root / "very-tall.jpg")
    _save_jpeg(landscape.filter(ImageFilter.GaussianBlur(radius=22)), root / "blurry.jpg")
    _save_jpeg(landscape, root / "compressed.jpg", quality=7)

    (root / "corrupt.png").write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
    mismatch = _logo((640, 640), label="MIME")
    mismatch.save(root / "mime-mismatch.jpg", format="PNG", compress_level=9)
    (root / "pixel-bomb.png").write_bytes(safe_declared_pixel_bomb())

    icon = Image.new("RGBA", (800, 800), (41, 93, 173, 255))
    icon_draw = ImageDraw.Draw(icon)
    icon_draw.ellipse((170, 170, 630, 630), fill=(255, 255, 255, 255))
    icon_draw.text((400, 400), "P", font=_font(240), fill=(41, 93, 173, 255), anchor="mm")
    icon.save(root / "generic-platform-icon.png", format="PNG", compress_level=9)

    alpha = Image.new("RGBA", (1000, 700), (0, 0, 0, 0))
    alpha_draw = ImageDraw.Draw(alpha)
    alpha_draw.polygon(((100, 600), (500, 80), (900, 600)), fill=(42, 176, 119, 170))
    alpha_draw.ellipse((300, 220, 700, 620), fill=(245, 195, 81, 220))
    alpha.save(root / "alpha.png", format="PNG", compress_level=9)
    _save_jpeg(_photo_like((1600, 1000), seed=20260737), root / "opaque.jpg")

    (root / "synthetic.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
<rect width="800" height="500" fill="#155b49"/>
<circle cx="240" cy="250" r="130" fill="#f5c351"/>
<text x="420" y="270" fill="white" font-size="64">SYNTHETIC SVG</text>
</svg>
""",
        encoding="utf-8",
    )

    return fixtures
