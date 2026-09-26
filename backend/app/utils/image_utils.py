from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError


def decode_image(data, max_pixels):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Use a JPEG, PNG or WebP image")
                if image.width * image.height > max_pixels:
                    raise ValueError("Image dimensions exceed the allowed pixel limit")
                image.load()
                return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("Invalid, corrupt, or excessively large image") from error
