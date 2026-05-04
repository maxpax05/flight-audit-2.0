import streamlit as st
import imaplib
import re
import pandas as pd
import plotly.express as px

# ---------------- CONFIG ----------------
IMAP_SERVER = "imap.mail.yahoo.com"

SENDER = "gpnet@xmedia.airfrance.fr"

st.set_page_config(page_title="Pilot Dashboard 3.3", layout="wide")

st.title("✈️ Pilot Dashboard 3.3")

# ---------------- INPUT ----------------
passenger_name = st.text_input("Nom du passager (ex: PIOT EYRAUD MAXENCE)")

email_user = st.text_input("Yahoo email")
email_pass = st.text_input("App password Yahoo", type="password")

st.divider()

st.subheader("💸 Frais annexes")

peages = st.number_input("Péages (€)", value=0.0)
parking = st.number_input("Parking (€)", value=0.0)
hotel = st.number_input("Hôtel (€)", value=0.0)
autres = st.number_input("Autres frais (€)", value=0.0)

# ---------------- PARSING STRUCTURÉ ----------------
def extract(body):

    # NOM
    name_match = re.search(
        r'Information passager.*?\n.*?\n([A-Z\s]+)',
        body,
        re.DOTALL
    )
    name = name_match.group(1).strip() if name_match else None

    # DATE
    date_match = re.search(
        r'Vol aller .*? (\d{1,2} \w+ \d{4})',
        body
    )
    date = date_match.group(1) if date_match else None

    # ROUTE
    route_match = re.search(
        r'\(([A-Z]{3}) .*?\).*?\(([A-Z]{3})',
        body
    )
    route = f"{route_match.group(1)}-{route_match.group(2)}" if route_match else None

    # PRIX TTC
    price_match = re.search(
        r'Montant total TTC\s*:\s*([\d.,]+)',
        body
    )

    price = None
    if price_match:
        price = float(price_match.group(1).replace(',', '.'))

    return name, date, route, price

# ---------------- FETCH OPTIMISÉ ----------------
def fetch_flights():

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(email_user, email_pass)
    mail.select("inbox")

    status, messages = mail.search(
        None,
        '(FROM "gpnet@xmedia.airfrance.fr" SUBJECT "Confirmation" SINCE "01-Jan-2025" BEFORE "01-Jan-2026")'
    )

    rows = []

    for i in messages[0].split():

        _, msg_data = mail.fetch(i, "(BODY.PEEK[TEXT])")

        try:
            body = msg_data[0][1].decode(errors="ignore")
        except:
            continue

        name, date, route, price = extract(body)

        # filtre passager
        if passenger_name and name:
            if passenger_name.upper() not in name:
                continue

        if price:
            rows.append([name, date, route, price])

    return pd.DataFrame(rows, columns=["Name", "Date", "Route", "Price"])

# ---------------- CACHE ----------------
@st.cache_data(ttl=3600)
def fetch_flights_cached(user, pwd, pname):
    return fetch_flights()

# ---------------- CALCUL ----------------
def compute(df):

    vols = len(df)
    cout_vols = df["Price"].sum()

    frais = peages + parking + hotel + autres
    total = cout_vols + frais

    return vols, cout_vols, frais, total

# ---------------- ACTION ----------------
if st.button("Lancer analyse pilote"):

    if not email_user or not email_pass:
        st.error("Email et mot de passe requis")
    else:

        df = fetch_flights_cached(email_user, email_pass, passenger_name)

        vols, cout_vols, frais, total = compute(df)

        # ---------------- HEADER ----------------
        st.subheader(f"👤 Passager : {passenger_name if passenger_name else 'Tous'}")

        # ---------------- KPI ----------------
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Vols", vols)
        col2.metric("Coût vols", f"{cout_vols:.2f} €")
        col3.metric("Frais annexes", f"{frais:.2f} €")
        col4.metric("Total annuel", f"{total:.2f} €")

        st.divider()

        # ---------------- TABLE ----------------
        st.subheader("📋 Détail des vols")
        st.dataframe(df)

        # ---------------- GRAPHIQUES ----------------
        if not df.empty:

            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

            st.subheader("📊 Coût par vol")
            fig1 = px.bar(df, x="Date", y="Price")
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("📈 Évolution mensuelle")
            monthly = df.groupby(df["Date"].dt.month)["Price"].sum().reset_index()

            fig2 = px.line(monthly, x="Date", y="Price", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

        # ---------------- EXPORT ----------------
        st.download_button(
            "📥 Export CSV",
            df.to_csv(index=False).encode(),
            "pilot_dashboard.csv",
            "text/csv"
        )

        # ---------------- SYNTHÈSE ----------------
        st.subheader("🧾 Synthèse")

        st.write("Base totale :", f"{total:.2f} €")