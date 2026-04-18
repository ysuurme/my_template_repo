import subprocess
import sys

import anthropic

from src.config import settings


def _staged_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True,
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
        client = anthropic.Anthropic(api_key=settings.ai_api_key)
        response = client.messages.create(
            model=settings.ai_model,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Generate a concise conventional commit message for this diff.\n"
                        "Format: <type>(<scope>): <description>\n"
                        "Return only the commit message, no explanation.\n\n"
                        f"{diff}"
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except anthropic.AuthenticationError:
        print("Invalid API key. Set AI_API_KEY in .env.")
        sys.exit(1)
    except anthropic.APIConnectionError:
        print("Could not reach Anthropic API. Check your network connection.")
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"Anthropic API error {e.status_code}: {e.message}")
        sys.exit(1)


def main() -> None:
    diff = _staged_diff()
    if not diff:
        print("No staged changes. Stage your changes first with `git add`.")
        sys.exit(1)
    print(generate_commit_message(diff))


if __name__ == "__main__":
    main()
