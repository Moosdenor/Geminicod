import streamlit as st
import pandas as pd
import requests
import io
from finvizfinance.screener.overview import Overview
from finvizfinance.news import News
from finvizfinance.quote import finvizfinance

# Zorgt ervoor dat de app over de hele breedte van je scherm staat
st.set_page_config(page_title="Finviz Screener, Insiders & Nieuws", layout="wide")

st.title("Finviz Stock Screener, Insider Trading & Nieuws")

# Maak drie tabbladen aan voor een overzichtelijk dashboard
tab1, tab2, tab3 = st.tabs(["Algemene Screener", "Recente Insider Trading", "Nieuws & Cijfers"])

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

        # Laat de tabel zien met een blauw kleurverloop voor de prijs
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
            # Haalt direct de 100 nieuwste transacties op
            url = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=730&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
            }
            reactie = requests.get(url, headers=headers)

            if reactie.status_code != 200:
                st.error(f"De website weigert toegang. Foutcode: {reactie.status_code}")
                return pd.DataFrame()

            tabellen = pd.read_html(io.StringIO(reactie.text))

            gezochte_kolommen = ['Trade Date', 'Ticker', 'Company Name', 'Insider Name', 'Title', 'Trade Type', 'Price', 'Qty', 'Value']

            grootste_tabel = pd.DataFrame()

            for tabel in tabellen:
                tabel.columns = [str(kolom).replace('\xa0', ' ').strip() for kolom in tabel.columns]

                if all(kolom in tabel.columns for kolom in gezochte_kolommen):
                    if len(tabel) > len(grootste_tabel):
                        grootste_tabel = tabel[gezochte_kolommen]

            if not grootste_tabel.empty:
                grootste_tabel.columns = ['Datum', 'Ticker', 'Bedrijf', 'Naam Directeur', 'Functie', 'Type Transactie', 'Prijs', 'Aantal', 'Waarde']
                return grootste_tabel
            else:
                st.error("Kon de juiste tabel niet vinden op de pagina.")
                return pd.DataFrame()

        except Exception as e:
            st.error(f"Er ging iets mis in de code: {e}")
            return pd.DataFrame()

    with st.spinner("Bezig met ophalen van de nieuwste transacties..."):
        df_insider = haal_insider_data_op()

    if not df_insider.empty:
        st.success(f"Er zijn {len(df_insider)} transacties succesvol binnengehaald!")
        st.dataframe(df_insider, height=600)
    else:
        st.warning("Geen data om te laten zien.")

# ==========================================
# TAB 3: Nieuws & Cijfers (Via Finviz)
# ==========================================
with tab3:
    st.header("Het laatste nieuws en bedrijfsinfo")
    st.write("Laat de zoekbalk leeg voor algemeen beursnieuws, of typ een afkorting (zoals SOFI) voor specifiek nieuws en cijfers.")

    # Het invulveld
    ingevulde_ticker = st.text_input("Typ een beursafkorting:", "").strip().upper()
    titel_tekst = ingevulde_ticker if ingevulde_ticker != "" else "de Algemene Beurs"

    st.subheader(f"Laatste nieuws over {titel_tekst}")
    
    with st.spinner("Nieuws ophalen..."):
        try:
            if ingevulde_ticker == "":
                # Algemeen marktnieuws ophalen
                fnews = News()
                nieuws_data = fnews.get_news()
                nieuws_df = nieuws_data['news']
            else:
                # Nieuws specifiek voor het gekozen aandeel
                stock = finvizfinance(ingevulde_ticker)
                nieuws_df = stock.ticker_news()

            # We laten de 5 nieuwste artikelen zien
            if not nieuws_df.empty:
                for index, row in nieuws_df.head(5).iterrows():
                    titel = row.get('Title', row.get('title', 'Geen titel'))
                    link = row.get('Link', row.get('link', '#'))
                    st.markdown(f"**[{titel}]({link})**")
                    st.write("---")
            else:
                st.write("Er is op dit moment geen nieuws gevonden.")
                
        except Exception as e:
            st.error(f"Het ophalen van het nieuws is niet gelukt. Foutmelding: {e}")

    # Cijfers tonen we alleen als je daadwerkelijk een bedrijf hebt ingetypt
    if ingevulde_ticker != "":
        st.subheader(f"Hoe staat {ingevulde_ticker} ervoor?")
        
        with st.spinner("Cijfers ophalen..."):
            try:
                stock = finvizfinance(ingevulde_ticker)
                info = stock.ticker_fundament()
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    prijs = info.get('Price', 'Onbekend')
                    st.metric("Huidige Prijs", f"${prijs}" if prijs != 'Onbekend' else prijs)
                    
                with col_b:
                    # Winst per aandeel (positief is winst, negatief is verlies)
                    winst = info.get('EPS (ttm)', 'Onbekend')
                    st.metric("Winst per aandeel", f"${winst}" if winst != 'Onbekend' else winst)
                    
                with col_c:
                    # Advies op een schaal van 1 (kopen) tot 5 (verkopen)
                    advies = info.get('Recom', 'Onbekend')
                    st.metric("Advies van analisten (1=Kopen, 5=Verkopen)", advies)
                    
            except Exception as e:
                st.error("Kon de bedrijfscijfers niet ophalen. Controleer of de afkorting klopt.")
