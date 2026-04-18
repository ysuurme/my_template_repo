import subprocess
import sys

from google import genai
from google.genai import errors as genai_errors
from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"


_settings = _Settings()


def _staged_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr.strip()}")
        sys.exit(1)
    except FileNotFoundError:
        print("Git not found. Ensure git is installed and available on PATH.")
        sys.exit(1)


def generate_commit_message(diff: str) -> str:
    try:
        client = genai.Client(api_key=_settings.google_api_key)
        response = client.models.generate_content(
            model=_settings.google_model,
            contents=(
                "Generate a concise conventional commit message for this diff.\n"
                "Format: <type>(<scope>): <description>\n"
                "Return only the commit message, no explanation.\n\n"
                f"{diff}"
            ),
        )
        return response.text.strip()
    except genai_errors.APIError as e:
        print(f"Google AI error: {e}")
        sys.exit(1)


def _commit(message: str) -> None:
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed: {e.stderr.strip() if e.stderr else e}")
        sys.exit(1)


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    diff = _staged_diff()
    if not diff:
        print("No staged changes. Stage your changes first with `git add`.")
        sys.exit(1)

    message = generate_commit_message(diff)

    if dry_run:
        print(message)
    else:
        print(message)
        _commit(message)


if __name__ == "__main__":
    main()
