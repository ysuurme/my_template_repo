from unittest.mock import MagicMock, patch

from src.utils.m_commit import generate_commit_message


def test_generate_commit_message_returns_string() -> None:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="feat(utils): add commit message generator")]

    with patch("src.utils.m_commit.anthropic.Anthropic") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.messages.create.return_value = mock_response

        result = generate_commit_message("diff --git a/file.py b/file.py\n+new line")

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_commit_message_strips_whitespace() -> None:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="  fix(config): correct env loading  ")]

    with patch("src.utils.m_commit.anthropic.Anthropic") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.messages.create.return_value = mock_response

        result = generate_commit_message("diff")

    assert result == "fix(config): correct env loading"
