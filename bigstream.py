import streamlit as st
import pandas as pd
import requests
from finvizfinance.screener.overview import Overview

# Zorgt ervoor dat de app over de hele breedte van je scherm staat
st.set_page_config(page_title="Finviz Screener & Insiders", layout="wide")

st.title("Finviz Stock Screener & Insider Trading")

# Maak twee tabbladen aan voor een overzichtelijk dashboard
tab1, tab2 = st.tabs(["Algemene Screener", "Recente Insider Trading"])

# ==========================================
# TAB 1: Algemene Aandelen Screener
# ==========================================
with tab1:
    st.header("Algemene Aandelen Screener")
    st.write("Zoek naar aandelen op basis van beurs en sector.")
    
    col1, col2 = st.columns(2)
    with col1:
        exchange = st.selectbox("Beurs", ["AMEX", "NASDAQ", "NYSE"], index=1)
    with col2:
        sector = st.selectbox("Sector", [
            "Basic Materials", "Communication Services", "Consumer Cyclical",
            "Consumer Defensive", "Energy", "Financial", "Healthcare",
            "Industrials", "Real Estate", "Technology", "Utilities"
        ], index=0)

    def get_screener_data(exchange, sector):
        try:
            foverview = Overview()
            filters_dict = {'Exchange': exchange, 'Sector': sector}
            foverview.set_filter(filters_dict=filters_dict)
            df = foverview.screener_view()
            
            if not df.empty:
                # Voeg een klikbare link toe
                df['Finviz Link'] = df['Ticker'].apply(
                    lambda x: f'https://finviz.com/quote.ashx?t={x}'
                )
            return df
        except Exception as e:
            st.error(f"Fout bij ophalen data: {e}")
            return pd.DataFrame()

    with st.spinner("Bezig met ophalen van data..."):
        df_screener = get_screener_data(exchange, sector)

    if not df_screener.empty:
        st.success(f"{len(df_screener)} aandelen gevonden voor {exchange} - {sector}")
        
        # Laat de tabel zien met een mooi blauw kleurverloop voor de prijs
        st.dataframe(
            df_screener.style.background_gradient(cmap='Blues', subset=['Price'])
            .format({'Price': '${:.2f}', 'Dividend %': '{:.2f}%'}, na_rep="N/A"),
            height=400,
            column_config={
                "Finviz Link": st.column_config.LinkColumn("Finviz Details")
            }
        )
    else:
        st.warning("Geen aandelen gevonden voor deze filters.")

# ==========================================
# TAB 2: De nieuwe en slimmere Insider Trading check
# ==========================================
with tab2:
    st.header("Wat doen de directeuren? (Insider Trading)")
    st.write("Hier zie je direct of directeuren of grote eigenaren hun eigen aandelen kopen of verkopen.")
    
    # We slaan de data tijdelijk op (cache) zodat de app lekker snel blijft als je wisselt van tab
    @st.cache_data
    def haal_insider_data_op():
        try:
            # Hier is het trucje: we doen alsof we een normale Mac-browser zijn
            url = "https://finviz.com/insidertrading.ashx"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # We halen de website op met ons 'masker' op
            reactie = requests.get(url, headers=headers)
            
            # We laten de code automatisch naar tabellen op de website zoeken
            tabellen = pd.read_html(reactie.text)
            
            # De tabel met directeuren heeft altijd 10 kolommen op Finviz, dus die pakken we eruit
            for tabel in tabellen:
                if len(tabel.columns) == 10:
                    # We maken de kolomnamen meteen netjes en makkelijk leesbaar
                    tabel.columns = ['Ticker', 'Eigenaar', 'Functie', 'Datum', 'Transactie', 'Prijs', 'Aantal', 'Waarde ($)', 'Totaal Aandelen', 'SEC Link']
                    return tabel
                    
            return pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
            
    with st.spinner("Bezig met ophalen van de nieuwste transacties..."):
        df_insider = haal_insider_data_op()
        
    if not df_insider.empty:
        st.success("De nieuwste transacties zijn succesvol binnengehaald!")
        # Laat de tabel zien
        st.dataframe(df_insider, height=600)
        
        # Download knop
        st.download_button(
            label="Download Data als CSV",
            data=df_insider.to_csv(index=False).encode('utf-8'),
            file_name="insider_trading.csv",
            mime="text/csv"
        )
    else:
        st.error("Het is helaas niet gelukt de gegevens op te halen. De website blokkeert ons momenteel.")