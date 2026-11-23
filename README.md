# AqarExit Resale Analytics

Streamlit application for exploring Egyptian resale properties, project and developer
rankings, market summaries, registered profiles and project reviews.

## Deploy on Streamlit Community Cloud

Use this folder's contents at the root of the GitHub repository. Choose branch `main`,
entrypoint `app.py`, Python 3.12, and custom subdomain `aqar-exit-resale-analytics`
(subject to availability). Configure DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
and DB_SSL_CA as root-level TOML strings in Advanced settings > Secrets.
DB_SSL_CA must be `ca.pem`. Never commit the password or `.env`.
The CA certificate is public certificate material, not a private key.

The app uses the existing remote Aiven MySQL database; it does not copy data into
GitHub. Database updates become visible after Refresh data or the five-minute cache
expiry. SQL and calculation definitions are documented in SQL_GUIDE.md. Developer
name aliases remain a known source-data quality limitation under review.

## Run locally from this deployment copy

Install requirements.txt into a Python 3.12 virtual environment, configure a private
.env file using .env.example, then run:

    python -m streamlit run app.py --server.address 127.0.0.1

This cloud copy serves at the root URL. The original project retains its local URL.
