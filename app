import streamlit as st
import imaplib
import email
import re
import pandas as pd

# ---------------- CONFIG ----------------
IMAP_SERVER = "imap.mail.yahoo.com"

SENDER = "gpnet@xmedia.airfrance.fr"
SUBJECT_KEY = "Confirmation de reservation"

# ---------------- UI ----------------
st.set_page_config(page_title="Flight Audit 2.0")

st.title("✈️ Flight Audit 2.0")

email_user = st.text_input("Email Yahoo")
email_pass = st.text_input("Mot de passe application", type="password")

# ---------------- PARSING ----------------
def extract_data(body):
    """
    Extraction robuste basée sur structure Air France
    """

    # Prix TTC
    price = re.search(r'(\d+[.,]\d{2})\s?€', body)
    price = float(price.group(1).replace(',', '.')) if price else None

    # Date
    date = re.search(r'\d{2}/\d{2}/\d{4}', body)
    date = date.group(0) if date else None

    # Trajet (format AAA-AAA)
    route = re.search(r'[A-Z]{3}\s*-\s*[A-Z]{3}', body)
    route = route.group(0) if route else None

    return date, route, price

# ---------------- FETCH ----------------
def fetch():

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(email_user, email_pass)
    mail.select("inbox")

    status, messages = mail.search(
        None,
        '(SINCE "01-Jan-2025" BEFORE "01-Jan-2026")'
    )

    ids = messages[0].split()

    rows = []
    total = 0

    for i in ids:

        status, msg_data = mail.fetch(i, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject = str(msg["subject"])
        sender = str(msg["from"])

        # FILTRE STRICT
        if SENDER not in sender:
            continue

        if SUBJECT_KEY.lower() not in subject.lower():
            continue

        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode(errors="ignore")
                    except:
                        pass

        date, route, price = extract_data(body)

        if price:
            rows.append([date, route, price])
            total += price

    df = pd.DataFrame(rows, columns=["Date", "Route", "Price"])

    return df, total


# ---------------- ACTION ----------------
if st.button("Lancer analyse 2025"):

    if not email_user or not email_pass:
        st.error("Champs manquants")
    else:
        df, total = fetch()

        st.success("Analyse terminée")

        st.write("Total :", total, "€")
        st.write("Nombre de vols :", len(df))

        st.dataframe(df)

        csv = df.to_csv(index=False).encode()

        st.download_button(
            "Télécharger CSV",
            csv,
            "flights_2.0.csv",
            "text/csv"
        )