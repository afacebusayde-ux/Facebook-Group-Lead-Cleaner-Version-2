import io
import re
import csv

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Facebook Group Leads Cleaner", layout="wide")

EXCLUDED_COUNTRIES = {"india", "pakistan", "philippines", "africa"}

COUNTRY_NORMALIZE = {
    "usa": "United States",
    "us": "United States",
    "u.s.a": "United States",
    "u.s.a.": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
}

# Every country name/alias -> canonical country name. Used to detect a
# country directly inside a "Lives in ..." line (e.g. "Lives in Hong Kong").
ALL_COUNTRIES = {
    "afghanistan": "Afghanistan", "albania": "Albania", "algeria": "Algeria", "andorra": "Andorra",
    "angola": "Angola", "argentina": "Argentina", "armenia": "Armenia", "australia": "Australia",
    "austria": "Austria", "azerbaijan": "Azerbaijan", "bahamas": "Bahamas", "bahrain": "Bahrain",
    "bangladesh": "Bangladesh", "barbados": "Barbados", "belarus": "Belarus", "belgium": "Belgium",
    "belize": "Belize", "benin": "Benin", "bhutan": "Bhutan", "bolivia": "Bolivia",
    "bosnia": "Bosnia and Herzegovina", "bosnia and herzegovina": "Bosnia and Herzegovina",
    "botswana": "Botswana", "brazil": "Brazil", "brunei": "Brunei", "bulgaria": "Bulgaria",
    "burkina faso": "Burkina Faso", "burundi": "Burundi", "cambodia": "Cambodia", "cameroon": "Cameroon",
    "canada": "Canada", "chad": "Chad", "chile": "Chile", "china": "China", "colombia": "Colombia",
    "costa rica": "Costa Rica", "croatia": "Croatia", "cuba": "Cuba", "cyprus": "Cyprus",
    "czech republic": "Czech Republic", "czechia": "Czech Republic", "denmark": "Denmark",
    "djibouti": "Djibouti", "dominican republic": "Dominican Republic", "ecuador": "Ecuador",
    "egypt": "Egypt", "el salvador": "El Salvador", "estonia": "Estonia", "ethiopia": "Ethiopia",
    "fiji": "Fiji", "finland": "Finland", "france": "France", "gabon": "Gabon", "gambia": "Gambia",
    "georgia": "Georgia", "germany": "Germany", "ghana": "Ghana", "greece": "Greece",
    "guatemala": "Guatemala", "guinea": "Guinea", "guyana": "Guyana", "haiti": "Haiti",
    "honduras": "Honduras", "hong kong": "Hong Kong", "hongkong": "Hong Kong", "hungary": "Hungary",
    "iceland": "Iceland", "indonesia": "Indonesia", "iran": "Iran", "iraq": "Iraq",
    "ireland": "Ireland", "israel": "Israel", "italy": "Italy", "ivory coast": "Ivory Coast",
    "jamaica": "Jamaica", "japan": "Japan", "jordan": "Jordan", "kazakhstan": "Kazakhstan",
    "kenya": "Kenya", "kosovo": "Kosovo", "kuwait": "Kuwait", "kyrgyzstan": "Kyrgyzstan",
    "laos": "Laos", "latvia": "Latvia", "lebanon": "Lebanon", "lesotho": "Lesotho",
    "liberia": "Liberia", "libya": "Libya", "liechtenstein": "Liechtenstein", "lithuania": "Lithuania",
    "luxembourg": "Luxembourg", "macau": "Macau", "macao": "Macau", "madagascar": "Madagascar",
    "malawi": "Malawi", "malaysia": "Malaysia", "maldives": "Maldives", "mali": "Mali",
    "malta": "Malta", "mauritania": "Mauritania", "mauritius": "Mauritius", "mexico": "Mexico",
    "moldova": "Moldova", "monaco": "Monaco", "mongolia": "Mongolia", "montenegro": "Montenegro",
    "morocco": "Morocco", "mozambique": "Mozambique", "myanmar": "Myanmar", "namibia": "Namibia",
    "nepal": "Nepal", "netherlands": "Netherlands", "new zealand": "New Zealand",
    "nicaragua": "Nicaragua", "niger": "Niger", "nigeria": "Nigeria", "north korea": "North Korea",
    "north macedonia": "North Macedonia", "norway": "Norway", "oman": "Oman",
    "panama": "Panama", "papua new guinea": "Papua New Guinea", "paraguay": "Paraguay",
    "peru": "Peru", "poland": "Poland", "portugal": "Portugal", "qatar": "Qatar",
    "romania": "Romania", "russia": "Russia", "rwanda": "Rwanda",
    "saudi arabia": "Saudi Arabia", "senegal": "Senegal", "serbia": "Serbia",
    "sierra leone": "Sierra Leone", "singapore": "Singapore", "slovakia": "Slovakia",
    "slovenia": "Slovenia", "somalia": "Somalia", "south africa": "South Africa",
    "south korea": "South Korea", "south sudan": "South Sudan", "spain": "Spain",
    "sri lanka": "Sri Lanka", "sudan": "Sudan", "suriname": "Suriname", "sweden": "Sweden",
    "switzerland": "Switzerland", "syria": "Syria", "taiwan": "Taiwan", "tajikistan": "Tajikistan",
    "tanzania": "Tanzania", "thailand": "Thailand", "togo": "Togo",
    "trinidad and tobago": "Trinidad and Tobago", "tunisia": "Tunisia", "turkey": "Turkey",
    "turkmenistan": "Turkmenistan", "uganda": "Uganda", "ukraine": "Ukraine",
    "united arab emirates": "United Arab Emirates", "uae": "United Arab Emirates",
    "united kingdom": "United Kingdom", "uk": "United Kingdom", "england": "United Kingdom",
    "scotland": "United Kingdom", "wales": "United Kingdom",
    "united states": "United States", "usa": "United States", "us": "United States",
    "uruguay": "Uruguay", "uzbekistan": "Uzbekistan", "venezuela": "Venezuela",
    "vietnam": "Vietnam", "yemen": "Yemen", "zambia": "Zambia", "zimbabwe": "Zimbabwe",
}

