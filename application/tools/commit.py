import subprocess
import sys

from google import genai
from google.genai import errors as genai_errors

from src.config import settings


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
        client = genai.Client(api_key=settings.google_api_key)
        response = client.models.generate_content(
            model=settings.google_model,
            contents=(
                "Generate a conventional commit message for this diff.\n\n"
                "Rules:\n"
                "- Format: <type>(<scope>): <description>\n"
                "- Types: feat, fix, refactor, test, docs, chore, perf, ci, build, revert\n"
                "- Scope: the module, file, or area changed (omit if not obvious)\n"
                "- Description: imperative mood, ≤72 chars, no period at end\n"
                "- Add a blank line + body only if the change is complex or non-obvious\n"
                "- If a breaking change, append a footer: BREAKING CHANGE: <explanation>\n"
                "- Return only the commit message, no explanation, no markdown.\n\n"
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
