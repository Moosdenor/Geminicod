import streamlit as st
import pandas as pd
import requests
import io
from finvizfinance.screener.overview import Overview
from finvizfinance.news import News
from finvizfinance.quote import finvizfinance

# Zorgt ervoor dat de app over de hele breedte van je scherm staat
st.set_page_config(page_title="Beurs Dashboard", layout="wide")

st.title("Beurs Dashboard: Screener, Insiders & Analyse")

# Drie overzichtelijke tabbladen
tab1, tab2, tab3 = st.tabs(["Algemene Screener", "Recente Insider Trading", "Aandelen Analyse & Nieuws"])

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
# TAB 3: Aandelen Analyse & Nieuws (10-Punten Score)
# ==========================================
with tab3:
    st.header("Aandelen Analyse & Nieuws")
    st.write("Laat de zoekbalk leeg voor algemeen nieuws, of typ een afkorting (zoals SOFI) voor een compleet rapport.")

    ingevulde_ticker = st.text_input("Typ een beursafkorting (bijv. SOFI of AAPL):", "").strip().upper()

    def naar_getal(tekst):
        try:
            return float(str(tekst).replace('%', '').replace(',', '').strip())
        except:
            return None

    if ingevulde_ticker != "":
        st.divider()
        st.subheader(f"Overzicht voor {ingevulde_ticker}")

        with st.spinner("Gegevens ophalen..."):
            try:
                stock = finvizfinance(ingevulde_ticker)
                info = stock.ticker_fundament()

                # --- BEREKENING GEZONDHEIDSSCORE (1 t/m 10) ---
                score = 0
                punten_uitleg = []

                # 1. Winst
                eps = naar_getal(info.get('EPS (ttm)'))
                if eps is not None and eps > 0:
                    score += 1
                    punten_uitleg.append("✅ Maakt winst (EPS is positief)")
                else:
                    punten_uitleg.append("❌ Maakt verlies (EPS is negatief)")

                # 2. Schulden
                debt = naar_getal(info.get('Debt/Eq'))
                if debt is not None and debt <= 1.0:
                    score += 1
                    punten_uitleg.append("✅ Gezonde schuldenlast ten opzichte van eigen vermogen")
                else:
                    punten_uitleg.append("❌ Hoge schulden ten opzichte van eigen vermogen")

                # 3. Korte termijn rekeningen
                curr_ratio = naar_getal(info.get('Current Ratio'))
                if curr_ratio is not None and curr_ratio >= 1.0:
                    score += 1
                    punten_uitleg.append("✅ Kan rekeningen op korte termijn makkelijk betalen")
                else:
                    punten_uitleg.append("❌ Weinig geld direct beschikbaar voor de lopende rekeningen")

                # 4. Winstmarge
                margin = naar_getal(info.get('Profit Margin'))
                if margin is not None and margin > 0:
                    score += 1
                    punten_uitleg.append("✅ Onder aan de streep is de winstmarge positief")
                else:
                    punten_uitleg.append("❌ Negatieve winstmarge (er lekt geld weg)")

                # 5. Directe geldreserves
                quick = naar_getal(info.get('Quick Ratio'))
                if quick is not None and quick >= 1.0:
                    score += 1
                    punten_uitleg.append("✅ Goede directe geldreserves (zonder voorraden mee te tellen)")
                else:
                    punten_uitleg.append("❌ Beperkte directe spaarreserves")

                # 6. Omzetgroei
                sales_qq = naar_getal(info.get('Sales Q/Q'))
                if sales_qq is not None and sales_qq > 0:
                    score += 1
                    punten_uitleg.append("✅ Omzet groeit vergeleken met vorig jaar")
                else:
                    punten_uitleg.append("❌ Omzet krimpt of stagneert")

                # 7. Winstgroei
                eps_qq = naar_getal(info.get('EPS Q/Q'))
                if eps_qq is not None and eps_qq > 0:
                    score += 1
                    punten_uitleg.append("✅ Winst stijgt vergeleken met vorig jaar")
                else:
                    punten_uitleg.append("❌ Winst krimpt of stagneert")

                # 8. Rendement op Eigen Vermogen (ROE)
                roe = naar_getal(info.get('ROE'))
                if roe is not None and roe > 10:
                    score += 1
                    punten_uitleg.append("✅ Sterk rendement op investeringen (ROE > 10%)")
                else:
                    punten_uitleg.append("❌ Laag rendement op het geld van aandeelhouders (ROE < 10%)")

                # 9. Waardering (P/E Ratio)
                pe = naar_getal(info.get('P/E'))
                if pe is not None and 0 < pe <= 30:
                    score += 1
                    punten_uitleg.append("✅ Aandeel is redelijk geprijsd (P/E onder de 30)")
                else:
                    punten_uitleg.append("❌ Aandeel is erg duur (P/E > 30) of het bedrijf maakt verlies")

                # 10. Operationele marge
                oper_margin = naar_getal(info.get('Oper. Margin'))
                if oper_margin is not None and oper_margin > 10:
                    score += 1
                    punten_uitleg.append("✅ Sterke operationele winstmarge (> 10%)")
                else:
                    punten_uitleg.append("❌ Lage operationele winstmarge (< 10%)")

                # --- BLOK 1: FINANCIËLE GEZONDHEID & SCORE ---
                st.markdown("#### 1. Gezondheid & Groei")
                if score >= 8:
                    st.success(f"🟢 **Rapportcijfer: {score} / 10 (Uitstekend & Gezond)**")
                elif score >= 5:
                    st.warning(f"🟡 **Rapportcijfer: {score} / 10 (Gemiddeld, bekijk de minpunten)**")
                else:
                    st.error(f"🔴 **Rapportcijfer: {score} / 10 (Kwetsbaar / Veel risico)**")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Winst per aandeel (EPS)", f"${info.get('EPS (ttm)', 'N/A')}")
                with c2:
                    st.metric("Schulden (Debt/Eq)", info.get('Debt/Eq', 'N/A'))
                with c3:
                    st.metric("Winstmarge", info.get('Profit Margin', 'N/A'))

                with st.expander("Bekijk de volledige 10-punten check"):
                    for punt in punten_uitleg:
                        st.write(punt)

                # --- BLOK 2: KOERS & VERWACHTINGEN ---
                st.markdown("#### 2. Koers & Verwachtingen")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Huidige Koers", f"${info.get('Price', 'N/A')}")
                with col2:
                    st.metric("Doelkoers Experts", f"${info.get('Target Price', 'N/A')}")
                with col3:
                    st.metric("Hoogste / Laagste (Jaar)", info.get('52W Range', 'N/A'))
                with col4:
                    st.metric("Advies (1=Koop, 5=Verkoop)", info.get('Recom', 'N/A'))

                # --- BLOK 3: VOLUME & HANDELSACTIVITEIT ---
                st.markdown("#### 3. Handelsactiviteit & Volume")
                col5, col6, col7 = st.columns(3)
                with col5:
                    st.metric("Dagvolume", info.get('Volume', 'N/A'))
                with col6:
                    st.metric("Gemiddeld Volume (3m)", info.get('Avg Volume', 'N/A'))
                with col7:
                    st.metric("Relatief Volume", info.get('Rel Volume', 'N/A'),
                              help="Boven de 1.0 betekent actiever dan normaal.")

                # --- BLOK 4: VERTROUWEN & DIVIDEND ---
                st.markdown("#### 4. Vertrouwen & Beloning")
                col8, col9, col10 = st.columns(3)
                with col8:
                    st.metric("Grote Fondsen (Inst Own)", info.get('Inst Own', 'N/A'))
                with col9:
                    st.metric("Gokt op daling (Short)", info.get('Short Float', 'N/A'))
                with col10:
                    st.metric("Dividend per Jaar", info.get('Dividend %', 'N/A'))

            except Exception as e:
                st.error("Kon de gegevens voor dit aandeel niet ophalen. Controleer of de afkorting klopt.")

        st.divider()

    # --- NIEUWSSECTIE ---
    titel_nieuws = ingevulde_ticker if ingevulde_ticker != "" else "de Algemene Beurs"
    st.subheader(f"Laatste nieuws over {titel_nieuws}")

    with st.spinner("Nieuws inladen..."):
        try:
            if ingevulde_ticker == "":
                fnews = News()
                nieuws_data = fnews.get_news()
                nieuws_df = nieuws_data['news']
            else:
                stock = finvizfinance(ingevulde_ticker)
                nieuws_df = stock.ticker_news()

            if not nieuws_df.empty:
                for _, row in nieuws_df.head(5).iterrows():
                    titel = row.get('Title', row.get('title', 'Geen titel'))
                    link = row.get('Link', row.get('link', '#'))
                    st.markdown(f"**[{titel}]({link})**")
                    st.write("---")
            else:
                st.write("Geen recent nieuws beschikbaar.")
        except Exception as e:
            st.error(f"Fout bij ophalen van het nieuws: {e}")
