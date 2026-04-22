"""
[TR] Streamlit Web Dashboard Modülü / [EN] Streamlit Web Dashboard Module
[TR] Supabase PostgreSQL veritabanından alınan verilerle ürün fiyatı değişimlerini görselleştiren web tabanlı bir kullanıcı arayüzü sağlar. / [EN] Provides a web-based UI to visualize product price changes over time using data from the Supabase PostgreSQL database.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import datetime
import config
from database import get_last_scan

st.set_page_config(page_title="Vatan RAM Tracker", page_icon="📈", layout="wide")

st.title("🖥️ Vatan RAM Fiyat Takip Paneli")
st.markdown("[TR] Veritabanına kaydedilen RAM fiyatlarının zamana göre değişim grafikleri. / [EN] Time-based charts of RAM prices saved in the database.")

# [TR] Sayfayı her 30 saniyede bir otomatik yenile / [EN] Auto-refresh page every 30 seconds
count = st_autorefresh(interval=30000, key="datarefresh")

# [TR] Veritabanı bağlantısı / [EN] Database connection
@st.cache_resource
def init_connection():
    try:
        return create_engine(config.DB_URL)
    except Exception as e:
        st.error(f"[TR] Veritabanına bağlanılamadı. Lütfen config.py içindeki DB_URL'yi kontrol edin. / [EN] Could not connect to database. Please check DB_URL in config.py. Hata/Error: {e}")
        return None

# [TR] Verileri cacheleyerek sitenin şimşek hızında açılmasını sağla / [EN] Cache data for lightning fast loads
@st.cache_data(ttl=25)
def get_dashboard_data():
    engine = init_connection()
    if not engine:
        return pd.DataFrame(), pd.DataFrame()
    
    products_df = pd.read_sql("SELECT * FROM products", engine)
    history_df = pd.read_sql("SELECT * FROM price_history ORDER BY timestamp ASC", engine)
    return products_df, history_df

engine = init_connection()

if engine:
    try:
        # [TR] Son tarama zamanını göster (Kompakt) / [EN] Show last scan time (Compact)
        last_scan = get_last_scan()
        if last_scan:
            next_scan = last_scan + datetime.timedelta(seconds=config.KONTROL_SIKLIGI_SANIYE)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.info(f"🔄 **Son Tarama:** {last_scan.strftime('%H:%M')}")
            col2.warning(f"⏳ **Sonraki Tarama:** {next_scan.strftime('%H:%M')}")
            
        st.markdown("---")
        
        # [TR] Verileri çek / [EN] Fetch data
        products_df, _ = get_dashboard_data()
        
        if products_df.empty:
            st.warning("[TR] Veritabanında henüz ürün bulunmuyor. Lütfen botun çalışmasını bekleyin. / [EN] No products in the database yet. Please wait for the bot to run.")
        else:
            # [TR] ARAMA VE SIRALAMA BARI / [EN] SEARCH AND SORT BAR
            scol1, scol2, scol3 = st.columns([2, 1, 1])
            search_query = scol1.text_input("🔍 Ürün Ara / Search Product", "")
            sort_option = scol2.selectbox("⇅ Sırala / Sort by", ["Fiyat (Artan) / Price (Asc)", "Fiyat (Azalan) / Price (Desc)"])
            show_in_stock = scol3.checkbox("📦 Sadece Stoktakiler", value=False)
            
            # [TR] Tüm ürünlerin son fiyatlarını ve stok durumlarını çekmek için genel bir history sorgusu / [EN] Query all histories to get current prices
            products_df, history_df = get_dashboard_data()
            
            if products_df.empty:
                st.warning("[TR] Veritabanında henüz ürün bulunmuyor. Lütfen botun çalışmasını bekleyin. / [EN] No products in the database yet. Please wait for the bot to run.")
                st.stop()
            
            # [TR] Her ürün için en güncel fiyatı bul / [EN] Find the most recent price for each product
            latest_prices = history_df.drop_duplicates(subset=['code'], keep='last')
            
            # [TR] products_df ile latest_prices tablosunu birleştir / [EN] Merge products with their latest prices
            merged_df = pd.merge(products_df, latest_prices[['code', 'price', 'in_stock']], on='code', how='left')
            
            # [TR] Eğer price yoksa base_price kullan / [EN] If no price history, use base_price
            merged_df['current_price'] = merged_df['price'].fillna(merged_df['base_price'])
            merged_df['in_stock'] = merged_df['in_stock'].fillna(0)
            
            # [TR] Arama Filtresi / [EN] Search Filter
            if search_query:
                merged_df = merged_df[merged_df['name'].str.contains(search_query, case=False, na=False)]
                
            # [TR] Stok Filtresi / [EN] Stock Filter
            if show_in_stock:
                merged_df = merged_df[merged_df['in_stock'] == 1]
                
            # [TR] Sıralama / [EN] Sorting
            if sort_option == "Fiyat (Artan) / Price (Asc)":
                merged_df = merged_df.sort_values(by='current_price', ascending=True)
            else:
                merged_df = merged_df.sort_values(by='current_price', ascending=False)
                
            # [TR] KUTU KUTU (GRID) GÖRÜNÜMÜ / [EN] GRID LAYOUT
            st.markdown("### 📦 Ürün Galerisi / Product Gallery")
            
            # 4 sütunlu bir grid yapısı oluştur / Create a 4-column grid structure
            num_columns = 4
            cols = st.columns(num_columns)
            
            for index, row in merged_df.iterrows():
                col_idx = index % num_columns
                with cols[col_idx]:
                    with st.container(border=True):
                        # [TR] Ürün Resmi / [EN] Product Image
                        img_url = row.get('image_url')
                        if img_url and str(img_url).startswith("http"):
                            st.image(img_url, use_column_width=True)
                        else:
                            # Placeholder image
                            st.image("https://cdn.vatanbilgisayar.com/images/frontend/assets/placeHolder.gif", use_column_width=True)
                        
                        # [TR] Ürün Adı (Kısaltılmış) / [EN] Product Name (Truncated)
                        name_display = row['name'] if len(row['name']) < 50 else row['name'][:47] + "..."
                        st.markdown(f"**[{name_display}]({row['url']})**")
                        
                        # [TR] Fiyat ve Stok Gösterimi / [EN] Price and Stock Display
                        stock_color = "green" if row['in_stock'] == 1 else "red"
                        stock_text = "Stokta Var" if row['in_stock'] == 1 else "Stokta Yok"
                        st.markdown(f"<h3 style='color: #FF4B4B; margin-bottom: 0px;'>{row['current_price']:,.2f} TL</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color: {stock_color}; font-size: 14px;'>{stock_text}</p>", unsafe_allow_html=True)
                        
                        # [TR] Grafiği Gör Expander'ı / [EN] View Chart Expander
                        with st.expander("📊 Grafiği Gör / View Chart"):
                            prod_history = history_df[history_df['code'] == row['code']].copy()
                            if prod_history.empty:
                                st.info("Henüz geçmiş yok / No history yet")
                            else:
                                prod_history['Stok Durumu'] = prod_history['in_stock'].apply(lambda x: 'Var' if x == 1 else 'Yok')
                                fig = px.line(prod_history, x='timestamp', y='price', markers=True, 
                                              line_shape='spline',
                                              labels={"timestamp": "Zaman", "price": "Fiyat (TL)"},
                                              hover_data=["Stok Durumu"])
                                fig.add_hline(y=row['base_price'], line_dash="dash", line_color="red")
                                
                                # [TR] X ekseni için gün/hafta/ay seçicilerini ekle (Tümü kaldırıldı) / [EN] Add day/week/month selectors for X axis
                                fig.update_layout(
                                    margin=dict(l=0, r=0, t=30, b=60), 
                                    height=350,
                                    xaxis=dict(
                                        rangeselector=dict(
                                            buttons=list([
                                                dict(count=1, label="1 Gün", step="day", stepmode="backward"),
                                                dict(count=7, label="1 Hafta", step="day", stepmode="backward"),
                                                dict(count=1, label="1 Ay", step="month", stepmode="backward")
                                            ]),
                                            y=-0.3,
                                            x=0.5,
                                            xanchor="center",
                                            yanchor="top"
                                        ),
                                        type="date"
                                    )
                                )
                                # [TR] Mobildeki zoom alet çantasıyla (Modebar) çakışmasını engellemek için modebar'ı gizleyebilir veya optimize edebiliriz.
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{row['code']}")
                                
    except Exception as e:
        st.error(f"[TR] Veri çekilirken bir hata oluştu / [EN] Error fetching data: {e}")
