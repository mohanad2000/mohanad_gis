import streamlit as st
import geopandas as gpd
import leafmap.foliumap as leafmap
import tempfile
import os
import zipfile

# إعدادات الصفحة
st.set_page_config(page_title="GIS Joiner Pro", layout="wide")

st.title("🌐 تطبيق الربط المكاني والوصفي (GIS)")
st.markdown("قم برفع ملفاتك الجغرافية وإجراء عمليات الربط بسهولة.")

# --- شريط الجانبي (Sidebar) ---
with st.sidebar:
    st.header("📂 رفع البيانات")
    
    def load_data(label):
        uploaded_file = st.file_uploader(f"اختر ملف {label} (Zip أو GeoJSON)", type=['zip', 'geojson'], key=label)
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.zip'):
                    # معالجة ملف Shapefile المضغوط
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with open(os.path.join(tmpdir, uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        with zipfile.ZipFile(os.path.join(tmpdir, uploaded_file.name), "r") as zip_ref:
                            zip_ref.extractall(tmpdir)
                        # البحث عن ملف .shp داخل المجلد
                        shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                        if not shp_files:
                            st.error("لم يتم العثور على ملف .shp داخل الملف المضغوط.")
                            return None
                        gdf = gpd.read_file(os.path.join(tmpdir, shp_files[0]))
                else:
                    # معالجة GeoJSON
                    gdf = gpd.read_file(uploaded_file)
                
                st.success(f"تم تحميل {label} بنجاح!")
                return gdf
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")
        return None

    left_gdf = load_data("الملف الأساسي (Left)")
    right_gdf = load_data("الملف الثانوي (Right)")

# --- المنطقة الرئيسية ---
col1, col2 = st.columns(2)

# عرض البيانات والخرائط للملف الأول
if left_gdf is not None:
    with col1:
        st.subheader("📍 الملف الأساسي")
        st.write(left_gdf.head(5))
        m1 = leafmap.Map(center=[0, 0], zoom=2)
        m1.add_gdf(left_gdf, layer_name="Left Layer")
        m1.to_streamlit(height=300)

# عرض البيانات والخرائط للملف الثاني
if right_gdf is not None:
    with col2:
        st.subheader("📍 الملف الثانوي")
        st.write(right_gdf.head(5))
        m2 = leafmap.Map(center=[0, 0], zoom=2)
        m2.add_gdf(right_gdf, layer_name="Right Layer")
        m2.to_streamlit(height=300)

# --- عمليات الربط ---
if left_gdf is not None and right_gdf is not None:
    st.divider()
    st.header("⚙️ إعدادات الربط")
    
    join_type = st.radio("اختر نوع الربط:", ["ربط مكاني (Spatial Join)", "ربط وصفي (Attribute Join)"])

    result_gdf = None

    if join_type == "ربط مكاني (Spatial Join)":
        predicate = st.selectbox("العلاقة المكانية:", ["intersects", "contains", "within", "touches", "overlaps"])
        if st.button("تنفيذ الربط المكاني"):
            with st.spinner("جاري المعالجة..."):
                # التأكد من توحيد نظام الإحداثيات (CRS)
                if left_gdf.crs != right_gdf.crs:
                    right_gdf = right_gdf.to_crs(left_gdf.crs)
                result_gdf = gpd.sjoin(left_gdf, right_gdf, how="left", predicate=predicate)

    else:
        left_col = st.selectbox("عمود الملف الأساسي:", left_gdf.columns)
        right_col = st.selectbox("عمود الملف الثانوي:", right_gdf.columns)
        how_attr = st.selectbox("نوع الربط الوصفي:", ["left", "right", "inner", "outer"])
        
        if st.button("تنفيذ الربط الوصفي"):
            with st.spinner("جاري المعالجة..."):
                result_gdf = left_gdf.merge(right_gdf.drop(columns='geometry'), left_on=left_col, right_on=right_col, how=how_attr)

    # --- عرض النتائج وتنزيلها ---
    if result_gdf is not None:
        st.subheader("📊 النتيجة النهائية")
        if result_gdf.empty:
            st.warning("لا توجد نتائج مطابقة لعملية الربط.")
        else:
            st.write(f"عدد الأسطر الناتجة: {len(result_gdf)}")
            st.write(result_gdf.head())
            
            # عرض الخريطة النهائية
            m_res = leafmap.Map()
            m_res.add_gdf(result_gdf, layer_name="Result")
            m_res.to_streamlit(height=400)
            
            # زر التنزيل
            geojson_data = result_gdf.to_json()
            st.download_button(
                label="📥 تحميل النتيجة بصيغة GeoJSON",
                data=geojson_data,
                file_name="result_join.geojson",
                mime="application/json"
            )
