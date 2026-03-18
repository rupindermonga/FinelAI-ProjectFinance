"""Default column configuration seeded for every new user."""
from sqlalchemy.orm import Session
from .models import ColumnConfig


DEFAULT_COLUMNS = [
    # ── Invoice Header ──────────────────────────────────────────────
    dict(field_key="invoice_number",    field_label="Invoice #",           field_description="The invoice or bill number",                                              field_type="string",  is_system=True,  display_order=1),
    dict(field_key="invoice_date",      field_label="Invoice Date",        field_description="The date the invoice was issued",                                         field_type="date",    is_system=True,  display_order=2),
    dict(field_key="due_date",          field_label="Due Date",            field_description="The payment due date",                                                    field_type="date",    is_system=False, display_order=3),
    dict(field_key="po_number",         field_label="PO Number",           field_description="Purchase order number referenced on the invoice",                         field_type="string",  is_system=False, display_order=4),
    dict(field_key="payment_terms",     field_label="Payment Terms",       field_description="Payment terms such as Net 30, Due on Receipt, etc.",                      field_type="string",  is_system=False, display_order=5),
    dict(field_key="currency",          field_label="Currency",            field_description="Currency code (CAD, USD, EUR, etc.)",                                     field_type="string",  is_system=True,  display_order=6),

    # ── Classification (driven by user-configured categories) ──────
    dict(field_key="category",          field_label="Category",            field_description="Category of this invoice — see allowed values in system prompt",          field_type="string",  is_system=False, display_order=7),
    dict(field_key="sub_category",      field_label="Sub-Category",        field_description="Sub-category within the main category — see allowed values",              field_type="string",  is_system=False, display_order=8),
    dict(field_key="sub_division",      field_label="Sub-Division",        field_description="Sub-division for construction/trade invoices (e.g. CSI division) — see allowed values", field_type="string", is_system=False, display_order=9),

    # ── Vendor ───────────────────────────────────────────────────────
    dict(field_key="vendor_name",       field_label="Vendor",              field_description="Name of the vendor or supplier issuing the invoice",                      field_type="string",  is_system=True,  display_order=10),
    dict(field_key="vendor_address",    field_label="Vendor Address",      field_description="Full address of the vendor",                                              field_type="string",  is_system=False, display_order=11),
    dict(field_key="vendor_email",      field_label="Vendor Email",        field_description="Email address of the vendor",                                             field_type="string",  is_system=False, display_order=12),
    dict(field_key="vendor_phone",      field_label="Vendor Phone",        field_description="Phone number of the vendor",                                              field_type="string",  is_system=False, display_order=13),
    dict(field_key="vendor_tax_id",     field_label="Vendor Tax ID",       field_description="Tax ID, VAT number, GST number, or business registration of the vendor", field_type="string",  is_system=False, display_order=14),
    dict(field_key="vendor_bank",       field_label="Bank / Payment Info", field_description="Bank account, IBAN, SWIFT, or payment instructions from vendor",          field_type="string",  is_system=False, display_order=15),

    # ── Bill To ───────────────────────────────────────────────────────
    dict(field_key="bill_to_name",      field_label="Bill To",             field_description="Name of the customer or company being billed",                            field_type="string",  is_system=False, display_order=20),
    dict(field_key="bill_to_address",   field_label="Bill To Address",     field_description="Billing address of the customer",                                         field_type="string",  is_system=False, display_order=21),

    # ── Manufacturer (invoice-level, for material invoices) ──────────
    dict(field_key="manufacturer",      field_label="Manufacturer",        field_description="Manufacturer or brand name for material/product invoices. Use null for service invoices.", field_type="string", is_system=False, display_order=22),

    # ── Totals ────────────────────────────────────────────────────────
    dict(field_key="subtotal",          field_label="Invoice Total (Excl. Tax)", field_description="Subtotal / invoice total before taxes",                             field_type="number",  is_system=False, display_order=30),
    dict(field_key="discount_total",    field_label="Discount",            field_description="Total discount amount applied",                                            field_type="number",  is_system=False, display_order=31),
    dict(field_key="tax_total",         field_label="Tax Amount",          field_description="Total tax amount (combine all: GST, HST, PST, VAT)",                      field_type="number",  is_system=False, display_order=32),
    dict(field_key="shipping",          field_label="Shipping / Freight",  field_description="Shipping or freight charges",                                             field_type="number",  is_system=False, display_order=33),
    dict(field_key="other_charges",     field_label="Other Charges",       field_description="Any other fees or charges on the invoice",                                field_type="number",  is_system=False, display_order=34),
    dict(field_key="total_due",         field_label="Invoice Total (Incl. Tax)", field_description="Total amount due for payment including all taxes",                  field_type="number",  is_system=True,  display_order=35),

    # ── Line Items ────────────────────────────────────────────────────
    # Each line item includes: line_no, manufacturer, sku, description,
    # qty, unit, unit_price, discount_amount, tax_rate, line_total,
    # sub_division (for construction lines)
    dict(field_key="line_items",        field_label="Line Items",          field_description="All line items. Each item: {line_no, manufacturer, sku, description, qty, unit, unit_price, discount_amount, tax_rate, line_total, sub_division}", field_type="array", is_system=False, display_order=40),

    # ── Notes ─────────────────────────────────────────────────────────
    dict(field_key="notes",             field_label="Notes / Points to Note", field_description="Any notes, comments, special instructions, or important points on the invoice", field_type="string", is_system=False, display_order=50),
]


# Columns added after initial release — used to patch existing users
NEW_COLUMNS = [
    dict(field_key="category",     field_label="Category",              field_description="Category of this invoice — see allowed values in system prompt",          field_type="string",  is_system=False, display_order=7),
    dict(field_key="sub_category", field_label="Sub-Category",          field_description="Sub-category within the main category — see allowed values",              field_type="string",  is_system=False, display_order=8),
    dict(field_key="sub_division", field_label="Sub-Division",          field_description="Sub-division for construction/trade invoices — see allowed values",       field_type="string",  is_system=False, display_order=9),
    dict(field_key="manufacturer", field_label="Manufacturer",          field_description="Manufacturer or brand name for material/product invoices",                field_type="string",  is_system=False, display_order=22),
]


def seed_default_columns(db: Session, user_id: int):
    """Seed default columns for a new user."""
    existing = db.query(ColumnConfig).filter(ColumnConfig.user_id == user_id).count()
    if existing > 0:
        return
    for col in DEFAULT_COLUMNS:
        db.add(ColumnConfig(user_id=user_id, **col))
    db.commit()


def patch_existing_user_columns(db: Session, user_id: int):
    """Add any missing columns to an existing user (run on login or startup)."""
    existing_keys = {
        c.field_key for c in db.query(ColumnConfig).filter(ColumnConfig.user_id == user_id).all()
    }
    added = False
    for col in NEW_COLUMNS:
        if col["field_key"] not in existing_keys:
            db.add(ColumnConfig(user_id=user_id, **col))
            added = True
    if added:
        db.commit()
