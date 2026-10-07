from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from .models import (
    HeroSection, FeaturedCollection, ShowcaseProduct, ProductImage, ProductVariant,
    CollectionCard, ParallaxSection, ShopBanner, StatItem, ContactInfo, AboutPage,
    PincodeAvailability, Address, Order, OrderItem, ReturnExchange, UserProfile,
    ContactMessage, Wishlist, Review, Coupon,
)


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'media_type', 'media_preview', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'media_type')
    fieldsets = (
        (None, {'fields': ('title', 'subtitle')}),
        ('Background Media', {
            'fields': ('media_type', 'background_image', 'background_video'),
            'description': 'Choose Image or Video, then upload the corresponding file. MP4 is recommended for videos.'
        }),
        ('Status', {'fields': ('is_active',)}),
    )

    def media_preview(self, obj):
        if obj.media_type == 'video' and obj.background_video:
            return format_html(
                '<video src="{}" style="height:50px; border-radius:4px;" muted></video> 🎬',
                obj.background_video.url
            )
        elif obj.background_image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.background_image.url)
        return '-'
    media_preview.short_description = 'Preview'


@admin.register(FeaturedCollection)
class FeaturedCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'formatted_price', 'discount_percent', 'formatted_discounted_price', 'image_preview', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'discount_percent')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {'fields': ('name', 'description', 'image')}),
        ('Pricing', {'fields': ('price', 'discount_percent', 'discounted_price'), 'description': 'Set original price and discount. Discounted price auto-calculates if left blank.'}),
        ('Display', {'fields': ('display_order', 'is_active')}),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'display_order', 'image_preview')
    readonly_fields = ('image_preview',)
    ordering = ('display_order',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px; border-radius:6px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('size', 'color', 'color_hex', 'sku', 'stock_quantity')
    ordering = ('color', 'size')


class PincodeAvailabilityInline(admin.TabularInline):
    model = PincodeAvailability
    extra = 1
    fields = ('pincode', 'is_available', 'delivery_days', 'extra_charge', 'updated_at')
    readonly_fields = ('updated_at',)
    ordering = ('pincode',)


@admin.register(ShowcaseProduct)
class ShowcaseProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'formatted_price', 'discount_percent', 'formatted_discounted_price', 'inventory_stock', 'image_preview', 'show_coming_soon', 'preorder_enabled', 'blur_image', 'display_order', 'is_active')
    list_editable = ('show_coming_soon', 'preorder_enabled', 'blur_image', 'display_order', 'is_active')
    list_filter = ('is_active', 'category', 'discount_percent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'category', 'image')}),
        ('Description', {'fields': ('description', 'fabric', 'care_instructions')}),
        ('Sizing', {'fields': ('available_sizes',), 'description': 'Comma-separated sizes e.g. S,M,L,XL,XXL'}),
        ('Pricing', {'fields': ('price', 'discount_percent', 'discounted_price'), 'description': 'Set original price and discount. Discounted price auto-calculates if left blank.'}),
        ('Stock', {'fields': ('stock_quantity',), 'description': 'Set to 0 when out of stock.'}),
        ('Product launch visuals', {
            'fields': ('blur_image', 'show_coming_soon', 'preorder_enabled'),
            'description': 'Enable pre-orders to accept this product while it is coming soon or out of stock. Pre-orders require Razorpay and a ₹500 advance per order.',
        }),
        ('Display', {'fields': ('display_order', 'is_active')}),
    )
    inlines = [ProductImageInline, ProductVariantInline, PincodeAvailabilityInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'

    @admin.display(description='Available stock')
    def inventory_stock(self, obj):
        return obj.total_stock


@admin.register(CollectionCard)
class CollectionCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'image_preview', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(ParallaxSection)
class ParallaxSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'image_preview', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)

    def image_preview(self, obj):
        if obj.background_image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.background_image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(ShopBanner)
class ShopBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'media_preview', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'media_type')
    fieldsets = (
        (None, {'fields': ('title', 'subtitle', 'badge_text')}),
        ('Background Media', {
            'fields': ('media_type', 'background_image', 'background_video', 'overlay_opacity'),
            'description': 'Choose Pattern (default gradient), Image, or Video. Upload the corresponding file.'
        }),
        ('Status', {'fields': ('is_active',)}),
    )

    def media_preview(self, obj):
        if obj.media_type == 'video' and obj.background_video:
            return format_html(
                '<video src="{}" style="height:50px; border-radius:4px;" muted></video> 🎬',
                obj.background_video.url
            )
        elif obj.media_type == 'image' and obj.background_image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.background_image.url)
        return '🎨 Pattern'
    media_preview.short_description = 'Preview'


@admin.register(StatItem)
class StatItemAdmin(admin.ModelAdmin):
    list_display = ('number', 'label', 'icon', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active',)
    ordering = ('display_order',)


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('phone', 'email', 'address', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    fieldsets = (
        ('Contact Details', {'fields': ('phone', 'email', 'address')}),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'pinterest_url', 'youtube_url', 'whatsapp_number'),
            'description': 'Leave blank to hide that social link.'
        }),
        ('Status', {'fields': ('is_active',)}),
    )


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ('heading', 'founder_name', 'image_preview', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    fieldsets = (
        ('Page Header', {'fields': ('heading', 'subheading')}),
        ('Founder', {'fields': ('founder_name', 'founder_title')}),
        ('Story', {
            'fields': ('story_text', 'quote_text'),
            'description': 'Write the founder\'s story and an optional inspirational quote.'
        }),
        ('Mission', {
            'fields': ('mission_title', 'mission_text'),
            'description': 'Brand mission section (optional).'
        }),
        ('Images', {
            'fields': ('main_image', 'secondary_image'),
            'description': 'Main image appears on the left side. Secondary image is optional for visual depth.'
        }),
        ('Status', {'fields': ('is_active',)}),
    )

    def image_preview(self, obj):
        if obj.main_image:
            return format_html('<img src="{}" style="height:50px; border-radius:4px;" />', obj.main_image.url)
        return '-'
    image_preview.short_description = 'Preview'

@admin.register(PincodeAvailability)
class PincodeAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('product', 'pincode', 'availability_status', 'is_available', 'delivery_days', 'extra_charge', 'updated_at')
    list_filter = ('is_available', 'product', 'updated_at')
    list_editable = ('is_available', 'delivery_days', 'extra_charge')
    search_fields = ('product__name', 'pincode')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Product & Pincode', {'fields': ('product', 'pincode')}),
        ('Availability', {
            'fields': ('is_available', 'delivery_days', 'extra_charge'),
            'description': 'Set whether this product is available in the pincode, delivery days, and any extra shipping charges.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def availability_status(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green; font-weight: bold;">✓ Available</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Unavailable</span>')
    availability_status.short_description = 'Status'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'label', 'city', 'state', 'pincode', 'is_default')
    list_filter = ('label', 'is_default', 'state')
    search_fields = ('full_name', 'city', 'pincode', 'user__username')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'google_id', 'facebook_id', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone', 'google_id', 'facebook_id')
    list_filter = ('created_at',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'variant', 'product_name', 'product_image', 'size', 'color', 'quantity', 'price', 'total')
    readonly_fields = ('total',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'status_badge', 'is_preorder', 'payment_status', 'formatted_total', 'formatted_amount_paid', 'formatted_balance_due', 'tracking_number', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    list_editable = ('status', 'payment_status')
    search_fields = ('order_number', 'user__username', 'user__email', 'tracking_number', 'shipping_full_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'cancelled_at')
    inlines = [OrderItemInline]
    actions = (
        'mark_orders_confirmed',
        'mark_orders_shipped',
        'mark_orders_out_for_delivery',
        'mark_orders_delivered',
    )
    fieldsets = (
        ('Order Info', {'fields': ('order_number', 'user', 'status', 'payment_status', 'payment_method', 'is_preorder', 'amount_paid')}),
        ('Shipping Address', {'fields': ('shipping_full_name', 'shipping_phone', 'shipping_address', 'shipping_city', 'shipping_state', 'shipping_pincode')}),
        ('Tracking', {'fields': ('tracking_number', 'courier_name', 'estimated_delivery', 'delivered_at')}),
        ('Pricing', {'fields': ('subtotal', 'shipping_charge', 'coupon_code', 'discount_amount', 'total')}),
        ('Cancellation', {'fields': ('cancellation_reason', 'cancelled_at'), 'classes': ('collapse',)}),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def _set_selected_order_status(self, request, queryset, status):
        updated = 0
        for order in queryset.select_related('user'):
            if order.status == status:
                continue

            order.status = status
            update_fields = ['status', 'updated_at']
            if status == 'delivered' and order.delivered_at is None:
                order.delivered_at = timezone.now()
                update_fields.append('delivered_at')
            order.save(update_fields=update_fields)
            updated += 1

        label = dict(Order.STATUS_CHOICES)[status]
        self.message_user(
            request,
            f'{updated} order(s) marked as {label.lower()}.',
            level=messages.SUCCESS,
        )

    @admin.action(description='Mark selected orders as confirmed')
    def mark_orders_confirmed(self, request, queryset):
        self._set_selected_order_status(request, queryset, 'confirmed')

    @admin.action(description='Mark selected orders as shipped')
    def mark_orders_shipped(self, request, queryset):
        self._set_selected_order_status(request, queryset, 'shipped')

    @admin.action(description='Mark selected orders as out for delivery')
    def mark_orders_out_for_delivery(self, request, queryset):
        self._set_selected_order_status(request, queryset, 'out_for_delivery')

    @admin.action(description='Mark selected orders as delivered')
    def mark_orders_delivered(self, request, queryset):
        self._set_selected_order_status(request, queryset, 'delivered')

    def status_badge(self, obj):
        colors = {
            'pending': '#f39c12',
            'confirmed': '#3498db',
            'shipped': '#9b59b6',
            'out_for_delivery': '#e67e22',
            'delivered': '#27ae60',
            'cancelled': '#e74c3c',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        """Record delivery time when an admin changes an order to delivered."""
        if change and 'status' in form.changed_data:
            if obj.status == 'delivered' and obj.delivered_at is None:
                obj.delivered_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ReturnExchange)
class ReturnExchangeAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'request_type', 'reason', 'status', 'status_badge', 'formatted_refund', 'created_at')
    list_filter = ('request_type', 'status', 'reason', 'created_at')
    list_editable = ('status',)
    search_fields = ('order__order_number', 'user__username', 'details')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Request', {'fields': ('user', 'order', 'order_item', 'request_type', 'reason', 'details')}),
        ('Status', {'fields': ('status', 'refund_amount', 'admin_notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def status_badge(self, obj):
        colors = {
            'requested': '#f39c12',
            'approved': '#3498db',
            'pickup_scheduled': '#9b59b6',
            'picked_up': '#e67e22',
            'completed': '#27ae60',
            'rejected': '#e74c3c',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    list_editable = ('is_read',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Sender', {'fields': ('name', 'email', 'phone')}),
        ('Message', {'fields': ('subject', 'message')}),
        ('Status', {'fields': ('is_read', 'created_at')}),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'star_display', 'title', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    list_editable = ('is_approved',)
    search_fields = ('product__name', 'user__username', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')

    def star_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color:#f39c12;">{}</span>', stars)
    star_display.short_description = 'Stars'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_display', 'min_order_amount', 'used_count', 'usage_limit', 'is_active', 'valid_until')
    list_filter = ('is_active', 'discount_type', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('code', 'description')
    readonly_fields = ('used_count', 'created_at')
    fieldsets = (
        (None, {'fields': ('code', 'description')}),
        ('Discount', {'fields': ('discount_type', 'discount_value', 'max_discount')}),
        ('Conditions', {'fields': ('min_order_amount', 'usage_limit', 'per_user_limit')}),
        ('Validity', {'fields': ('is_active', 'valid_from', 'valid_until')}),
        ('Stats', {'fields': ('used_count', 'created_at'), 'classes': ('collapse',)}),
    )

    def discount_display(self, obj):
        if obj.discount_type == 'percent':
            return f'{obj.discount_value:.0f}%'
        return f'₹{obj.discount_value:.0f}'
    discount_display.short_description = 'Discount'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'product__name')


# ── Admin site customisation ──
admin.site.site_header = 'Nowhence Clothings Store Management'
admin.site.site_title = 'Nowhence Clothings Store'
admin.site.index_title = 'Store management'
admin.site.index_template = 'admin/store_dashboard.html'