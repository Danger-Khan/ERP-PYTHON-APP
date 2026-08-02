import urllib.parse
from app.utils.logger import log_event

class NotificationService:
    """Handles generation of customer notifications via WhatsApp API links or SMS standard formatting."""

    @staticmethod
    def format_whatsapp_url(phone: str, message: str) -> str:
        """Generates a direct WhatsApp web/api click-to-send URL."""
        # Clean phone number (e.g., convert +923001234567 or 03001234567 to 923001234567)
        clean_phone = ''.join(filter(str.isdigit, phone))
        if clean_phone.startswith('0'):
            clean_phone = '92' + clean_phone[1:]

        encoded_message = urllib.parse.quote(message)
        return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"

    @classmethod
    def send_order_confirmation(cls, customer_name: str, phone: str, invoice_no: str, amount: float, balance: float) -> dict:
        msg = (
            f"Dear {customer_name},\n"
            f"Thank you for choosing our Atelier! Your order #{invoice_no} has been confirmed.\n"
            f"Total Amount: PKR {amount:.2f}\n"
            f"Remaining Balance: PKR {balance:.2f}\n"
            f"We will notify you when your order is ready for fitting."
        )
        url = cls.format_whatsapp_url(phone, msg)
        log_event("NOTIFICATION", f"Generated order confirmation link for {customer_name} ({phone})")
        return {"phone": phone, "whatsapp_url": url, "message_text": msg}

    @classmethod
    def send_order_ready_notice(cls, customer_name: str, phone: str, invoice_no: str, balance: float) -> dict:
        msg = (
            f"Dear {customer_name},\n"
            f"Great news! Your suit (Order #{invoice_no}) is now READY for pickup!\n"
            f"Remaining Balance Due: PKR {balance:.2f}\n"
            f"Please visit our shop during operating hours."
        )
        url = cls.format_whatsapp_url(phone, msg)
        log_event("NOTIFICATION", f"Generated ready notice for {customer_name} ({phone})")
        return {"phone": phone, "whatsapp_url": url, "message_text": msg}