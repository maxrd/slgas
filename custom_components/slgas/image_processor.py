"""Meter image preprocessing — glare removal + contrast enhancement."""
import logging

_LOGGER = logging.getLogger(__name__)


def preprocess_meter_image(image_path: str) -> bool:
    """Remove glare and enhance contrast for meter OCR.

    Pipeline:
      1. Detect over-exposed (glare) pixels via HSV V-channel threshold
      2. Dilate mask to cover glare edges
      3. cv2.inpaint (TELEA) to fill glare regions
      4. CLAHE on LAB L-channel for adaptive contrast
      5. Overwrite original file with processed result

    Returns True on success, False if skipped or failed.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        _LOGGER.warning("[影像處理] opencv-python-headless 未安裝，跳過預處理")
        return False

    try:
        img = cv2.imread(image_path)
        if img is None:
            _LOGGER.error("[影像處理] 無法讀取圖片: %s", image_path)
            return False

        h, w = img.shape[:2]
        total_pixels = h * w

        # ── Step 1: 偵測反光區域 ─────────────────────────────────
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        _, glare_mask = cv2.threshold(v_channel, 240, 255, cv2.THRESH_BINARY)

        # ── Step 2: 擴大遮罩涵蓋反光邊緣 ─────────────────────────
        kernel = np.ones((5, 5), np.uint8)
        glare_mask = cv2.dilate(glare_mask, kernel, iterations=2)

        glare_ratio = cv2.countNonZero(glare_mask) / total_pixels
        _LOGGER.debug("[影像處理] 反光面積佔比: %.1f%%", glare_ratio * 100)

        if glare_ratio > 0.6:
            _LOGGER.warning(
                "[影像處理] 反光面積過大 (%.0f%%)，無法有效修補，跳過 inpaint",
                glare_ratio * 100,
            )
        elif glare_ratio > 0.01:
            # ── Step 3: Inpaint 填補反光區域 ─────────────────────
            img = cv2.inpaint(img, glare_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
            _LOGGER.debug("[影像處理] Inpaint 完成，修補面積: %.1f%%", glare_ratio * 100)

        # ── Step 4: CLAHE 自適應對比強化 ─────────────────────────
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab = cv2.merge([clahe.apply(l), a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # ── Step 5: 覆寫原檔 ──────────────────────────────────────
        cv2.imwrite(image_path, img)
        _LOGGER.info("[影像處理] 預處理完成: %s (反光佔比 %.1f%%)", image_path, glare_ratio * 100)
        return True

    except Exception as exc:
        _LOGGER.error("[影像處理] 預處理失敗: %s", exc, exc_info=True)
        return False
