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
# TAB 2: Insider Trading (Via OpenInsider)
# ==========================================
with tab2:
    st.header("Wat doen de directeuren? (Insider Trading)")
    st.write("Hier zie je de nieuwste transacties, direct uit de officiële database.")
    
    @st.cache_data
    def haal_insider_data_op():
        try:
            # We stappen over naar OpenInsider, die blokkeren de app niet!
            url = "http://openinsider.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
            }
            reactie = requests.get(url, headers=headers)
            
            # We zoeken naar de tabellen op de pagina
            tabellen = pd.read_html(reactie.text)
            
            # We zoeken de tabel waar het woord 'Ticker' in de titel staat
            for tabel in tabellen:
                if 'Ticker' in tabel.columns:
                    # We pakken alleen de kolommen die we echt interessant vinden
                    mooie_tabel = tabel[['Trade Date', 'Ticker', 'Company Name', 'Insider Name', 'Title', 'Trade Type', 'Price', 'Qty', 'Value']]
                    # We maken er meteen mooie Nederlandse namen van!
                    mooie_tabel.columns = ['Datum', 'Ticker', 'Bedrijf', 'Naam Directeur', 'Functie', 'Type Transactie', 'Prijs', 'Aantal', 'Waarde']
                    return mooie_tabel
                    
            return pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
            
    with st.spinner("Bezig met ophalen van de nieuwste transacties..."):
        df_insider = haal_insider_data_op()
        
    if not df_insider.empty:
        st.success("De nieuwste transacties zijn succesvol binnengehaald!")
        # Laat de tabel zien
        st.dataframe(df_insider, height=600)
        
        st.download_button(
            label="Download Data als CSV",
            data=df_insider.to_csv(index=False).encode('utf-8'),
            file_name="insider_trading.csv",
            mime="text/csv"
        )
    else:
        st.error("Het is helaas niet gelukt de gegevens op te halen.")
