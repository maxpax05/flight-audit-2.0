import streamlit as st
import imaplib
import re
import pandas as pd
import plotly.express as px

# ---------------- CONFIG ----------------
IMAP_SERVER = "imap.mail.yahoo.com"

SENDER = "gpnet@xmedia.airfrance.fr"
SUBJECT_KEY = "Confirmation"

st.set_page_config(page_title="Pilot Dashboard 3.2", layout="wide")

st.title("✈️ Pilot Dashboard 3.2")

# ---------------- INPUT ----------------
passenger_name = st.text_input("Nom du passager")

email_user = st.text_input("Yahoo email")
email_pass = st.text_input("App password Yahoo", type="password")

st.divider()

st.subheader("💸 Frais annexes")

peages = st.number_input("Péages (€)", value=0.0)
parking = st.number_input("Parking (€)", value=0.0)
hotel = st.number_input("Hôtel (€)", value=0.0)
autres = st.number_input("Autres frais (€)", value=0.0)

# ---------------- PARSING ----------------
def extract(body):

    price = re.search(r'(\d+[.,]\d{2})\s?€', body)
    date = re.search(r'\d{2}/\d{2}/\d{4}', body)
    route = re.search(r'[A-Z]{3}\s*-\s*[A-Z]{3}', body)

    return (
        date.group(0) if date else None,
        route.group(0) if route else None,
        float(price.group(1).replace(',', '.')) if price else None
    )

# ---------------- FETCH OPTIMISÉ ----------------
def fetch_flights():

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(email_user, email_pass)
    mail.select("inbox")

    # FILTRAGE CÔTÉ SERVEUR (ULTRA IMPORTANT)
    status, messages = mail.search(
        None,
        '(FROM "gpnet@xmedia.airfrance.fr" SUBJECT "Confirmation" SINCE "01-Jan-2025" BEFORE "01-Jan-2026")'
    )

    rows = []

    for i in messages[0].split():

        # TEXTE SEULEMENT (beaucoup plus rapide)
        _, msg_data = mail.fetch(i, "(BODY.PEEK[TEXT])")

        try:
            body = msg_data[0][1].decode(errors="ignore")
        except:
            continue

        date, route, price = extract(body)

        if price:
            rows.append([date, route, price])

    return pd.DataFrame(rows, columns=["Date", "Route", "Price"])


# ---------------- CACHE ----------------
@st.cache_data(ttl=3600)
def fetch_flights_cached(user, pwd):
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

        df = fetch_flights_cached(email_user, email_pass)

        vols, cout_vols, frais, total = compute(df)

        # ---------------- HEADER ----------------
        st.subheader(f"👤 Passager : {passenger_name if passenger_name else 'Non renseigné'}")

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
        df.insert(0, "Passenger", passenger_name)

        st.download_button(
            "📥 Export CSV",
            df.to_csv(index=False).encode(),
            "pilot_dashboard.csv",
            "text/csv"
        )

        # ---------------- SYNTHÈSE ----------------
        st.subheader("🧾 Synthèse")

        st.write("Base totale :", f"{total:.2f} €")