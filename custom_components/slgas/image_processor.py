"""Meter image preprocessing — glare removal + contrast enhancement.

Uses only Pillow and numpy, both built-in HA dependencies.

Pipeline:
  1. Detect over-exposed (glare) pixels: all RGB channels > 240
  2. Highlight recovery: compress top tonal range (soft curve)
  3. Glare regions: blend with Gaussian-blurred version to reduce hot spots
  4. Contrast enhancement via ImageEnhance.Contrast
"""
import logging

_LOGGER = logging.getLogger(__name__)

_GLARE_THRESHOLD = 240   # pixel brightness threshold for glare detection
_GLARE_SKIP_RATIO = 0.7  # if glare > 70% of image, skip processing


def preprocess_meter_image(image_path: str) -> bool:
    """Remove glare and enhance contrast for meter OCR.

    Returns True on success, False if skipped or failed.
    """
    try:
        import numpy as np
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError:
        _LOGGER.warning("[影像處理] Pillow/numpy 未找到，跳過預處理")
        return False

    try:
        img = Image.open(image_path).convert("RGB")
        arr = np.array(img, dtype=np.float32)

        # ── Step 1: 偵測反光遮罩 ─────────────────────────────────
        t = _GLARE_THRESHOLD
        glare_mask = (arr[:, :, 0] > t) & (arr[:, :, 1] > t) & (arr[:, :, 2] > t)

        glare_ratio = glare_mask.sum() / glare_mask.size
        _LOGGER.debug("[影像處理] 反光面積佔比: %.1f%%", glare_ratio * 100)

        if glare_ratio > _GLARE_SKIP_RATIO:
            _LOGGER.warning(
                "[影像處理] 反光面積過大 (%.0f%%)，跳過預處理",
                glare_ratio * 100,
            )
            return False

        # ── Step 2: 高光壓縮（soft curve，將 >90% 亮度往下拉） ──
        norm = arr / 255.0
        norm = np.where(norm > 0.9, 0.9 + (norm - 0.9) * 0.25, norm)
        arr = (norm * 255.0).clip(0, 255)

        # ── Step 3: 反光區域與模糊版本混合 ──────────────────────
        if glare_ratio > 0.01:
            base_img = Image.fromarray(arr.astype(np.uint8))
            blurred = base_img.filter(ImageFilter.GaussianBlur(radius=12))
            blur_arr = np.array(blurred, dtype=np.float32)

            mask3 = np.stack([glare_mask] * 3, axis=-1)
            arr = np.where(mask3, blur_arr, arr)
            _LOGGER.debug("[影像處理] 反光混合完成，面積 %.1f%%", glare_ratio * 100)

        # ── Step 4: 對比強化 ──────────────────────────────────────
        result = Image.fromarray(arr.astype(np.uint8))
        result = ImageEnhance.Contrast(result).enhance(1.4)
        result = ImageEnhance.Sharpness(result).enhance(1.2)

        result.save(image_path)
        _LOGGER.info(
            "[影像處理] 預處理完成: %s (反光佔比 %.1f%%)",
            image_path, glare_ratio * 100,
        )
        return True

    except Exception as exc:
        _LOGGER.error("[影像處理] 預處理失敗: %s", exc, exc_info=True)
        return False
