"""Support tools for the Music Store Assistant.

These are SENSITIVE tools for account operations.
Used by the Support_Rep node. process_refund triggers HITL approval.
"""

from langchain_core.tools import tool
from src.utils import get_db


@tool
def get_customer_info(customer_id: int) -> str:
    """Look up customer information by their ID.

    Use this tool to retrieve customer profile details like name,
    email, address, and contact information.

    Args:
        customer_id: The unique identifier for the customer.

    Returns:
        Customer profile information as a formatted string.
    """
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
def get_invoice(customer_id: int, invoice_id: int | None = None) -> str:
    """Get invoice information for a customer.

    Use this tool to:
    - Look up a specific invoice by ID (provide both customer_id and invoice_id)
    - Get a customer's invoice history (provide only customer_id)

    Args:
        customer_id: The unique identifier for the customer.
        invoice_id: Optional. If provided, returns just that specific invoice.

    Returns:
        Invoice information as a formatted string.
    """
    db = get_db()

    if invoice_id is not None:
        # Look up a specific invoice
        result = db.run(
            f"""
            SELECT InvoiceId, InvoiceDate, BillingCity, BillingCountry, Total
            FROM Invoice
            WHERE CustomerId = {customer_id} AND InvoiceId = {invoice_id};
            """,
            include_columns=True,
        )
        if not result or result == "[]":
            # Maybe try without customer_id filter in case they got it wrong
            result = db.run(
                f"""
                SELECT InvoiceId, InvoiceDate, BillingCity, BillingCountry, Total, CustomerId
                FROM Invoice
                WHERE InvoiceId = {invoice_id};
                """,
                include_columns=True,
            )
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
def process_refund(invoice_id: int) -> str:
    """Process a refund for a specific invoice.

    IMPORTANT: This is a sensitive operation that requires human approval.
    The graph will interrupt before executing this tool to allow
    a human operator to review and approve the refund request.

    Use this tool when a customer requests a refund for a purchase.

    Args:
        invoice_id: The unique identifier for the invoice to refund.

    Returns:
        Confirmation message for the refund initiation.
    """
    # In production, this would integrate with a payment processor
    # For MVP, we return a mock confirmation
    db = get_db()

    # Verify the invoice exists
    invoice_info = db.run(
        f"""
        SELECT InvoiceId, Total, CustomerId
        FROM Invoice
        WHERE InvoiceId = {invoice_id};
        """
    )

    if not invoice_info or invoice_info == "[]":
        return f"Error: Invoice {invoice_id} not found."

    return f"Refund initiated for Invoice #{invoice_id}. The refund will be processed within 3-5 business days."


# Export all support tools as a list for easy binding
SUPPORT_TOOLS = [get_customer_info, get_invoice, process_refund]

# Safe tools (no approval needed)
SAFE_SUPPORT_TOOLS = [get_customer_info, get_invoice]

# Tools that require HITL approval
HITL_SUPPORT_TOOLS = [process_refund]
HITL_TOOLS = ["process_refund"]
