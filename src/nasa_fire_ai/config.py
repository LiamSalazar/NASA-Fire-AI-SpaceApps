import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def load_project_environment() -> None:
    """One local configuration mechanism; explicit environment values take precedence."""
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


load_project_environment()


@dataclass(frozen=True)
class Settings:
    root: Path = Path(__file__).resolve().parents[2]
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.6-luna")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    api_key: str | None = os.getenv("OPENAI_API_KEY")
    include_media: bool = os.getenv("INCLUDE_MEDIA", "false").lower() == "true"
    max_single_download_mb: int = int(os.getenv("MAX_SINGLE_DOWNLOAD_MB", "50"))
    ingestion_retry_limit: int = int(os.getenv("INGESTION_RETRY_LIMIT", "3"))
    llm_extraction_enabled: bool = os.getenv("LLM_EXTRACTION_ENABLED", "false").lower() == "true"
    nvidia_api_key: str | None = os.getenv("NVIDIA_API_KEY")
    nvidia_base_url: str | None = os.getenv("NVIDIA_BASE_URL")
    nvidia_extraction_model: str | None = os.getenv(
        "NVIDIA_EXTRACTION_MODEL",
        os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
    )
    nvidia_science_fallback_models: tuple[str, ...] = tuple(
        m.strip() for m in os.getenv("NVIDIA_SCIENCE_FALLBACK_MODELS", "").split(",") if m.strip()
    )
    nvidia_science_vision_model: str | None = os.getenv("NVIDIA_SCIENCE_VISION_MODEL")
    nvidia_phase3_model: str = os.getenv(
        "NVIDIA_PHASE3_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"
    )
    nvidia_embedding_model: str = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")
    # Scientific stages only; NVIDIA is the default provider.
    science_provider: str = os.getenv("SCIENCE_PROVIDER", "nvidia").lower()
    scientific_llm_provider: str = os.getenv(
        "NASA_SCIENTIFIC_LLM_PROVIDER", os.getenv("SCIENCE_PROVIDER", "nvidia")
    ).lower()
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_science_model: str = os.getenv("ANTHROPIC_SCIENCE_MODEL", "claude-sonnet-5-5")
    anthropic_science_fallback_models: tuple[str, ...] = tuple(
        m.strip()
        for m in os.getenv("ANTHROPIC_SCIENCE_FALLBACK_MODELS", "").split(",")
        if m.strip()
    )
    anthropic_science_effort: str = os.getenv("ANTHROPIC_SCIENCE_EFFORT", "high")
    # "0" for a measurement run: a safety decline stays a recorded refusal instead of
    # being answered by the model the API routes to.
    anthropic_science_refusal_fallback: bool = (
        os.getenv("ANTHROPIC_SCIENCE_REFUSAL_FALLBACK", "1") == "1"
    )
    embedding_preprocessing_version: str = "phase2-v1"
    # Optional advisory routing only. It never grants semantic classifiers any
    # authority to publish claims, alter DIRECT matching, or mutate the KG.
    semantic_classifier_backend: str = os.getenv("SEMANTIC_CLASSIFIER_BACKEND", "rule")

    @property
    def scientific_model(self) -> str:
        if self.science_provider == "anthropic":
            return self.anthropic_science_model
        return self.nvidia_extraction_model or self.nvidia_phase3_model

    @property
    def science_fallback_models(self) -> tuple[str, ...]:
        if self.science_provider == "anthropic":
            return self.anthropic_science_fallback_models
        return self.nvidia_science_fallback_models

    @property
    def science_vision_model(self) -> str | None:
        # Claude models read images themselves.
        if self.science_provider == "anthropic":
            return self.anthropic_science_model
        return self.nvidia_science_vision_model

    @property
    def science_api_key(self) -> str | None:
        if self.science_provider == "anthropic":
            return self.anthropic_api_key
        return self.nvidia_api_key

    @property
    def registry_path(self) -> Path:
        return self.root / "data/index/evidence.sqlite"

    @property
    def raw_manifest_path(self) -> Path:
        return self.root / "data/raw/manifest.json"
