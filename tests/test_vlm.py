from PIL import Image

from pagesight.answer.vlm import load_image


def test_large_pages_shrink_to_the_pixel_budget_keeping_their_shape(tmp_path):
    path = tmp_path / "a4.png"
    Image.new("RGB", (1654, 2339), "white").save(path)  # an A4 page at 200 dpi

    img = load_image(path, max_pixels=1_000_000)

    assert img.width * img.height <= 1_000_000
    assert img.width * img.height > 990_000  # shrunk only as far as needed
    assert abs(img.width / img.height - 1654 / 2339) < 0.002


def test_small_pages_are_never_enlarged(tmp_path):
    path = tmp_path / "small.png"
    Image.new("L", (300, 400), "white").save(path)

    img = load_image(path, max_pixels=1_000_000)

    assert img.size == (300, 400) and img.mode == "RGB"