# Common cities/regions -> country, for when "Lives in ..." names a city
# instead of a country (e.g. "Lives in Bangkok").
LOCATION_TO_COUNTRY = {
    "new york": "United States", "los angeles": "United States", "chicago": "United States",
    "dallas": "United States", "houston": "United States", "miami": "United States",
    "london": "United Kingdom", "manchester": "United Kingdom", "birmingham": "United Kingdom",
    "paris": "France", "berlin": "Germany", "munich": "Germany", "madrid": "Spain",
    "barcelona": "Spain", "rome": "Italy", "milan": "Italy", "amsterdam": "Netherlands",
    "bangkok": "Thailand", "chiang mai": "Thailand", "pattaya": "Thailand", "phuket": "Thailand",
    "manila": "Philippines", "cebu": "Philippines", "davao": "Philippines",
    "jakarta": "Indonesia", "bali": "Indonesia", "kuala lumpur": "Malaysia",
    "ho chi minh": "Vietnam", "hanoi": "Vietnam", "seoul": "South Korea", "busan": "South Korea",
    "tokyo": "Japan", "osaka": "Japan", "beijing": "China", "shanghai": "China",
    "guangzhou": "China", "shenzhen": "China", "mumbai": "India", "delhi": "India",
    "bangalore": "India", "karachi": "Pakistan", "lahore": "Pakistan", "islamabad": "Pakistan",
    "sydney": "Australia", "melbourne": "Australia", "toronto": "Canada", "vancouver": "Canada",
    "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates", "doha": "Qatar",
    "riyadh": "Saudi Arabia", "cairo": "Egypt", "lagos": "Nigeria", "nairobi": "Kenya",
    "johannesburg": "South Africa", "cape town": "South Africa", "moscow": "Russia",
    "istanbul": "Turkey", "athens": "Greece", "lisbon": "Portugal", "dublin": "Ireland",
    "oslo": "Norway", "stockholm": "Sweden", "copenhagen": "Denmark", "warsaw": "Poland",
}

