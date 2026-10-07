# AWS production deployment guide

This guide deploys the project using AWS Elastic Beanstalk, RDS PostgreSQL, ElastiCache Redis, S3, and SES. The production settings and `.ebextensions/01_django.config` are already included in the source bundle.

## What you will need

- An AWS account with billing enabled and MFA on the account.
- A domain name and access to its DNS.
- The deployment ZIP `NowhenceClothings-Production-20261008.zip`.
- A verified sender domain/address in Amazon SES.
- Razorpay test credentials for initial checkout validation. Do not start with live keys.

Choose one AWS region for all the resources where practical. This project was initially prepared for Mumbai (`ap-south-1`); confirm service availability and pricing before choosing it or another region.

## Step 1 — Create the network

Create or choose a VPC with:

- Public subnets for the Elastic Beanstalk load balancer.
- Private subnets for the Elastic Beanstalk instances, RDS, and Redis.
- Security groups allowing HTTPS to the load balancer, web traffic from the load balancer to the app, PostgreSQL from the app to RDS, and Redis from the app to ElastiCache only.

Do not give the database or Redis a public IP or allow their ports from the internet.

## Step 2 — Create the data and media services

1. Create an Amazon RDS PostgreSQL database. Enable automated backups and point-in-time recovery. Use a supported PostgreSQL version and a size appropriate to expected traffic.
2. Create an ElastiCache Redis deployment with in-transit encryption enabled. The app expects a `rediss://` URL.
3. Create a private S3 bucket for media. Keep Block Public Access enabled.
4. Create an EC2 instance profile for Elastic Beanstalk. Grant only `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` on the bucket's `media/*` prefix. Add Secrets Manager read access only if you use it to inject secrets.

The ZIP intentionally excludes the local database and uploaded media. Populate the production catalog and upload its image files separately after deployment.

## Step 3 — Configure SES and HTTPS

1. Verify your sending domain in SES and publish the DKIM DNS records.
2. Request production sending access if the SES account is still in the sandbox.
3. Create SES SMTP credentials (these are not IAM access keys).
4. Request or import an ACM certificate for your custom domain, in the same region as the Elastic Beanstalk load balancer.

## Step 4 — Create the Elastic Beanstalk environment

1. In the AWS console, create an Elastic Beanstalk **Web server** application and environment.
2. Select the Python 3.12 platform.
3. Use a load-balanced environment for a public production site. Configure the VPC, subnets, load balancer security group, and EC2 instance profile from Step 1 and Step 2.
4. Attach the ACM certificate to the load balancer listener for HTTPS.
5. Configure the environment's health check path as `/` (the app does not currently define a dedicated health endpoint).

The provided `.ebextensions/01_django.config` sets the WSGI entry point and runs migrations on the environment leader, then collects static files.

## Step 5 — Add production environment variables

Set these as Elastic Beanstalk environment properties or inject them from AWS Secrets Manager. Never add secret values to the ZIP or a committed file.

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `mysite.settings.prod` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | A new, unique, randomly generated secret |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames only, e.g. `shop.example.com,www.shop.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins, e.g. `https://shop.example.com,https://www.shop.example.com` |
| `PUBLIC_SITE_URL` | Canonical HTTPS URL, e.g. `https://shop.example.com` |
| `DATABASE_URL` | RDS PostgreSQL URL; URL-encode reserved characters in the password |
| `AWS_REGION` | Region containing the S3 bucket |
| `AWS_STORAGE_BUCKET_NAME` | Private media bucket name |
| `REDIS_URL` | TLS URL, e.g. `rediss://<redis-endpoint>:6379/0` |
| `EMAIL_HOST` | SES SMTP endpoint, e.g. `email-smtp.ap-south-1.amazonaws.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | SES SMTP username |
| `EMAIL_HOST_PASSWORD` | SES SMTP password |
| `DEFAULT_FROM_EMAIL` | Sender address verified in SES |
| `RAZORPAY_KEY_ID` | Razorpay test key ID first |
| `RAZORPAY_KEY_SECRET` | Matching Razorpay test API secret |
| `AWS_SMS_ENABLED` | `false` until SMS has been separately approved and tested |

Use the actual domain in `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `PUBLIC_SITE_URL`. Do not use wildcard hosts. When the environment configuration is saved, deploy the ZIP from Step 6.

## Step 6 — Upload the production ZIP

1. Open the Elastic Beanstalk application and choose **Upload and deploy**.
2. Upload `NowhenceClothings-Production-20261008.zip` as the source bundle itself; do not unzip it before uploading.
3. Choose a unique version label and deploy.
4. Wait for the environment to report healthy. Inspect **Events**, **Health**, and application logs if it does not.

## Step 7 — Set up the domain and admin user

1. Point your domain's DNS record to the Elastic Beanstalk load balancer.
2. Confirm the site redirects to HTTPS and the HTTPS certificate is valid.
3. Use a secure one-off management command session connected to the deployed environment to run `python manage.py createsuperuser`. Do not put the admin password in environment configuration or a file.
4. Log in at `/manage-store/` and add catalog products, variants, inventory, and site content.
5. Upload product media through the admin and check that S3-backed images load.

## Step 8 — Validate before accepting real orders

- Test signup/login, CSRF-protected forms, admin, product pages, static assets, and media upload/read.
- Send a test contact message and order email; confirm SES delivery and check bounce/complaint monitoring.
- Complete the pre-order flow with Razorpay test credentials, including payment verification and the remaining-balance display. Do not use live payment keys for this check.
- Configure and validate Razorpay webhook signature verification and payment reconciliation before relying on live payments.
- Confirm backup restoration procedures for RDS and S3.
- Review `python manage.py check --deploy` in the production environment and resolve relevant warnings.
- Set CloudWatch alarms for application health and 5xx responses, EC2 CPU/memory, database storage/connections, and SES delivery/bounces.

Only switch to Razorpay live credentials after the test flow and reconciliation have been verified. Keep a prior healthy Elastic Beanstalk application version available for rollback.

## Cost and scaling notes

The load balancer, RDS, and ElastiCache are separate billable services. Choose instance sizes based on measured production-like load and expected traffic; the local light performance sample is not capacity evidence. Set AWS Budgets alerts before creating resources.
