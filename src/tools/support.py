"""Support tools for the Music Store Assistant.

These are SENSITIVE tools for account operations.
Used by the Support_Rep node. process_refund triggers HITL approval.

SECURITY NOTE: Tools that access customer data read customer_id from the
RunnableConfig, NOT from LLM parameters. The config parameter is hidden from
the LLM's tool schema, preventing prompt injection attacks from accessing
other customers' data.
"""

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from src.utils import get_db


def _get_customer_id(config: RunnableConfig) -> int:
    """Extract customer_id from config, raising error if not found."""
    customer_id = config.get("configurable", {}).get("customer_id")
    if customer_id is None:
        raise ValueError("customer_id not found in config - authentication required")
    return int(customer_id)


@tool
def get_customer_info(config: RunnableConfig) -> str:
    """Look up YOUR customer information.

    Use this tool to retrieve your profile details like name,
    email, address, and contact information.

    Returns:
        Customer profile information as a formatted string.
    """
    customer_id = _get_customer_id(config)
    db = get_db()
    return db.run(
        f"""
        SELECT CustomerId, FirstName, LastName, Email, Phone, Address, City, Country
        FROM Customer 
        WHERE CustomerId = {customer_id};
        """,
        include_columns=True,
    )


@tool
def get_invoice(invoice_id: int | None = None, *, config: RunnableConfig) -> str:
    """Get YOUR invoice information.

    Use this tool to:
    - Look up a specific invoice by ID (provide invoice_id)
    - Get your invoice history (no arguments needed)

    Args:
        invoice_id: Optional. If provided, returns just that specific invoice.

    Returns:
        Invoice information as a formatted string.
    """
    customer_id = _get_customer_id(config)
    db = get_db()

    if invoice_id is not None:
        # Look up a specific invoice - MUST belong to this customer
        result = db.run(
            f"""
            SELECT InvoiceId, InvoiceDate, BillingCity, BillingCountry, Total
            FROM Invoice
            WHERE CustomerId = {customer_id} AND InvoiceId = {invoice_id};
            """,
            include_columns=True,
        )
        if not result or result == "[]":
            return f"Invoice {invoice_id} not found in your account."
        return result
    else:
        # Get all invoices for customer
        return db.run(
            f"""
            SELECT InvoiceId, InvoiceDate, BillingCity, BillingCountry, Total
            FROM Invoice
            WHERE CustomerId = {customer_id}
            ORDER BY InvoiceDate DESC
            LIMIT 10;
            """,
            include_columns=True,
        )


@tool
def process_refund(invoice_id: int, *, config: RunnableConfig) -> str:
    """Process a refund for one of YOUR invoices.

    IMPORTANT: This is a sensitive operation that requires human approval.
    The graph will interrupt before executing this tool to allow
    a human operator to review and approve the refund request.

    Use this tool when you want a refund for one of your purchases.

    Args:
        invoice_id: The unique identifier for the invoice to refund.

    Returns:
        Confirmation message for the refund initiation.
    """
    customer_id = _get_customer_id(config)
    db = get_db()

    # Verify the invoice exists AND belongs to this customer
    invoice_info = db.run(
        f"""
        SELECT InvoiceId, Total, CustomerId
        FROM Invoice
        WHERE InvoiceId = {invoice_id} AND CustomerId = {customer_id};
        """
    )

    if not invoice_info or invoice_info == "[]":
        return f"Error: Invoice {invoice_id} not found in your account."

    return f"Refund initiated for Invoice #{invoice_id}. The refund will be processed within 3-5 business days."


# Export all support tools as a list for easy binding
SUPPORT_TOOLS = [get_customer_info, get_invoice, process_refund]

# Safe tools (no approval needed)
SAFE_SUPPORT_TOOLS = [get_customer_info, get_invoice]

# Tools that require HITL approval
HITL_SUPPORT_TOOLS = [process_refund]
HITL_TOOLS = ["process_refund"]
