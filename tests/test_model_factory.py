"""Tests for the get_model_for_role model factory function."""

import os
import pytest
from unittest.mock import patch, MagicMock

from langchain_openai import ChatOpenAI


class TestModelFactoryProviderDetection:
    """Tests for provider auto-detection from model name prefixes."""

    def test_gpt_model_returns_openai(self):
        """GPT models (gpt-*) should use ChatOpenAI."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "gpt-4o-mini"}, clear=False):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock(spec=ChatOpenAI)
                mock_openai.return_value = mock_instance

                model = get_model_for_role("Test", "TEST_MODEL")

                mock_openai.assert_called_once()
                call_kwargs = mock_openai.call_args[1]
                assert call_kwargs["model"] == "gpt-4o-mini"
                assert model == mock_instance

    def test_gpt4_model_returns_openai(self):
        """GPT-4 models should use ChatOpenAI."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "gpt-4o"}, clear=False):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock(spec=ChatOpenAI)
                mock_openai.return_value = mock_instance

                model = get_model_for_role("Test", "TEST_MODEL")

                mock_openai.assert_called_once()
                call_kwargs = mock_openai.call_args[1]
                assert call_kwargs["model"] == "gpt-4o"
                assert model == mock_instance

    def test_gemini_model_returns_google_genai(self):
        """Gemini models (gemini-*) should use ChatGoogleGenerativeAI."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "gemini-2.0-flash"}, clear=False):
            # Mock the dynamic import of ChatGoogleGenerativeAI
            mock_gemini_class = MagicMock()
            mock_gemini_instance = MagicMock()
            mock_gemini_class.return_value = mock_gemini_instance
            
            mock_module = MagicMock()
            mock_module.ChatGoogleGenerativeAI = mock_gemini_class

            with patch.dict(
                "sys.modules", {"langchain_google_genai": mock_module}
            ):
                model = get_model_for_role("Test", "TEST_MODEL")

                mock_gemini_class.assert_called_once()
                call_kwargs = mock_gemini_class.call_args[1]
                assert call_kwargs["model"] == "gemini-2.0-flash"
                assert model == mock_gemini_instance

    def test_claude_model_returns_anthropic(self):
        """Claude models (claude-*) should use ChatAnthropic."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "claude-sonnet-4-20250514"}, clear=False):
            # Mock the dynamic import of ChatAnthropic
            mock_anthropic_class = MagicMock()
            mock_anthropic_instance = MagicMock()
            mock_anthropic_class.return_value = mock_anthropic_instance

            mock_module = MagicMock()
            mock_module.ChatAnthropic = mock_anthropic_class

            with patch.dict(
                "sys.modules", {"langchain_anthropic": mock_module}
            ):
                model = get_model_for_role("Test", "TEST_MODEL")

                mock_anthropic_class.assert_called_once()
                call_kwargs = mock_anthropic_class.call_args[1]
                assert call_kwargs["model_name"] == "claude-sonnet-4-20250514"
                assert model == mock_anthropic_instance

    def test_deepseek_model_uses_openai_with_custom_base_url(self):
        """DeepSeek models should use ChatOpenAI with custom base_url."""
        from src.graph import get_model_for_role

        with patch.dict(
            os.environ,
            {"TEST_MODEL": "deepseek-chat", "DEEPSEEK_API_KEY": "test-key"},
            clear=False,
        ):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock()
                mock_openai.return_value = mock_instance

                model = get_model_for_role("Test", "TEST_MODEL")

                # Verify ChatOpenAI was called with DeepSeek-specific config
                mock_openai.assert_called()
                call_kwargs = mock_openai.call_args[1]
                assert call_kwargs["base_url"] == "https://api.deepseek.com"
                assert call_kwargs["api_key"] == "test-key"
                assert call_kwargs["model"] == "deepseek-chat"


