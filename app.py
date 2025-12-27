import streamlit as st
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
import plotly.express as px

# --- PAGE SETTINGS ---
st.set_page_config(page_title="PharmaLytics", layout="wide", page_icon="💊")

st.title("💊 PharmaLytics: Pharmacy Analytics Dashboard")
st.markdown("*AI-driven insights for pharmacy operations, inventory optimization, and cross-selling strategies.*")

# --- SIDEBAR ---
st.sidebar.header("Data Configuration")
uploaded_file = st.sidebar.file_uploader("Upload Sales Report (Excel)", type=["xlsx", "xls"])

# --- DATA LOADING FUNCTION ---
@st.cache_data
def load_and_clean_data(file):
    # 1. Read Excel
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    
    # 2. Rename Columns
    column_mapping = {
        'Ürün Adı': 'Product_Name',
        'Satış Adet': 'Quantity',
        'Net Tutar': 'Total_Price',
        'İşlem Tipi': 'Transaction_Type',
        'Barkod': 'Barcode'
    }
    df.rename(columns=column_mapping, inplace=True)
    
    # 3. DATE FIX
    if 'Tarih' in df.columns and 'Saat' in df.columns:
        df['Date_Combined'] = df['Tarih'].astype(str) + " " + df['Saat'].astype(str)
        df['Date'] = pd.to_datetime(df['Date_Combined'], dayfirst=True, errors='coerce')
    elif 'TarihSaat' in df.columns:
        df['Date'] = pd.to_datetime(df['TarihSaat'], dayfirst=True, errors='coerce')
    else:
        st.error(f"⚠️ Error: Date column not found. Columns detected: {df.columns.tolist()}")
        st.stop()
        
    df = df.sort_values(by='Date')
    
    # --- FILTERS ---
    
    # A) Only Sales
    if 'Transaction_Type' in df.columns:
        df = df[df['Transaction_Type'].astype(str).str.contains("Satış|Satis|SATIS", case=False, na=False)]
    
    # B) Remove Closed Period
    mask_open = (df['Date'] < '2024-09-13') | (df['Date'] > '2024-10-31')
    df = df[mask_open]
    
    # C) Excluded Products (Updated List)
    EXCLUDED_PRODUCTS = [
        "KAN ÜRÜNÜ 1 ADI", "KAN ÜRÜNÜ 2 ADI", "POŞET", "Eczane Poşeti",
        "OCTAGAM 10 G/200 ML IV INFUZYONLUK COZELTI(10 GR)", 
        "EMOCLOT-DI 1.000 IU (FACTOR 8) 1 FLK",
        "MOUNJARO 2,5 MG/0,5 ML ENJEKSIYONLUK COZELTI (4 ADET)", 
        "MOUNJARO 10 MG/0,5 ML ENJEKSIYONLUK COZELTI (4 ADET)", 
        "MOUNJARO 5 MG/0,5 ML ENJEKSIYONLUK COZELTI (4 ADET)", 
        "MOUNJARO 7,5 MG/0,5 ML ENJEKSIYONLUK COZELTI (4 ADET)", 
        "XTANDI 40 MG YUMUSAK KAPSUL (112 KAPSUL)", 
        "ERLEADA 60 MG FILM KAPLI TABLET (120 TABLET)", 
        "ARANESP 40 MCG.4 KULL.HAZIR SIRINGA", 
        "EMGALITY 120 MG/ML ENJEKSIYONLUK COZELTI ICEREN KULLANIMA HAZIR KALEM (1 KALEM)", 
        "NUCALA 100 MG/ML SC ENJEKSIYONLUK COZELTI ICEREN KULLANIMA HAZIR KALEM (1 ADET)", 
        "OZEMPIC 1 MG ENJEKSIYONLUK COZELTI ICEREN KULLANIMA HAZIR KALEM (1 ADET)", 
        "VERXANT 150 MG/1 ML ENJEKSIYONLUK COZELTI ICEREN KULLANIMA HAZIR KALEM",
        "ABOUND PORTAKAL AROMALI TOZ 24 GR 30 POSET(2.670 KCAL)",
        "GENOTROPIN 36 IU (12 MG) GOQUICK ENJ. SOL. ICIN TOZ VE COZ. ICEREN KULL. HAZIR KALEM",
        "EPOBEL 5000 IU/0,5 ML I.V. /S.C. STERIL ENJEKSIYONLUK COZELTI ICEREN KULLANIMA HAZIR ENJEKTOR 6 ENJE",
        "ELIQUIS 2,5 MG FILM KAPLI 56 TABLET",
        "ARANESP 60 MCG.4 KULL.HAZIR SIRINGA"
    ]
    
    if 'Product_Name' in df.columns:
        df = df[~df['Product_Name'].isin(EXCLUDED_PRODUCTS)]
    
    return df

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean_data(uploaded_file)
        
        # Info Metrics
        min_date = df['Date'].min().strftime('%Y-%m-%d')
        max_date = df['Date'].max().strftime('%Y-%m-%d')
        total_sales = df['Total_Price'].sum()
        
        st.success(f"✅ Analysis Ready! Data Period: {min_date} to {max_date} | Total Revenue: {total_sales:,.2f} TL")
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["🛒 Cross-Selling (AI)", "⏰ Shift Analysis", "💰 ABC Revenue"])
        
        # === TAB 1: MARKET BASKET ===
        with tab1:
            st.header("Cross-Selling Recommendations")
            st.write("Sensitivity Settings:")
            min_support_val = st.slider("Min Support Threshold", 0.001, 0.05, 0.001, 0.001, format="%.3f")
            
            basket = (df.groupby(['Date', 'Product_Name'])['Quantity']
                      .sum().unstack().reset_index().fillna(0)
                      .set_index('Date'))
            
            def encode_units(x): return 1 if x >= 1 else 0
            basket_sets = basket.applymap(encode_units)
            
            with st.spinner('AI is analyzing patterns...'):
                frequent_itemsets = apriori(basket_sets, min_support=min_support_val, use_colnames=True)
            
            if not frequent_itemsets.empty:
                rules = association_rules(frequent_itemsets, metric="lift", min_threshold=0.1)
                rules = rules.sort_values(['lift'], ascending=False)
                
                display = rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].head(20)
                display['antecedents'] = display['antecedents'].apply(lambda x: list(x)[0])
                display['consequents'] = display['consequents'].apply(lambda x: list(x)[0])
                
                st.write(f"Found {len(rules)} relationships!")
                st.dataframe(display, use_container_width=True)
            else:
                st.warning("No patterns found yet.")

        # === TAB 2: SHIFT ANALYSIS (UPDATED) ===
        with tab2:
            st.header("Operational Density by Shift")
            
            # 1. Extract Time Info
            df['Hour'] = df['Date'].dt.hour
            df['Day'] = df['Date'].dt.day_name()
            
            # 2. DEFINE SHIFTS (BINNING)
            def get_time_slot(hour):
                if 8 <= hour < 12:
                    return '1. Morning (08-12)'
                elif 12 <= hour < 14:
                    return '2. Lunch Break (12-14)'
                elif 14 <= hour < 17:
                    return '3. Afternoon (14-17)'
                elif 17 <= hour < 20:
                    return '4. Evening Rush (17-20)'
                else:
                    return '5. Night/Duty'

            # Apply Logic
            df['Shift'] = df['Hour'].apply(get_time_slot)
            
            # 3. VISUALIZATION
            heatmap_data = df.groupby(['Day', 'Shift'])['Product_Name'].count().reset_index()
            
            # Custom Sorting
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            shift_order = ['1. Morning (08-12)', '2. Lunch Break (12-14)', '3. Afternoon (14-17)', '4. Evening Rush (17-20)', '5. Night/Duty']
            
            # Heatmap
            fig_heat = px.density_heatmap(heatmap_data, x='Shift', y='Day', z='Product_Name', 
                                     category_orders={"Day": days_order, "Shift": shift_order},
                                     color_continuous_scale='Viridis',
                                     title="Which Shift is Busiest?")
            st.plotly_chart(fig_heat, use_container_width=True)
            
            # Trend Line
            st.divider()
            st.subheader("Hourly Trend Detail")
            hourly_trend = df.groupby('Hour')['Product_Name'].count().reset_index()
            fig_line = px.line(hourly_trend, x='Hour', y='Product_Name', title="Total Sales Volume by Hour", markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

        # === TAB 3: ABC ANALYSIS ===
        with tab3:
            st.header("Top Revenue Products")
            prod_sales = df.groupby('Product_Name')['Total_Price'].sum().reset_index().sort_values('Total_Price', ascending=False)
            prod_sales['Class'] = pd.qcut(prod_sales['Total_Price'].rank(method='first', ascending=False), 3, labels=['A (Top)', 'B (Mid)', 'C (Low)'])
            
            fig2 = px.bar(prod_sales.head(20), x='Product_Name', y='Total_Price', color='Class', 
                          color_discrete_map={'A (Top)': '#EF553B', 'B (Mid)': '#00CC96', 'C (Low)': '#636EFA'})
            st.plotly_chart(fig2, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error details: {e}")

else:
    st.info("👈 Upload your Excel file to start.")