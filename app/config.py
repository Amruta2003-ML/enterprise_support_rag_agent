from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the repository (parent of the app/ package)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # OpenAI LLM & Embeddings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Optional Search Providers
    tavily_api_key: str = ""

    # Storage Paths
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    chroma_dir: str = str(BASE_DIR / "data" / "chroma")
    docs_dir: str = str(BASE_DIR / "data" / "docs")

    # Retrieval and Execution Tunables
    top_k: int = 5
    max_tool_rounds: int = 6
    enable_mock_llm: bool = False
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
