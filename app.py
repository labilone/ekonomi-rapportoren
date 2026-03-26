import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

# --- 1. FUNKTION FÖR ATT SKAPA EN PROFFSIG PDF MED MOMS-DATA ---
def create_pdf(summary, company_name):
    pdf = FPDF()
    pdf.add_page()
    
    # --- DESIGN ---
    brand_color = (46, 204, 113) # Grön för vinst
    alert_color = (231, 76, 60)   # Röd för moms/utgifter
    
    pdf.set_fill_color(*brand_color)
    pdf.rect(0, 0, 210, 5, 'F')
    
    # Header
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 26)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, "EKONOMISK ANALYS & MOMS-PROGNOS", ln=True, align='L')
    
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 10, f"Foretag: {company_name.upper()}", ln=True, align='L')
    pdf.cell(0, 5, "Status: Beraknad inkl. moms (25%)", ln=True, align='L')
    
    pdf.ln(15)
    
    # --- RESULTAT-SEKTION ---
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(44, 62, 80)
    
    # Försäljning Brutto
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(90, 12, " Total Forsaljning (Brutto):", fill=True)
    pdf.cell(100, 12, f"{summary['Brutto']} kr ", fill=True, align='R', ln=True)
    pdf.ln(2)
    
    # Moms-reservering
    pdf.set_text_color(*alert_color)
    pdf.cell(90, 12, " Moms att reservera (25%):", fill=True)
    pdf.cell(100, 12, f"- {summary['Moms']} kr ", fill=True, align='R', ln=True)
    pdf.ln(2)
    
    # Kostnader
    pdf.set_text_color(44, 62, 80)
    pdf.cell(90, 12, " Totala Kostnader:", fill=True)
    pdf.cell(100, 12, f"- {summary['Kostnad']} kr ", fill=True, align='R', ln=True)
    
    pdf.ln(15)
    
    # --- NETTOVINST (DET VIKTIGASTE NUMRET) ---
    pdf.set_draw_color(*brand_color)
    pdf.set_line_width(1)
    pdf.set_text_color(*brand_color)
    pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 25, f"DIN NETTOVINST: {summary['Vinst']} kr", ln=True, align='C', border=1)
    
    # Tips-ruta
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 10, f"Rad: Baserat pa din forsaljning bor du ha minst {summary['Moms']} kr tillgangligt pa ditt skattekonto for kommande momsbetalning.")
    
    # Footer
    pdf.set_y(-25)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(189, 195, 199)
    pdf.cell(0, 10, "Rapporten ar framtagen automatiskt via RapportMastaren. Ej juridisk radgivning.", align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 2. WEBBGRÄNSSNITT (STREAMLIT) ---
st.set_page_config(page_title="RapportMästaren AI", page_icon="💰", layout="centered")

# Snyggare styling
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .main { background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 RapportMästaren")
st.write("Ladda upp din data – vi sköter moms, skatt och analys åt dig.")

with st.expander("Inställningar"):
    company = st.text_input("Företagsnamn", "Mitt Företag AB")
    vat_rate = st.slider("Momssats (%)", 0, 25, 25)

uploaded_file = st.file_uploader("Dra in din fil (Excel eller CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # Läs filen
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        
        # Kolumn-tvätt
        intakt_syn = ['intäkt', 'intakt', 'inkomst', 'försäljning', 'belopp', 'revenue', 'amount']
        kostnad_syn = ['kostnad', 'utgift', 'utlägg', 'cost', 'expenses']
        
        found_i, found_k = None, None
        clean_cols = {c.lower().strip(): c for c in df.columns}
        
        for s in intakt_syn: 
            if s in clean_cols: found_i = clean_cols[s]; break
        for s in kostnad_syn: 
            if s in clean_cols: found_k = clean_cols[s]; break

        if found_i and found_k:
            # Rensa valuta-tecken och räkna
            def to_num(col): return pd.to_numeric(df[col].replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

            brutto = to_num(found_i).sum()
            kostnad = to_num(found_k).sum()
            
            # --- BERÄKNINGAR ---
            moms_faktor = 1 + (vat_rate / 100)
            netto_intakt = brutto / moms_faktor
            moms_belopp = brutto - netto_intakt
            vinst_netto = netto_intakt - (kostnad / moms_faktor) # Förenklad vinst-efter-moms

            summary = {
                "Brutto": f"{brutto:,.2f}",
                "Moms": f"{moms_belopp:,.2f}",
                "Kostnad": f"{kostnad:,.2f}",
                "Vinst": f"{vinst_netto:,.2f}"
            }

            # Visa dashboard
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Försäljning (Brutto)", f"{brutto:,.0f} kr")
            c2.metric("Moms att betala", f"{moms_belopp:,.0f} kr", delta_color="inverse")
            c3.metric("Vinst (Netto)", f"{vinst_netto:,.0f} kr")

            # PDF-Knapp
            pdf_bytes = create_pdf(summary, company)
            st.divider()
            st.download_button(
                label="✅ GENERERA PROFFSIG ANALYS (PDF)",
                data=pdf_bytes,
                file_name=f"Analys_{company}.pdf",
                mime="application/pdf"
            )
            
        else:
            st.error("Vi hittade inte rätt kolumner. Dubbelkolla att de heter 'Intäkt' och 'Kostnad'.")
            
    except Exception as e:
        st.error(f"Ett fel uppstod: {e}")

st.divider()
st.caption("Verktyget räknar automatiskt bort 25% moms från din bruttoförsäljning.")