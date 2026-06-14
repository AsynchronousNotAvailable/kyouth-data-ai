from enum import StrEnum


class Local(StrEnum):
    DEEPSEEK_R1_1_5B = "deepseek-r1:1.5b"
    PHI3_LATEST = "phi3:latest"
    LLAMA3_1_LATEST = "llama3.1:latest"
    QWEN_3_5_LATEST = "qwen3.5:latest"


class Cloud(StrEnum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_3_FLASH_PREVIEW = "gemini-3-flash-preview"


class Models:
    LOCAL_MODELS = Local
    CLOUD_MODELS = Cloud