# Lines that mark the start of a new "field" in the scraped block - used to
# know where a free-text answer (like Remarks) ends.
LABEL_PATTERNS = [
    r"^country$",
    r"^do you agree",
    r"^by giving your email",
    r"^please provide your email",
    r"^joined facebook$",
    r"^lives in ",
    r"^member",
    r"^studied at ",
    r"^works at ",
    r"^submitted a",
    r"\d+\s+groups?\s+in\s+common",
    r"\d+\s+other\s+groups",
    r"^recently joined group",
    r"^\d+\s+(hour|hours|day|days|week|weeks|month|months|year|years)\s+ago$",
    r"^a\s+(day|week|month|year)\s+ago$",
    r"^an?\s+(hour|day|week|month|year)\s+ago$",
]
LABEL_REGEX = re.compile("|".join(LABEL_PATTERNS), re.IGNORECASE)

NAME_ANCHOR_REGEX = re.compile(r"member\s*[\u00b7\.\-]\s*requested", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
LIVES_IN_REGEX = re.compile(r"^lives in\s+(.+)$", re.IGNORECASE)
COUNTRY_LINE_REGEX = re.compile(r"^country$", re.IGNORECASE)


def normalize_country(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw.strip()
    key = cleaned.lower().strip(" .")
    if key in COUNTRY_NORMALIZE:
        return COUNTRY_NORMALIZE[key]
    return cleaned.title() if cleaned.isupper() or cleaned.islower() else cleaned


def is_excluded_country(country: str) -> bool:
    if not country:
        return False
    key = country.lower().strip()
    if key in EXCLUDED_COUNTRIES:
        return True
    for bad in EXCLUDED_COUNTRIES:
        if bad in key:
            return True
    return False


def split_into_blocks(raw_text: str):
    """Split scraped text into one block per lead, anchored on the
    'Member · Requested' marker (the lead's name is the non-empty line
    immediately before that marker)."""
    lines = raw_text.splitlines()
    anchors = []
    for i, line in enumerate(lines):
        if NAME_ANCHOR_REGEX.search(line):
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0:
                anchors.append(j)

    if not anchors:
        return []

    blocks = []
    for idx, start in enumerate(anchors):
        end = anchors[idx + 1] if idx + 1 < len(anchors) else len(lines)
        name = lines[start].strip()
        block_lines = lines[start:end]
        blocks.append((name, block_lines))
    return blocks


def extract_email(block_lines):
    for line in block_lines:
        m = EMAIL_REGEX.search(line)
        if m:
            return m.group(0).strip()
    return ""


def extract_address(block_lines):
    for line in block_lines:
        m = LIVES_IN_REGEX.match(line.strip())
        if m:
            return m.group(1).strip()
    return ""


def country_from_place(place: str) -> str:
    """Given free text like 'Hong Kong' or 'Bangkok, Thailand', try to
    resolve it to a canonical country name using known countries first,
    then known cities."""
    place_lower = place.lower()
    for key, country in ALL_COUNTRIES.items():
        if key in place_lower:
            return country
    for key, country in LOCATION_TO_COUNTRY.items():
        if key in place_lower:
            return country
    return ""


def extract_country(block_lines):
    # 1. Prefer an explicit "Country" field if present.
    for i, line in enumerate(block_lines):
        if COUNTRY_LINE_REGEX.match(line.strip()):
            for j in range(i + 1, len(block_lines)):
                val = block_lines[j].strip()
                if val:
                    return val

    # 2. Fall back to inferring the country from "Lives in ..." text,
    #    e.g. "Lives in Hong Kong" -> "Hong Kong".
    for line in block_lines:
        m = LIVES_IN_REGEX.match(line.strip())
        if m:
            resolved = country_from_place(m.group(1).strip())
            if resolved:
                return resolved
    return ""


def extract_remarks(block_lines, remark_question: str):
    if not remark_question:
        return ""
    question_norm = remark_question.strip().lower()
    for i, line in enumerate(block_lines):
        if line.strip().lower() == question_norm:
            answer_lines = []
            for j in range(i + 1, len(block_lines)):
                candidate = block_lines[j].strip()
                if not candidate:
                    if answer_lines:
                        break
                    continue
                if LABEL_REGEX.search(candidate):
                    break
                if EMAIL_REGEX.search(candidate):
                    break
                answer_lines.append(candidate)
            return " ".join(answer_lines).strip()
    return ""


def parse_leads(raw_text: str, group_name: str, remark_question: str):
    blocks = split_into_blocks(raw_text)
    leads = []
    for name, block_lines in blocks:
        email = extract_email(block_lines)
        country_raw = extract_country(block_lines)
        country = normalize_country(country_raw)
        address = extract_address(block_lines)
        remarks = extract_remarks(block_lines, remark_question)
        leads.append(
            {
                "Facebook Group Name": group_name,
                "Lead Name": name,
                "Lead Email": email,
                "Lead Country": country,
                "Lead Address": address,
                "Remarks": remarks,
            }
        )
    return leads


@st.cache_data(ttl=300, show_spinner=False)
def fetch_existing_emails(sheet_id: str, tab_name: str):
    """Fetch column I from the given Google Sheet tab via the public CSV
    export. Returns (set_of_emails, error_message_or_None)."""
    if not sheet_id or not tab_name:
        return set(), "Missing sheet ID or tab name."
    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={requests.utils.quote(tab_name)}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), header=None)
        if df.shape[1] < 9:
            return set(), "Column I not found in fetched sheet (sheet may not be public)."
        col_i = df.iloc[:, 8].dropna().astype(str)
        emails = {e.strip().lower() for e in col_i if "@" in e}
        return emails, None
    except Exception as e:  # noqa: BLE001
        return set(), f"Could not fetch sheet automatically ({e})."


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("Facebook Group Leads Cleaner")

