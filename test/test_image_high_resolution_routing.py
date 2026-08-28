from __future__ import annotations

import base64
import unittest
from io import BytesIO
from unittest import mock

from PIL import Image

from services.protocol import openai_v1_image_generations
from services.protocol.conversation import (
    ConversationRequest,
    normalize_codex_image_size,
    stream_codex_image_outputs,
)
from utils.helper import route_image_model_for_size


class ImageHighResolutionRoutingTests(unittest.TestCase):
    def test_regular_model_keeps_1k_sizes(self):
        self.assertEqual(
            route_image_model_for_size("gpt-image-2", "1920x1088"),
            ("gpt-image-2", "1920x1088"),
        )

    def test_regular_model_routes_2k_and_4k_sizes_to_codex(self):
        for size in ("2048x2048", "2560x1440", "1440x2560", "3840x2160", "2160x3840"):
            with self.subTest(size=size):
                self.assertEqual(
                    route_image_model_for_size("gpt-image-2", size),
                    ("codex-gpt-image-2", size),
                )

    def test_resolution_aliases_are_normalized(self):
        self.assertEqual(
            route_image_model_for_size("gpt-image-2", "2K"),
            ("codex-gpt-image-2", "2048x2048"),
        )
        self.assertEqual(
            route_image_model_for_size("gpt-image-2", "4k"),
            ("codex-gpt-image-2", "3840x2160"),
        )

    def test_existing_codex_model_is_not_rewritten(self):
        self.assertEqual(
            route_image_model_for_size("plus-codex-gpt-image-2", "3840x2160"),
            ("plus-codex-gpt-image-2", "3840x2160"),
        )

    def test_generations_handler_uses_routed_model(self):
        captured = []

        def fake_stream(request):
            captured.append(request)
            return iter(())

        with mock.patch.object(openai_v1_image_generations, "stream_image_outputs_with_pool", fake_stream):
            openai_v1_image_generations.handle({
                "model": "gpt-image-2",
                "prompt": "high resolution poster",
                "size": "3840x2160",
            })

        self.assertEqual(captured[0].model, "codex-gpt-image-2")
        self.assertEqual(captured[0].size, "3840x2160")

    def test_codex_result_is_normalized_to_exact_requested_size(self):
        source = BytesIO()
        Image.new("RGB", (917, 1716), "red").save(source, format="PNG")

        normalized = normalize_codex_image_size(
            base64.b64encode(source.getvalue()).decode("ascii"),
            "1152x2048",
        )

        with Image.open(BytesIO(base64.b64decode(normalized))) as image:
            self.assertEqual(image.size, (1152, 2048))

    def test_codex_result_with_exact_size_is_not_reencoded(self):
        source = BytesIO()
        Image.new("RGB", (64, 32), "blue").save(source, format="PNG")
        encoded = base64.b64encode(source.getvalue()).decode("ascii")

        self.assertEqual(normalize_codex_image_size(encoded, "64x32"), encoded)

    def test_codex_result_applies_exif_orientation_before_size_check(self):
        source = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (32, 64), "green").save(source, format="JPEG", exif=exif)

        normalized = normalize_codex_image_size(
            base64.b64encode(source.getvalue()).decode("ascii"),
            "64x32",
        )

        with Image.open(BytesIO(base64.b64decode(normalized))) as image:
            self.assertEqual(image.size, (64, 32))
            self.assertEqual(image.format, "PNG")

    def test_codex_stream_returns_png_format_and_exact_pixels(self):
        source = BytesIO()
        Image.new("RGB", (46, 86), "purple").save(source, format="PNG")
        encoded = base64.b64encode(source.getvalue()).decode("ascii")

        class FakeBackend:
            def iter_codex_image_response_events(self, **_kwargs):
                return iter([{"type": "image_generation_call", "result": encoded}])

        outputs = list(stream_codex_image_outputs(
            FakeBackend(),
            ConversationRequest(prompt="poster", size="64x128", response_format="b64_json"),
        ))

        self.assertEqual(outputs[0].data[0]["output_format"], "png")
        with Image.open(BytesIO(base64.b64decode(outputs[0].data[0]["b64_json"]))) as image:
            self.assertEqual(image.size, (64, 128))

    def test_large_ratio_change_preserves_full_foreground_on_extended_canvas(self):
        source_image = Image.new("RGB", (100, 100), "blue")
        for x in range(100):
            for y in range(100):
                if x < 10 or x >= 90 or y < 10 or y >= 90:
                    source_image.putpixel((x, y), (255, 0, 0))
        source = BytesIO()
        source_image.save(source, format="PNG")

        normalized = normalize_codex_image_size(
            base64.b64encode(source.getvalue()).decode("ascii"),
            "64x128",
        )

        with Image.open(BytesIO(base64.b64decode(normalized))).convert("RGB") as image:
            self.assertEqual(image.size, (64, 128))
            # The red left/right edge remains in the centered foreground. A
            # destructive 1:2 center crop would have removed both edges.
            red, green, blue = image.getpixel((0, 64))
            self.assertGreater(red, 200)
            self.assertLess(green, 40)
            self.assertLess(blue, 40)


if __name__ == "__main__":
    unittest.main()
