# AWS Elastic Beanstalk deployment

This application is configured for the Elastic Beanstalk Python 3.12 platform (see `runtime.txt`). The repository intentionally contains no AWS credentials, database passwords, or payment secrets. Do not commit those values.

## Required AWS resources

- Elastic Beanstalk Python web environment, with an EC2 instance profile attached.
- Amazon RDS for PostgreSQL, in private subnets; allow inbound PostgreSQL only from the Elastic Beanstalk instance security group.
- A private S3 bucket for uploaded media. Keep S3 Block Public Access enabled; the application generates time-limited signed media URLs.
- ElastiCache for Redis with in-transit encryption. Allow Redis traffic only from the Elastic Beanstalk instance security group.
- Amazon SES domain/email identity and SMTP credentials for outbound mail.
- A load balancer with an ACM certificate for the production domain. Point DNS to the load balancer and enable HTTPS.

Configure the Elastic Beanstalk EC2 instance profile with least-privilege access:

- `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject` on the media bucket's `media/*` prefix.
- `sns:Publish` only if phone OTP login is enabled.
- `secretsmanager:GetSecretValue` only if retrieving environment secrets from Secrets Manager at deploy/startup.

Place RDS and ElastiCache in private networking; do not expose their ports to the public internet.

## Elastic Beanstalk environment variables

Set these in the Elastic Beanstalk environment configuration or inject them from AWS Secrets Manager. Never place secret values in `.ebextensions`.

| Variable | Required value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `mysite.settings.prod` (also set by `.ebextensions/01_django.config`) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | A unique, randomly generated secret (50+ characters recommended) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated production DNS hostnames, without schemes |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins, e.g. `https://shop.example.com` |
| `PUBLIC_SITE_URL` | Canonical HTTPS site URL, e.g. `https://shop.example.com` |
| `DATABASE_URL` | PostgreSQL URL for RDS; URL-encode special characters in credentials |
| `AWS_REGION` | Region used for the S3 bucket and SNS |
| `AWS_STORAGE_BUCKET_NAME` | Private S3 media bucket |
| `REDIS_URL` | ElastiCache TLS URL, e.g. `rediss://<endpoint>:6379/0` |
| `EMAIL_HOST` | SES SMTP endpoint, e.g. `email-smtp.<region>.amazonaws.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | SES SMTP username (not an IAM access key) |
| `EMAIL_HOST_PASSWORD` | SES SMTP password |
| `DEFAULT_FROM_EMAIL` | Sender address verified with SES |
| `RAZORPAY_KEY_ID` | Razorpay live key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay live API secret |
| `AWS_SMS_ENABLED` | `true` only after SNS SMS sending is approved and tested; otherwise `false` |

The production settings fail fast if required secrets, HTTPS hosts, PostgreSQL, S3, Redis, or SES settings are missing. Redis is required because OTPs and rate limits must be shared across application workers and instances.

## Deploy the ZIP from the AWS console

The prepared source bundle is `NowhenceClothings-ElasticBeanstalk.zip` in the project folder. Upload the ZIP itself; do not unzip it first. It contains the application code and Elastic Beanstalk configuration, but deliberately does not contain the local SQLite database, uploaded `media/` files, virtual environment, or secrets.

### Before uploading

1. Sign in to the AWS console and select the same AWS Region as your RDS database, Redis replication group, S3 bucket, and SES setup. This project was initially prepared for `ap-south-1`; change this only if all resources are in another region.
2. Complete the prerequisites in [Required AWS resources](#required-aws-resources) and [AWS account setup](#aws-account-setup), including VPC connectivity, database, Redis, S3, email, IAM instance profile, and HTTPS certificate. The application will not start until its required production environment variables are set.
3. Keep the ZIP in a convenient local folder. Confirm it is the generated deployment ZIP, not the project directory or a ZIP containing `.venv`, `.env`, `db.sqlite3`, or `media/`.

### Create the Elastic Beanstalk application and environment

1. Open **AWS Elastic Beanstalk** in the console and select **Create application**.
2. Enter an application name, then create an environment with **Web server environment**.
3. Choose the **Python** platform and Python 3.12. Use a supported platform branch offered in your Region.
4. For the application code, choose **Upload your code**, select `NowhenceClothings-ElasticBeanstalk.zip`, and enter a new application version label such as `release-2026-10-05-1`.
5. Configure the environment to use the VPC and subnets that can reach RDS and Redis. Use a load-balanced environment for a public production site, and attach the EC2 instance profile that has the S3 permissions listed above. Do not make the database or Redis publicly accessible.
6. Create the environment. Allow the initial deployment and health checks to finish. The bundle's `.ebextensions/01_django.config` sets the WSGI application, runs `migrate` once on the leader, and runs `collectstatic`.

If an Elastic Beanstalk application/environment already exists, open the application in the console and use **Upload and deploy** (or **Upload** under application versions). Select the ZIP, provide a unique version label, upload it, then deploy that version to the intended environment.

### Set environment properties

Configure the required production environment variables before deploying the application ZIP. If the console flow requires an initial application version to create the environment, create the environment with the sample application, configure its environment properties, and then use **Upload and deploy** for the real ZIP. Otherwise, the first application startup will fail fast because production settings intentionally require real production values.

Open the environment's **Configuration** page, edit **Updates, monitoring, and logging** or **Software** (the console label varies by platform version), and add the values from the [Elastic Beanstalk environment variables](#elastic-beanstalk-environment-variables) table. Save and apply the configuration before deploying the application version.

Set actual production values, not examples or placeholders:

- Generate and store `DJANGO_SECRET_KEY` securely. Do not put it in the ZIP or source control.
- Use the real RDS PostgreSQL URL, TLS Redis endpoint, S3 bucket, SES SMTP credentials, hostnames, and HTTPS origins.
- Set `DJANGO_ALLOWED_HOSTS` to hostnames only (no `https://`); set `CSRF_TRUSTED_ORIGINS` and `PUBLIC_SITE_URL` to HTTPS URLs.
- Keep `AWS_SMS_ENABLED=false` until SNS SMS and any regional compliance requirements have been completed.
- Set Razorpay live credentials only when the live account and webhook are configured; verify payment callbacks/webhooks before accepting real orders.