with st.sidebar:
    st.subheader("Duplicate-email check settings")
    st.caption(
        "The sheet must be shared as 'Anyone with the link can view' for "
        "automatic checking to work."
    )
    sheet_id = st.text_input(
        "Google Sheet ID",
        value="14BzYkTHu4ZCYx9ckQiBBjQDVSWM4PjVJ-7cnkhxhLio",
    )
    tab_name = st.text_input("Tab name", value="Email List 2023-2026")
    manual_emails_text = st.text_area(
        "Or paste existing emails manually (one per line) — used as a "
        "fallback / addition if the sheet can't be auto-fetched",
        height=100,
    )

col1, col2 = st.columns(2)
with col1:
    group_name = st.text_input("Facebook Group Name")
with col2:
    remark_question = st.text_input("Remark/s (the question asked in the form)")

scraped_data = st.text_area("Scraped Data", height=350, placeholder="Paste the raw text copied from Facebook here...")

clean_clicked = st.button("Clean Data", type="primary")

if clean_clicked:
    if not scraped_data.strip():
        st.warning("Please paste the scraped data first.")
    else:
        with st.spinner("Cleaning data, please wait..."):
            leads = parse_leads(scraped_data, group_name, remark_question)

            existing_emails, fetch_error = fetch_existing_emails(sheet_id, tab_name)
            manual_emails = {
                e.strip().lower() for e in manual_emails_text.splitlines() if e.strip()
            }
            existing_emails = existing_emails | manual_emails

            prev_kept = st.session_state.get("kept", [])
            session_emails = {l["Lead Email"].strip().lower() for l in prev_kept if l["Lead Email"]}

            kept, removed = [], []
            for lead in leads:
                email = lead["Lead Email"].strip()
                country = lead["Lead Country"]

                if not email:
                    removed.append({**lead, "Reason": "No email found"})
                    continue
                if is_excluded_country(country):
                    removed.append({**lead, "Reason": f"Country ({country or 'Unknown'})"})
                    continue
                if email.lower() in existing_emails:
                    removed.append({**lead, "Reason": "Already Exist"})
                    continue
                if email.lower() in session_emails:
                    removed.append({**lead, "Reason": "Already Exist (this session)"})
                    continue

                kept.append(lead)
                session_emails.add(email.lower())

            # Accumulate so multiple batches of scraped data (e.g. several
            # groups, or several pastes) build up into one combined table.
            st.session_state["kept"] = prev_kept + kept
            st.session_state["removed"] = removed

        if fetch_error and not manual_emails:
            st.info(
                f"Note: {fetch_error} Duplicate-email check is using only the "
                "manually pasted list (if any)."
            )
        st.success(
            f"Processed {len(leads)} row(s) from this batch — "
            f"{len(kept)} added, {len(removed)} removed. "
            f"Total cleaned so far: {len(st.session_state['kept'])}."
        )

