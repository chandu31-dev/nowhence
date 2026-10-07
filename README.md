# Nowhence Clothings

A luxury T-shirt e-commerce website built with Django.

## Features

- **Product Catalog** — Premium T-shirts, graphic tees, polos, and oversized fits with filtering, search, sizes, and color variants
- **Inventory** — Stock tracked independently for every configured size/color combination; products without variants retain shared-stock support
- **Product Detail** — Image gallery, size guide, color and size selection, pincode availability checker
- **Shopping Cart** — Drawer-based cart with localStorage persistence
- **Multi-step Checkout** — Account → Shipping → Review flow
- **Authentication** — Username/password login, Phone OTP login, Google sign-in, signup
- **Customer Portal** — Profile management, addresses, order history, order tracking, returns & exchanges
- **Admin Panel** — Django admin for managing products, orders, hero section, collections, and more
- **Dark Mode** — System-aware theme toggle with smooth transitions
- **Responsive Design** — Fully mobile-optimized with hamburger menu, collapsible sections
- **Smooth Animations** — Page transitions, scroll effects, parallax sections

## Tech Stack

- **Backend:** Django 6.x, Python 3.12 (Elastic Beanstalk target)
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** Vanilla HTML/CSS/JS, Font Awesome icons
- **Smooth Scroll:** Lenis

## Setup

```bash
# Open the project folder (replace the path with its location on your machine)
cd path/to/nowhenceclothings-main

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --settings mysite.settings.dev

# Create superuser (admin)
python manage.py createsuperuser --settings mysite.settings.dev

# Add products and inventory in Django admin. For variant-level inventory,
# add a separate size/color variant and stock quantity for each combination.

# Run the server
python manage.py runserver --settings mysite.settings.dev
```

Open the development site at `http://127.0.0.1:8000/`. Development settings serve plain HTTP; HTTPS redirection is enabled only by production settings.

## PostgreSQL for Local Development

Development uses SQLite when `DATABASE_URL` is not set. To use PostgreSQL instead, add your PostgreSQL URL to the ignored local `.env` file (not `.env.example`):

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE_NAME
```

Then run `python manage.py migrate --settings mysite.settings.dev` to create the empty Django schema in PostgreSQL, followed by `python manage.py runserver --settings mysite.settings.dev`. This does not copy SQLite data. Keep the database URL and password private, and URL-encode reserved characters in the password.

## Order Confirmation Emails

Customers receive an order confirmation after a Cash on Delivery order is confirmed or an online payment succeeds. The email includes the order items, quantities, prices, totals, payment status, delivery address, and a tracking link. For local SMTP testing, copy `.env.example` to `.env` and set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`. Development uses SMTP when the host, username, and password are set; otherwise it prints emails to the server console. Production uses SMTP with the same values provided as hosting environment variables. Never commit `.env` or SMTP credentials.

## Google Sign-in

1. Create an OAuth 2.0 Client ID for a Web application in Google Cloud Console and configure the OAuth consent screen.
2. Add `http://127.0.0.1:8000/account/google/callback/` as an authorized redirect URI. Add `https://your-domain/account/google/callback/` for production.
3. Copy `.env.example` to `.env` and set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. For deployment, set these as environment variables instead. Do not commit `.env`.

Google sign-in requests the `openid`, `email`, and `profile` scopes and rejects unverified email addresses.

## Project Structure

```
├── mysite/              # Django project settings & main views
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   └── static/          # CSS, JS, images
├── store/               # Django app — models, admin, migrations
├── templates/           # HTML templates
├── media/               # User-uploaded content (not tracked)
└── manage.py
```