For a mature production setup, keep secret values in AWS Secrets Manager and restrict access to them. Never paste secrets into this document, `.ebextensions`, or a checked-in file.

### Verify deployment and create the admin account

1. In the Elastic Beanstalk environment, review **Events** and **Health**. If deployment is unhealthy, use **Logs** to request the full logs and inspect the application and deployment logs. Resolve missing configuration, IAM, or network access issues before retrying.
2. Open the environment URL over HTTPS. Verify sign-in and CSRF, static assets, product/media access, password-reset email, order email, and checkout. Test SMS only if enabled. Confirm HTTP redirects to HTTPS.
3. Before launch, decide which catalog records to import into RDS and copy the referenced product media to S3. Neither the local SQLite data nor `media/` is included in the ZIP. Do not import development users, orders, or sessions without a deliberate data migration plan.
4. Create the first Django superuser using a secure one-off management-command session connected to the running environment and production database. Do not store the admin password in the ZIP, environment configuration, or a committed deployment file.
5. Keep the previous healthy application version in Elastic Beanstalk. If a deployment fails, deploy that previous version while investigating the failed release.

## AWS account setup

1. Choose a region and create the VPC/subnets and security groups for Elastic Beanstalk, RDS, and ElastiCache.
2. Create the RDS PostgreSQL database and ElastiCache Redis replication group with TLS enabled.
3. Create the private S3 bucket and attach the least-privilege policy to the Elastic Beanstalk EC2 instance profile.
4. Verify the sending domain in SES, publish its DKIM records, request production sending access if the account is in the SES sandbox, and create SES SMTP credentials.
5. If enabling SMS, confirm SNS SMS support and spending limits in the region. For Indian destinations, complete the applicable sender-ID and DLT registration requirements before setting `AWS_SMS_ENABLED=true`.
6. Create an Elastic Beanstalk Python 3.12 environment and configure its VPC, instance profile, load balancer, and production environment variables as described above. Ensure the load balancer forwards HTTPS and the app receives the `X-Forwarded-Proto` header.
7. Deploy the ZIP through **Upload and deploy** in the Elastic Beanstalk console. `.ebextensions/01_django.config` runs database migrations once on the leader and collects static assets during deployment.
8. Attach an ACM certificate to the load balancer and route the production DNS name to it.
9. Create the first Django superuser through a secure one-off Elastic Beanstalk SSH/management command session. Do not create an admin account from a committed migration or deployment config.
10. Verify HTTP redirects to HTTPS, login/CSRF, static files, media upload/read, password-reset email, order email, SMS if enabled, and Razorpay checkout before opening the site.

## Operations before opening sales

- Enable automated RDS backups and point-in-time recovery; test restoration.
- Set CloudWatch alarms for environment health, 5xx responses, CPU/memory, RDS storage/connections, and SES delivery/bounce rates.
- Configure a Razorpay webhook for payment lifecycle reconciliation and verify its signature using a dedicated webhook secret before relying on payment callbacks alone.
- Confirm stock/order behavior under concurrent checkout and load-test the selected Elastic Beanstalk instance size.
- Review Django's `check --deploy` output using the actual production environment variables before launch.
