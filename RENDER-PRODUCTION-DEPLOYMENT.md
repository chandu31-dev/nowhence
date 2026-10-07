# Render production deployment guide

This guide uses a Render Python web service, Render PostgreSQL, Render Key Value (Redis), and a persistent disk for uploaded media. It uses the included `mysite.settings.render` production settings rather than AWS-only `mysite.settings.prod`.

## Important constraints

- Render deploys from a Git repository, not by uploading this ZIP as a source bundle. Extract the ZIP, create a private GitHub/GitLab repository, and push the extracted application. Keep the ZIP as a backup/release artifact.
- This configuration stores uploaded media on a Render persistent disk mounted at `/var/data`. Render disks require a paid web service, and a service with an attached disk cannot scale to multiple instances. Start with one instance. For horizontal scaling, migrate media to a shared S3-compatible object store and change the media storage configuration.
- Use a paid Render PostgreSQL plan with backups appropriate for production. Confirm current pricing, retention, and service-region availability in the Render dashboard.
- Do not use the free web service or an ephemeral filesystem for production media. Files not written under the persistent disk mount can disappear on restart or redeploy.

## Step 1 — Prepare the source repository

1. Extract `NowhenceClothings-Production-20261008.zip` into a clean directory.
2. Verify the extracted root contains `manage.py`, `requirements.txt`, `Procfile`, `mysite/`, `store/`, `templates/`, and this guide.
3. Create a private Git repository and push the extracted files.
4. Do not include `.env`, database files, uploaded local media, virtual environments, or credentials. The production ZIP is already built to exclude these.

## Step 2 — Create Render services

Create the resources in the same Render region:

1. Create a paid **PostgreSQL** database. In its dashboard, copy the **Internal Database URL** for the app service.
2. Create a **Key Value** service (Redis) in the same region. Restrict inbound access to the web service where the dashboard allows it. Copy its internal connection URL.
3. Create a **Web Service** from the private repository. Choose the Python runtime, select a paid instance, and configure a persistent disk:
   - Mount path: `/var/data`
   - Size: start with the smallest size that covers expected uploads; disk size may be increased later.
4. Keep the Web Service at one instance while using local persistent-disk media.

## Step 3 — Configure build and deployment commands

Set the web service commands:

- **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Pre-deploy command:** `python manage.py migrate --noinput`
- **Start command:** `gunicorn mysite.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`

If the dashboard does not offer a separate pre-deploy command for your service plan, use this single-instance start command instead:

```sh
python manage.py migrate --noinput && exec gunicorn mysite.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
```

The second form runs migrations at process startup. Keep one instance during deployment and do not use it with concurrent autoscaled instances.

## Step 4 — Add environment variables

Set these in the Render Web Service's **Environment** page. Keep secret values only in Render's secret environment variables.

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `mysite.settings.render` |
| `DJANGO_SECRET_KEY` | Generate a new unique secret (Render can generate a secret value) |
| `DJANGO_ALLOWED_HOSTS` | Render hostname and any custom domain hostnames, comma-separated, no scheme |
| `CSRF_TRUSTED_ORIGINS` | HTTPS origins, comma-separated; e.g. `https://your-service.onrender.com,https://shop.example.com` |
| `PUBLIC_SITE_URL` | Canonical HTTPS URL of the site |
| `DATABASE_URL` | Render PostgreSQL **Internal Database URL** |
| `REDIS_URL` | Render Key Value internal URL; set the scheme the dashboard supplies (`redis://` or `rediss://`) |
| `MEDIA_ROOT` | `/var/data/media` |
| `EMAIL_HOST` | SES SMTP endpoint, e.g. `email-smtp.ap-south-1.amazonaws.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | SES SMTP username |
| `EMAIL_HOST_PASSWORD` | SES SMTP password |
| `DEFAULT_FROM_EMAIL` | Sender address verified with SES |
| `RAZORPAY_KEY_ID` | Razorpay test key ID first |
| `RAZORPAY_KEY_SECRET` | Matching Razorpay test API secret |

The Render Key Value URL is intended for private service-to-service connectivity. Do not publish a Redis URL or make the service publicly accessible. If the provider supplies an externally reachable Redis endpoint, require TLS and use `rediss://`.

## Step 5 — Deploy and initialize the site

1. Save environment variables and deploy the web service.
2. Wait for a successful deploy and inspect Render logs for migrations, static collection, and application startup errors.
3. Confirm the public Render URL returns the homepage over HTTPS. Add the custom domain in Render, configure the DNS records it provides, then update `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `PUBLIC_SITE_URL` to include the final domain.
4. Run `python manage.py createsuperuser` once using the Render Shell connected to the production service/database. Do not store the admin password in Git.
5. Use the admin page at `/manage-store/` to add catalog content and upload product images. Confirm uploaded files remain accessible after a deploy/restart.

## Step 6 — Validate before real payments

- Verify login, admin, forms/CSRF, static assets, product images, and uploads.
- Send a test contact message and order confirmation email; confirm SES delivery. SES must be out of its sandbox before sending to arbitrary customers.
- Test pre-order checkout and payment verification with Razorpay test credentials. Confirm the success screen displays the advance and remaining amount. Do not use live credentials until the full payment/reconciliation flow is checked.
- Configure Razorpay webhooks and verify signature handling/payment reconciliation before opening live sales.
- Check database backups, disk usage, service logs, and alerting; document a restore procedure.
- Run `python manage.py check --deploy` with the production settings and environment variables, then resolve any security warnings that apply.

## Operating and scaling notes

The attached media disk is persistent but belongs to one service instance. Do not scale this service horizontally until media is moved to shared object storage and session/cache behavior has been verified across instances. PostgreSQL and Redis remain separate services with their own plan costs. The local four-concurrent-request performance sample is not evidence for production capacity.
