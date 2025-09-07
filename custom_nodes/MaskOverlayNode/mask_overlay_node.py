import cv2
import numpy as np
from PIL import Image
import torch

class MaskOverlayNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "overlay_image": ("IMAGE",),  # 只在 overlay 模式使用
                "mode": (["pixelate", "blur", "overlay", "black"],),
                "strength": ("INT", {"default": 20, "min": 1, "max": 100}),
                "feather": ("INT", {"default": 5, "min": 0, "max": 50}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_mask"
    CATEGORY = "Custom/MaskOps"

    def apply_mask(self, image, mask, overlay_image, mode, strength, feather):
        # 获取批次大小
        batch_size = image.shape[0]
        output_images = []
        
        for i in range(batch_size):
            # 转 numpy - 处理批次中的每个图像
            img = (image[i].cpu().numpy() * 255).astype(np.uint8)
            msk = (mask[i].cpu().numpy() * 255).astype(np.float32) / 255.0
            
            # 确保 mask 是二维的
            if len(msk.shape) == 3:
                msk = msk[:, :, 0]  # 取第一个通道
            
            h, w = img.shape[:2]

            # 羽化 mask
            if feather > 0:
                ksize = feather * 2 + 1
                msk = cv2.GaussianBlur(msk, (ksize, ksize), 0)

            overlay_result = img.copy()

            if mode == "pixelate":
                small = cv2.resize(img, (max(1, w // strength), max(1, h // strength)), interpolation=cv2.INTER_LINEAR)
                pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
                overlay_result = (msk[..., None] * pixelated + (1 - msk[..., None]) * overlay_result).astype(np.uint8)

            elif mode == "blur":
                blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=strength)
                overlay_result = (msk[..., None] * blurred + (1 - msk[..., None]) * overlay_result).astype(np.uint8)

            elif mode == "overlay":
                # 处理覆盖图像的批次
                ov_idx = min(i, overlay_image.shape[0] - 1)
                ov_np = (overlay_image[ov_idx].cpu().numpy() * 255).astype(np.uint8)
                ov_resized = cv2.resize(ov_np, (w, h), interpolation=cv2.INTER_LINEAR)
                overlay_result = (msk[..., None] * ov_resized + (1 - msk[..., None]) * overlay_result).astype(np.uint8)

            elif mode == "black":
                black = np.zeros_like(img)
                overlay_result = (msk[..., None] * black + (1 - msk[..., None]) * overlay_result).astype(np.uint8)

            # 转换回 Tensor 格式
            result_tensor = torch.from_numpy(overlay_result.astype(np.float32) / 255.0).unsqueeze(0)
            output_images.append(result_tensor)

        # 合并批次
        if output_images:
            return (torch.cat(output_images, dim=0),)
        else:
            # 返回空图像以防万一
            return (torch.zeros_like(image),)


NODE_CLASS_MAPPINGS = {
    "MaskOverlayNode": MaskOverlayNode
}