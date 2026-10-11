import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Contact Centre Reporting Hub", page_icon="📊", layout="wide")

st.title("📊 Contact Centre Reporting Hub")
st.caption("Upload Excel/CSV reports to view CLI, CQM, FCR and SLA summaries.")

with st.sidebar:
    st.header("Report Settings")
    report_type = st.selectbox(
        "Choose report module",
        ["CLI Breakdown", "CQM / QA Performance", "FCR / Repeat Calls", "SLA Tracking", "General Data Explorer"]
    )
    st.info("This starter version analyses files uploaded in the current session. Download your results before leaving the page.")

uploaded_files = st.file_uploader(
    "Upload Excel or CSV file(s)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
    help="You can upload multiple files. Files should have a header row."
)

def read_upload(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(file)
        except UnicodeDecodeError:
            file.seek(0)
            return pd.read_csv(file, encoding="latin-1")
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    return None

def norm(s):
    return str(s).strip().lower().replace("_", " ").replace("-", " ")

def find_col(columns, hints):
    lookup = {norm(c): c for c in columns}
    for hint in hints:
        for nc, original in lookup.items():
            if hint in nc:
                return original
    return None

if not uploaded_files:
    st.markdown("### Start here")
    st.write("1. Choose a report module from the left.")
    st.write("2. Upload your Excel/CSV file(s).")
    st.write("3. Review the detected columns and select the correct fields where needed.")
    st.write("4. Download the filtered data or summary.")
    st.warning("For confidential insurance data, use only files approved for this purpose. Do not upload customer names, NICs, phone numbers, claim details, or other sensitive company data to a public app without company approval.")
    st.stop()

frames = []
errors = []
for file in uploaded_files:
    try:
        df = read_upload(file)
        if df is not None and not df.empty:
            df["__source_file"] = file.name
            frames.append(df)
        else:
            errors.append(f"{file.name}: empty or unsupported file")
    except Exception as exc:
        errors.append(f"{file.name}: {exc}")

if errors:
    with st.expander("Files that could not be read"):
        for err in errors:
            st.write("• " + err)

if not frames:
    st.error("No readable data was found. Check that each file has a header row and tabular data.")
    st.stop()

# Combine files only when they have the same column structure; otherwise show them individually.
same_columns = all(list(df.columns) == list(frames[0].columns) for df in frames)
if same_columns:
    data = pd.concat(frames, ignore_index=True)
    st.success(f"Loaded {len(frames)} file(s), {len(data):,} rows.")
    st.caption("Files with matching column names/order were combined. Different file structures should be analysed separately.")
else:
    chosen_file = st.selectbox("Files have different column structures. Choose one to analyse:", [f.name for f in uploaded_files if f.name in [x["__source_file"].iloc[0] for x in frames]])
    data = next(df.copy() for df in frames if str(df["__source_file"].iloc[0]) == chosen_file)
    st.warning("Only the selected file is shown because the uploaded files have different column structures.")

data.columns = [str(c).strip() for c in data.columns]
cols = [c for c in data.columns if c != "__source_file"]

# Common filters
st.subheader("Data preview and filters")
date_guess = find_col(cols, ["date", "started at", "start time", "call date", "assessment date", "created"])
agent_guess = find_col(cols, ["agent", "employee", "staff name", "user name", "assessor"])
date_col = st.selectbox("Date column (optional)", ["— None —"] + cols, index=(cols.index(date_guess) + 1 if date_guess in cols else 0), key="date_col")
agent_col = st.selectbox("Agent column (optional)", ["— None —"] + cols, index=(cols.index(agent_guess) + 1 if agent_guess in cols else 0), key="agent_col")

filtered = data.copy()
if date_col != "— None —":
    parsed_dates = pd.to_datetime(filtered[date_col], errors="coerce", dayfirst=True)
    valid = parsed_dates.dropna()
    if not valid.empty:
        min_date = valid.min().date()
        max_date = valid.max().date()
        start_date, end_date = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        filtered["__parsed_date"] = parsed_dates
        filtered = filtered[
            filtered["__parsed_date"].notna()
            & (filtered["__parsed_date"].dt.date >= start_date)
            & (filtered["__parsed_date"].dt.date <= end_date)
        ]
    else:
        st.info("The selected date column could not be interpreted as dates; date filtering is skipped.")

if agent_col != "— None —":
    agents = sorted(filtered[agent_col].dropna().astype(str).unique().tolist())
    selected_agents = st.multiselect("Filter agents", agents, default=agents)
    filtered = filtered[filtered[agent_col].astype(str).isin(selected_agents)]

c1, c2, c3 = st.columns(3)
c1.metric("Rows in current view", f"{len(filtered):,}")
c2.metric("Columns", f"{len(cols):,}")
c3.metric("Files uploaded", f"{len(uploaded_files):,}")

st.dataframe(filtered.drop(columns=["__parsed_date"], errors="ignore"), use_container_width=True, height=300)

st.divider()
st.header(report_type)

if report_type == "CLI Breakdown":
    disposition_col = st.selectbox("Disposition column", ["— Select —"] + cols, index=(cols.index(find_col(cols, ["disposition", "wrap up", "outcome"])) + 1 if find_col(cols, ["disposition", "wrap up", "outcome"]) in cols else 0))
    direction_col = st.selectbox("Direction column (optional)", ["— None —"] + cols, index=(cols.index(find_col(cols, ["direction", "inbound outbound", "call type"])) + 1 if find_col(cols, ["direction", "inbound outbound", "call type"]) in cols else 0))
    if agent_col != "— None —":
        st.subheader("Calls by agent")
        by_agent = filtered.groupby(agent_col, dropna=False).size().reset_index(name="Call Count").sort_values("Call Count", ascending=False)
        st.dataframe(by_agent, use_container_width=True)
        st.plotly_chart(px.bar(by_agent, x=agent_col, y="Call Count", title="Call Count by Agent"), use_container_width=True)
    if disposition_col != "— Select —":
        by_disp = filtered.groupby(disposition_col, dropna=False).size().reset_index(name="Call Count").sort_values("Call Count", ascending=False)
        st.subheader("Calls by disposition")
        st.dataframe(by_disp, use_container_width=True)
        st.plotly_chart(px.bar(by_disp, x=disposition_col, y="Call Count", title="Call Count by Disposition"), use_container_width=True)
    if direction_col != "— None —":
        st.subheader("Direction split")
        st.plotly_chart(px.pie(filtered, names=direction_col, title="Call Direction"), use_container_width=True)
    st.caption("Repeat-call detection needs a caller/CLI field and a business-approved definition (for example, more than 2 calls from the same CLI in a selected period).")

elif report_type == "CQM / QA Performance":
    score_guess = find_col(cols, ["score", "percentage", "cqm", "qa result", "marks", "rating"])
    score_col = st.selectbox("Score column", ["— Select —"] + cols, index=(cols.index(score_guess) + 1 if score_guess in cols else 0))
    if agent_col != "— None —" and score_col != "— Select —":
        numeric_scores = pd.to_numeric(filtered[score_col].astype(str).str.replace("%", "", regex=False), errors="coerce")
        temp = filtered.assign(__score=numeric_scores).dropna(subset=["__score"])
        summary = temp.groupby(agent_col)["__score"].agg(["count", "mean", "min", "max"]).reset_index()
        summary.columns = [agent_col, "Assessments", "Average Score", "Lowest Score", "Highest Score"]
        st.dataframe(summary.round(2), use_container_width=True)
        st.plotly_chart(px.bar(summary, x=agent_col, y="Average Score", title="Average QA/CQM Score by Agent"), use_container_width=True)
        st.caption("Configure score bands according to your approved QA matrix. This starter does not assume one universal grading scale.")
    else:
        st.info("Select an agent column and a numeric score column to show agent performance.")

elif report_type == "FCR / Repeat Calls":
    cli_guess = find_col(cols, ["cli", "caller", "phone", "ani", "customer number"])
    cli_col = st.selectbox("Caller/CLI column", ["— Select —"] + cols, index=(cols.index(cli_guess) + 1 if cli_guess in cols else 0))
    reason_col = st.selectbox("Repeat reason / disposition column (optional)", ["— None —"] + cols, index=(cols.index(find_col(cols, ["repeat reason", "reason", "disposition", "wrap up"])) + 1 if find_col(cols, ["repeat reason", "reason", "disposition", "wrap up"]) in cols else 0))
    threshold = st.number_input("Flag caller after this many calls", min_value=1, max_value=20, value=2)
    if cli_col != "— Select —":
        counts = filtered.groupby(cli_col, dropna=False).size().reset_index(name="Calls")
        repeats = counts[counts["Calls"] > threshold].sort_values("Calls", ascending=False)
        st.metric("Caller IDs above threshold", f"{len(repeats):,}")
        st.dataframe(repeats, use_container_width=True)
        if reason_col != "— None —":
            st.subheader("Call reasons in current view")
            reasons = filtered.groupby(reason_col, dropna=False).size().reset_index(name="Count").sort_values("Count", ascending=False)
            st.dataframe(reasons, use_container_width=True)
        st.caption("This is a repeat-caller proxy, not a validated FCR measure. A proper FCR calculation needs a defined repeat window and repeat reason rules.")

elif report_type == "SLA Tracking":
    sla_guess = find_col(cols, ["sla", "target", "tat", "expected time"])
    actual_guess = find_col(cols, ["duration", "elapsed", "actual time", "response time", "time taken"])
    sla_col = st.selectbox("SLA target column (optional)", ["— None —"] + cols, index=(cols.index(sla_guess) + 1 if sla_guess in cols else 0))
    actual_col = st.selectbox("Actual duration/time column", ["— Select —"] + cols, index=(cols.index(actual_guess) + 1 if actual_guess in cols else 0))
    if actual_col != "— Select —":
        st.write("Select the correct time format before relying on SLA results. Durations may be seconds, minutes, or Excel time values.")
        unit = st.selectbox("Actual duration unit", ["Seconds", "Minutes"])
        if sla_col != "— None —":
            target = pd.to_numeric(filtered[sla_col], errors="coerce")
            actual = pd.to_numeric(filtered[actual_col], errors="coerce")
            target_minutes = target / 60 if unit == "Seconds" else target
            actual_minutes = actual / 60 if unit == "Seconds" else actual
            valid = target_minutes.notna() & actual_minutes.notna() & (target_minutes >= 0)
            if valid.any():
                breaches = (actual_minutes[valid] > target_minutes[valid]).sum()
                compliance = 100 * (1 - breaches / valid.sum())
                a, b = st.columns(2)
                a.metric("SLA compliance", f"{compliance:.1f}%")
                b.metric("Breaches", f"{breaches:,}")
                st.caption("Check that both columns use the same unit and that the target column contains numeric values.")
            else:
                st.info("Could not calculate SLA. Confirm numeric values and time units.")
        else:
            st.info("Choose an SLA target column to calculate compliance. Alternatively, configure approved SLA targets by disposition in a later version.")

else:
    st.subheader("Explore any uploaded data")
    numeric_cols = filtered.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        metric_col = st.selectbox("Numeric field to summarise", numeric_cols)
        st.metric(f"Average {metric_col}", f"{filtered[metric_col].mean():,.2f}")
        st.plotly_chart(px.histogram(filtered, x=metric_col, title=f"Distribution of {metric_col}"), use_container_width=True)
    st.write("Use the filters above to explore the uploaded dataset.")

st.divider()
st.subheader("Download")
csv_bytes = filtered.drop(columns=["__parsed_date"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Download current filtered data (CSV)", data=csv_bytes, file_name=f"report_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

st.caption("Starter build: validate column mapping, repeat-call rules, SLA units and CQM score bands against your actual report templates before using results for management decisions.")