st.markdown("---")

kept = st.session_state.get("kept", [])
removed = st.session_state.get("removed", [])

if kept:
    if st.button("Clear All Cleaned Data"):
        st.session_state["kept"] = []
        st.session_state["removed"] = []
        st.rerun()

if kept or removed:
    if kept:
        df_kept = pd.DataFrame(
            kept,
            columns=[
                "Facebook Group Name",
                "Lead Name",
                "Lead Email",
                "Lead Country",
                "Lead Address",
                "Remarks",
            ],
        )

        tsv_buffer = io.StringIO()
        writer = csv.writer(tsv_buffer, delimiter="\t", lineterminator="\n")
        for row in df_kept.itertuples(index=False):
            writer.writerow(row)
        tsv_data = tsv_buffer.getvalue()

        header_col1, header_col2 = st.columns([5, 1])
        with header_col1:
            st.subheader("Cleaned Leads")
        with header_col2:
            import html as html_lib
            import streamlit.components.v1 as components

            escaped = html_lib.escape(tsv_data)
            components.html(
                f"""
                <div style="display:flex; justify-content:flex-end; align-items:center; height:2.4em;">
                  <button id="copy-btn" style="
                      padding: 0.4em 0.9em;
                      border-radius: 0.5em;
                      border: 1px solid #d0d0d0;
                      background-color: #ffffff;
                      cursor: pointer;
                      font-size: 0.9em;
                  ">📋 Copy Data</button>
                </div>
                <textarea id="copy-source" style="position:absolute; left:-9999px;">{escaped}</textarea>
                <script>
                const btn = document.getElementById("copy-btn");
                btn.addEventListener("click", function() {{
                    const textarea = document.getElementById("copy-source");
                    let copied = false;
                    if (navigator.clipboard && navigator.clipboard.writeText) {{
                        navigator.clipboard.writeText(textarea.value).then(function() {{
                            copied = true;
                        }}).catch(function() {{}});
                    }}
                    if (!copied) {{
                        textarea.style.position = "fixed";
                        textarea.style.left = "0";
                        textarea.focus();
                        textarea.select();
                        try {{ document.execCommand("copy"); }} catch (e) {{}}
                        textarea.style.position = "absolute";
                        textarea.style.left = "-9999px";
                    }}
                    btn.innerText = "✅ Copied!";
                    setTimeout(function() {{ btn.innerText = "📋 Copy Data"; }}, 1500);
                }});
                </script>
                """,
                height=50,
            )

        st.dataframe(df_kept, use_container_width=True, hide_index=True)
    else:
        st.subheader("Cleaned Leads")
        st.info("No leads passed the cleaning rules.")

    if removed:
        if st.toggle("Show Removed Data"):
            df_removed = pd.DataFrame(
                removed,
                columns=[
                    "Lead Name",
                    "Lead Email",
                    "Lead Country",
                    "Lead Address",
                    "Remarks",
                    "Reason",
                ],
            )
            st.dataframe(df_removed, use_container_width=True, hide_index=True)
else:
    st.caption("Paste your data above and click \"Clean Data\" to get started.")