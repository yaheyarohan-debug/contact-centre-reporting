# Contact Centre Reporting Hub (Free starter)

## Included
- Upload multiple CSV / Excel files
- Date and agent filters where available
- CLI breakdown by agent, disposition, and direction
- CQM/QA score summary by agent
- Repeat-caller threshold report (proxy; not a validated FCR measure)
- Basic SLA compliance calculation when actual and target times are numeric and use the same unit
- CSV export of the filtered data

## Run locally
1. Install Python 3.10+ from https://www.python.org/downloads/
2. Open a terminal / Command Prompt in this folder.
3. Run: `python -m pip install -r requirements.txt`
4. Run: `streamlit run app.py`
5. Your browser should open the app.

## Deploy free
1. Create a GitHub account at https://github.com
2. Create a **private** repository for the code if allowed by your organisation.
3. Upload `app.py` and `requirements.txt`.
4. Go to https://share.streamlit.io and connect GitHub.
5. Create app, select the repository and `app.py`, then deploy.

Important:
- A Streamlit Community Cloud app is online. Do not upload real customer or confidential insurance data unless your company has approved the hosting and data handling.
- This starter keeps uploaded data in the active app session; it is not a permanent database. Uploads may need to be repeated after a refresh/restart.
- Free hosting limits and terms can change.
- Files with different column structures are analysed one at a time. Matching structures are combined.
- Validate all results against known reports before relying on them.
