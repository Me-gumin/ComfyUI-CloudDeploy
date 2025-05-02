import torch
from comfy.sd import load_checkpoint_guess_config

class ModelPrecisionConverter:
    """
    动态精度转换节点 (fp32/fp16/bf16)
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "dtype": (["fp16", "fp32", "bf16"], {"default": "fp16"}),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("converted_model", "converted_clip", "converted_vae")
    FUNCTION = "convert"
    CATEGORY = "custom/converters"

    def convert(self, model, clip, vae, dtype):
        # 映射字符串到 torch.dtype
        dtype_map = {
            "fp16": torch.float16,
            "fp32": torch.float32,
            "bf16": torch.bfloat16
        }
        target_dtype = dtype_map[dtype]

        # 克隆并转换 MODEL
        model_converted = model.clone()
        model_converted.model.to(dtype=target_dtype)

        # 克隆并转换 CLIP
        clip_converted = clip.clone()
        clip_converted.cond_stage_model.to(dtype=target_dtype)

        # 克隆并转换 VAE
        vae_converted = vae.clone()
        vae_converted.first_stage_model.to(dtype=target_dtype)

        return (model_converted, clip_converted, vae_converted)

# 注册节点
NODE_CLASS_MAPPINGS = {
    "ModelPrecisionConverter": ModelPrecisionConverter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ModelPrecisionConverter": "Model Precision Converter"
}