class TestModelFactoryDefaults:
    """Tests for default values and environment variable handling."""

    def test_uses_default_model_when_env_var_not_set(self):
        """Should use DEFAULT_MODEL when environment variable is not set."""
        from src.graph import get_model_for_role, DEFAULT_MODEL

        # Ensure the env var is not set
        env_var = "NONEXISTENT_MODEL_VAR"
        if env_var in os.environ:
            del os.environ[env_var]

        with patch("src.graph.ChatOpenAI") as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance

            get_model_for_role("Test", env_var)

            # Should use the default model
            mock_openai.assert_called()
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["model"] == DEFAULT_MODEL

    def test_temperature_parameter_passed_correctly(self):
        """Temperature parameter should be passed to the model constructor."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "gpt-4o-mini"}, clear=False):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock()
                mock_openai.return_value = mock_instance

                get_model_for_role("Test", "TEST_MODEL", temperature=0.7)

                mock_openai.assert_called()
                call_kwargs = mock_openai.call_args[1]
                assert call_kwargs["temperature"] == 0.7

    def test_additional_kwargs_passed_to_model(self):
        """Additional kwargs should be passed to the model constructor."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "gpt-4o-mini"}, clear=False):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock()
                mock_openai.return_value = mock_instance

                get_model_for_role("Test", "TEST_MODEL", streaming=True)

                mock_openai.assert_called()
                call_kwargs = mock_openai.call_args[1]
                assert call_kwargs["streaming"] is True

    def test_env_var_case_insensitive(self):
        """Model name should be case-insensitive for provider detection."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "GPT-4O-MINI"}, clear=False):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock()
                mock_openai.return_value = mock_instance

                get_model_for_role("Test", "TEST_MODEL")

                # Should still detect as OpenAI (gpt-*)
                mock_openai.assert_called()
                call_kwargs = mock_openai.call_args[1]
                # Model name should be lowercased
                assert call_kwargs["model"] == "gpt-4o-mini"


class TestModelFactoryFallback:
    """Tests for fallback behavior when optional dependencies are missing."""

    def test_gemini_fallback_when_import_fails(self):
        """Should fallback to OpenAI when langchain-google-genai is not installed."""
        from src.graph import get_model_for_role, DEFAULT_MODEL

        with patch.dict(os.environ, {"TEST_MODEL": "gemini-2.0-flash"}, clear=False):
            # Mock the import to raise ImportError
            original_import = __builtins__["__import__"]

            def mock_import(name, *args, **kwargs):
                if name == "langchain_google_genai":
                    raise ImportError("No module named 'langchain_google_genai'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with patch("src.graph.ChatOpenAI") as mock_openai:
                    mock_instance = MagicMock()
                    mock_openai.return_value = mock_instance

                    model = get_model_for_role("Test", "TEST_MODEL")

                    # Should fallback to OpenAI with default model
                    mock_openai.assert_called()
                    call_kwargs = mock_openai.call_args[1]
                    assert call_kwargs["model"] == DEFAULT_MODEL

    def test_anthropic_fallback_when_import_fails(self):
        """Should fallback to OpenAI when langchain-anthropic is not installed."""
        from src.graph import get_model_for_role, DEFAULT_MODEL

        with patch.dict(os.environ, {"TEST_MODEL": "claude-sonnet-4-20250514"}, clear=False):
            # Mock the import to raise ImportError
            original_import = __builtins__["__import__"]

            def mock_import(name, *args, **kwargs):
                if name == "langchain_anthropic":
                    raise ImportError("No module named 'langchain_anthropic'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with patch("src.graph.ChatOpenAI") as mock_openai:
                    mock_instance = MagicMock()
                    mock_openai.return_value = mock_instance

                    model = get_model_for_role("Test", "TEST_MODEL")

                    # Should fallback to OpenAI with default model
                    mock_openai.assert_called()
                    call_kwargs = mock_openai.call_args[1]
                    assert call_kwargs["model"] == DEFAULT_MODEL

    def test_deepseek_fallback_on_exception(self):
        """Should fallback to OpenAI when DeepSeek setup fails."""
        from src.graph import get_model_for_role, DEFAULT_MODEL

        with patch.dict(
            os.environ, {"TEST_MODEL": "deepseek-chat"}, clear=False
        ):
            # Remove DEEPSEEK_API_KEY to potentially cause issues
            if "DEEPSEEK_API_KEY" in os.environ:
                del os.environ["DEEPSEEK_API_KEY"]

            # Mock ChatOpenAI to track calls
            call_count = 0
            original_chat_openai = ChatOpenAI

            def mock_chat_openai(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1 and kwargs.get("base_url") == "https://api.deepseek.com":
                    # First call (DeepSeek) raises exception
                    raise Exception("DeepSeek API key missing")
                # Second call (fallback) succeeds
                return MagicMock()

            with patch("src.graph.ChatOpenAI", side_effect=mock_chat_openai):
                model = get_model_for_role("Test", "TEST_MODEL")

                # Should have attempted DeepSeek first, then fallback
                assert call_count == 2
                assert model is not None


class TestModelFactoryRoleLogging:
    """Tests for role-based logging output."""

    def test_logs_role_and_model_name(self, capsys):
        """Should print the role and model name being used."""
        from src.graph import get_model_for_role

        with patch.dict(os.environ, {"TEST_MODEL": "gpt-4o-mini"}, clear=False):
            with patch("src.graph.ChatOpenAI") as mock_openai:
                mock_instance = MagicMock()
                mock_openai.return_value = mock_instance

                get_model_for_role("Music Expert", "TEST_MODEL")

                captured = capsys.readouterr()
                assert "Music Expert" in captured.out
                assert "gpt-4o-mini" in captured.out
