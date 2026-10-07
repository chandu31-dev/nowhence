"""Public page views — home, about, shop, product detail."""

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from store.models import (
    HeroSection, FeaturedCollection, ShowcaseProduct,
    ParallaxSection, ShopBanner, StatItem, ContactInfo, AboutPage,
)


import shutil
import os
try:
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logo_black_192.png')
    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images', 'logo_black_192.png')
    shutil.copy(src, dst)
except Exception as e:
    print("Module level copy failed:", e)


def home(request):
    featured_collections = list(FeaturedCollection.objects.filter(is_active=True))

    # Batch-fetch linked product details in one query instead of N+1
    all_names = [fc.name for fc in featured_collections]
    product_map = {
        product.name: product
        for product in ShowcaseProduct.objects.filter(
            name__in=all_names,
            is_active=True,
        ).only('name', 'slug', 'blur_image', 'show_coming_soon')
    }
    for fc in featured_collections:
        linked_product = product_map.get(fc.name)
        fc.product_slug = linked_product.slug if linked_product else None
        fc.blur_image = linked_product.blur_image if linked_product else False
        fc.show_coming_soon = linked_product.show_coming_soon if linked_product else False

    context = {
        'hero': HeroSection.objects.filter(is_active=True).first(),
        'featured_collections': featured_collections,
        'showcase_products': ShowcaseProduct.objects.filter(is_active=True).only(
            'name', 'slug', 'image', 'price', 'discount_percent', 'discounted_price', 'category',
            'blur_image', 'show_coming_soon',
        ),
        'parallax': ParallaxSection.objects.filter(is_active=True).first(),
        'stats': StatItem.objects.filter(is_active=True),
        'contact': ContactInfo.objects.filter(is_active=True).first(),
    }
    return render(request, 'home.html', context)


def about(request):
    """About page — founder story and brand mission."""
    context = {
        'about': AboutPage.objects.filter(is_active=True).first(),
        'contact': ContactInfo.objects.filter(is_active=True).first(),
    }
    return render(request, 'about.html', context)


def shop(request):
    """Shop page — all products with category sidebar filtering."""
    category = request.GET.get('category', 'all')
    products = ShowcaseProduct.objects.filter(is_active=True).prefetch_related('variants').only(
        'name', 'slug', 'image', 'price', 'discount_percent', 'discounted_price', 'category',
        'blur_image', 'show_coming_soon',
    )
    if category and category != 'all':
        products = products.filter(category=category)

    # Paginate — 12 products per page
    paginator = Paginator(products, 12)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'categories': ShowcaseProduct.CATEGORY_CHOICES,
        'active_category': category,
        'shop_banner': ShopBanner.objects.filter(is_active=True).first(),
        'contact': ContactInfo.objects.filter(is_active=True).first(),
    }
    return render(request, 'shop.html', context)


def product_detail(request, slug):
    """Individual product detail page."""
    product = get_object_or_404(
        ShowcaseProduct.objects.prefetch_related('variants'),
        slug=slug,
        is_active=True,
    )
    gallery_images = product.images.only('image', 'alt_text', 'display_order')
    related_products = ShowcaseProduct.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk).only(
        'name', 'slug', 'image', 'price', 'discount_percent', 'discounted_price',
    )[:4]
    context = {
        'product': product,
        'product_variant_data': list(
            product.variants.values('size', 'color', 'color_hex', 'stock_quantity')
        ),
        'gallery_images': gallery_images,
        'related_products': related_products,
        'contact': ContactInfo.objects.filter(is_active=True).first(),
    }
    return render(request, 'product_detail.html', context)
