"""Tests for support tools (sensitive operations requiring auth)."""

import pytest


class TestToolExistence:
    """Tests that all required support tools exist."""

    def test_get_customer_info_exists(self):
        """Support tools should have get_customer_info function."""
        from src.tools.support import get_customer_info

        assert get_customer_info is not None

    def test_get_invoice_exists(self):
        """Support tools should have get_invoice function."""
        from src.tools.support import get_invoice

        assert get_invoice is not None

    def test_process_refund_exists(self):
        """Support tools should have process_refund function."""
        from src.tools.support import process_refund

        assert process_refund is not None


class TestToolDecorators:
    """Tests that tools are properly decorated as LangChain tools."""

    def test_all_support_tools_are_langchain_tools(self):
        """All support tools should be decorated as LangChain tools."""
        from src.tools.support import get_customer_info, get_invoice, process_refund

        for tool in [get_customer_info, get_invoice, process_refund]:
            assert hasattr(tool, "name"), f"{tool} should be a LangChain @tool"
            assert hasattr(tool, "description"), f"{tool} needs a docstring"

    def test_process_refund_has_meaningful_docstring(self):
        """process_refund must have a clear docstring for HITL triggering."""
        from src.tools.support import process_refund

        assert "refund" in process_refund.description.lower()


class TestToolFunctionality:
    """Integration tests for tool database queries."""

    @pytest.mark.integration
    def test_get_customer_info_returns_customer_data(self, test_config):
        """get_customer_info should return customer details."""
        from src.tools.support import get_customer_info

        # Customer ID 1 exists in Chinook (from test_config)
        result = get_customer_info.invoke({}, config=test_config)

        assert result is not None
        assert "1" in str(result)  # Customer ID should be in result

    @pytest.mark.integration
    def test_get_invoice_returns_invoice_data(self, test_config):
        """get_invoice should return invoice details for a customer."""
        from src.tools.support import get_invoice

        # Customer 1 has invoices in Chinook (from test_config)
        result = get_invoice.invoke({}, config=test_config)

        assert result is not None

    @pytest.mark.integration
    def test_process_refund_returns_confirmation(self, test_config):
        """process_refund should return a confirmation message."""
        from src.tools.support import process_refund

        # Invoice 98 belongs to customer 1 (from test_config)
        result = process_refund.invoke({"invoice_id": 98}, config=test_config)

        assert result is not None
        assert "refund" in result.lower() or "initiated" in result.lower()

    @pytest.mark.integration
    def test_process_refund_rejects_other_customer_invoice(self, test_config):
        """process_refund should reject invoices that don't belong to the customer.

        This tests the security fix: customer_id comes from config (authenticated
        session), not from LLM parameters, preventing cross-customer data access.
        """
        from src.tools.support import process_refund

        # Invoice 1 belongs to customer 2, but test_config has customer_id=1
        result = process_refund.invoke({"invoice_id": 1}, config=test_config)

        assert "not found in your account" in result.lower()
