"""Email notification helpers for orders."""

import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_order_confirmation(order):
    """Send the customer a complete HTML and plain-text order receipt."""
    recipient_email = order.customer_email or order.user.email
    if not recipient_email:
        logger.warning('Order confirmation not sent for %s: customer has no email address.', order.order_number)
        return

    items = []
    for item in order.items.all():
        options = [
            f'Color: {item.color}' if item.color else '',
            f'Size: {item.size}' if item.size else '',
        ]
        items.append({
            'name': item.product_name,
            'options': ', '.join(option for option in options if option),
            'quantity': item.quantity,
            'unit_price': _format_currency(item.price),
            'total': _format_currency(item.total),
        })

    site_url = getattr(settings, 'PUBLIC_SITE_URL', 'https://NowhenceClothings.com').rstrip('/')
    context = {
        'customer_name': order.shipping_full_name or order.user.first_name or order.user.username,
        'order_number': order.order_number,
        'order_date': timezone.localtime(order.created_at).strftime('%d %b %Y, %I:%M %p'),
        'status': order.get_status_display(),
        'payment_method': order.get_payment_method_display(),
        'payment_status': order.get_payment_status_display(),
        'is_preorder': order.is_preorder,
        'amount_paid': _format_currency(order.amount_paid),
        'balance_due': _format_currency(order.balance_due),
        'items': items,
        'subtotal': _format_currency(order.subtotal),
        'coupon_code': order.coupon_code,
        'discount_amount': _format_currency(order.discount_amount),
        'shipping_charge': 'Free' if order.shipping_charge == 0 else _format_currency(order.shipping_charge),
        'total': _format_currency(order.total),
        'shipping_name': order.shipping_full_name,
        'shipping_phone': order.shipping_phone,
        'shipping_address': order.shipping_address,
        'shipping_city': order.shipping_city,
        'shipping_state': order.shipping_state,
        'shipping_pincode': order.shipping_pincode,
        'tracking_url': f'{site_url}/account/track-order/?order_number={order.order_number}',
    }
    message = render_to_string('emails/order_confirmation.txt', context)
    html_message = render_to_string('emails/order_confirmation.html', context)
    email = EmailMultiAlternatives(
        subject=f'Order confirmed — #{order.order_number} | Nowhence Clothings',
        body=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@NowhenceClothings.com'),
        to=[recipient_email],
    )
    email.attach_alternative(html_message, 'text/html')
    sent_count = email.send(fail_silently=False)
    if sent_count:
        logger.info('Order confirmation email sent for %s to %s', order.order_number, recipient_email)
    else:
        logger.error('Order confirmation email was not accepted for %s to %s', order.order_number, recipient_email)


def _format_currency(amount):
    return f'₹{amount:,.2f}'


def send_shipping_notification(order):
    """Send shipping update email when order status changes."""
    if not order.user.email:
        return

    status_messages = {
        'confirmed': 'Your order has been confirmed and is being prepared.',
        'shipped': f'Your order has been shipped! Tracking: {order.tracking_number or "Will be updated soon"}',
        'out_for_delivery': 'Your order is out for delivery. It should arrive today!',
        'delivered': 'Your order has been delivered. We hope you love it!',
        'cancelled': 'Your order has been cancelled. If you paid online, a refund will be processed within 7-10 business days.',
    }

    status_msg = status_messages.get(order.status)
    if not status_msg:
        return

    site_url = getattr(settings, 'PUBLIC_SITE_URL', 'https://NowhenceClothings.com').rstrip('/')
    message = f"""Hi {order.user.first_name or order.user.username},

{status_msg}

Order: #{order.order_number}
Status: {order.get_status_display()}

Track your order: {site_url}/account/track-order/?order_number={order.order_number}

— Nowhence Clothings
"""
    try:
        from django.core.mail import send_mail
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nowhenceclothings.com')
        send_mail(
            subject=f'Order #{order.order_number} — {order.get_status_display()} | Nowhence Clothings',
            message=message,
            from_email=from_email,
            recipient_list=[order.user.email],
        )
    except Exception as e:
        logger.error(f'Failed to send shipping email for {order.order_number}: {e}')
