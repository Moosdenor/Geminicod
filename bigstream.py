import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf  # NIEUW: Dit pakketje haalt het nieuws en de cijfers op
from finvizfinance.screener.overview import Overview

# Zorgt ervoor dat de app over de hele breedte van je scherm staat
st.set_page_config(page_title="Beurs Dashboard", layout="wide")

st.title("Beurs Dashboard: Screener, Insiders & Nieuws")

# We maken nu DRIE tabbladen aan voor een overzichtelijk dashboard
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
            # De uitgebreide link die direct de 100 nieuwste rijen ophaalt
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

            # We maken een leeg mandje waar we de allergrootste tabel in gaan stoppen
            grootste_tabel = pd.DataFrame()

            for tabel in tabellen:
                tabel.columns = [str(kolom).replace('\xa0', ' ').strip() for kolom in tabel.columns]

                if all(kolom in tabel.columns for kolom in gezochte_kolommen):
                    # Als deze tabel meer rijen heeft dan degene in ons mandje, wisselen we ze om!
                    if len(tabel) > len(grootste_tabel):
                        grootste_tabel = tabel[gezochte_kolommen]

            # Als we een tabel hebben gevonden, geven we die mooie Nederlandse namen
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
# TAB 3: Nieuws & Cijfers (Nieuw!)
# ==========================================
with tab3:
    st.header("Het laatste nieuws en bedrijfsinfo")
    st.write("Laat de zoekbalk leeg voor algemeen beursnieuws, of typ een afkorting (zoals SOFI) voor specifiek nieuws en cijfers.")

    # Het invulveld. Standaard is het helemaal leeg.
    ingevulde_ticker = st.text_input("Typ een beursafkorting:", "")

    # Als het veld leeg is, gebruiken we de afkorting 'SPY' op de achtergrond.
    # SPY volgt de 500 grootste bedrijven, dus dat geeft perfect algemeen marktnieuws.
    zoek_ticker = ingevulde_ticker if ingevulde_ticker != "" else "SPY"
    
    # We passen de titel aan afhankelijk van wat je hebt ingetypt
    titel_tekst = ingevulde_ticker.upper() if ingevulde_ticker != "" else "de Algemene Beurs"

    st.subheader(f"Laatste nieuws over {titel_tekst}")
    
    with st.spinner("Nieuws ophalen..."):
        try:
            aandeel = yf.Ticker(zoek_ticker)
            nieuws_berichten = aandeel.news
            
            if nieuws_berichten:
                for artikel in nieuws_berichten[:5]: # We laten de 5 nieuwste artikelen zien
                    # Maakt een klikbare link aan van de titel
                    st.markdown(f"**[{artikel['title']}]({artikel['link']})**")
                    st.write("---") # Een mooi streepje tussen de artikelen
            else:
                st.write("Er is op dit moment geen nieuws gevonden.")
        except Exception as e:
            st.error("Het ophalen van het nieuws is even niet gelukt.")

    # We laten de financiële cijfers ALLEEN zien als je echt zelf een bedrijf hebt ingetypt.
    # Bij algemeen nieuws heeft dit namelijk niet zoveel nut.
    if ingevulde_ticker != "":
        st.subheader(f"Hoe gezond is {ingevulde_ticker.upper()}?")
        
        with st.spinner("Cijfers ophalen..."):
            try:
                info = aandeel.info
                
                # We maken drie kolommen naast elkaar voor een mooi overzicht
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    prijs = info.get('currentPrice', 'Onbekend')
                    st.metric("Huidige Prijs", f"${prijs}" if prijs != 'Onbekend' else prijs)
                    
                with col_b:
                    # Winst per aandeel: is het positief (winst) of negatief (verlies)?
                    winst = info.get('trailingEps', 'Onbekend')
                    st.metric("Winst per aandeel", f"${winst}" if winst != 'Onbekend' else winst)
                    
                with col_c:
                    # Wat zeggen de professionele investeerders?
                    advies = info.get('recommendationKey', 'Onbekend').replace('_', ' ').upper()
                    st.metric("Advies van experts", advies)
            except Exception as e:
                st.error("Kon de bedrijfscijfers niet goed inladen.")
