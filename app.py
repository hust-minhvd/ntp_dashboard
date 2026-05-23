import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Industrial Extruder Dashboard",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS TÙY CHỈNH (DARK MODE STYLE) ---
# st.markdown("""
#     <style>
#     .main { background-color: black; }
#     </style>
#     """, unsafe_allow_html=True)

# --- HÀM ĐỌC VÀ XỬ LÝ DỮ LIỆU EXCEL ---
@st.cache_data(ttl=5)
def load_and_clean_data(file_path):
    # Sử dụng read_excel thay vì read_csv
    # Lưu ý: Tuỳ thuộc vào file Excel, bạn có thể cần chỉnh skiprows=3 hoặc 4
    df = pd.read_excel(file_path, skiprows=4)
    
    # Xóa khoảng trắng thừa ở tiêu đề cột (nếu có)
    df.columns = df.columns.astype(str).str.strip()
    
    # Kiểm tra xem 'trenddate' có tồn tại không
    if 'trenddate' not in df.columns:
        st.error("🚨 LỖI: Không tìm thấy cột 'trenddate' trong file Excel!")
        st.warning("Danh sách các cột mà hệ thống đang đọc được:")
        st.write(df.columns.tolist())
        st.stop()
        
    # Chuyển đổi định dạng thời gian
    df['trenddate'] = pd.to_datetime(df['trenddate'])
    df = df.sort_values('trenddate')

    # Ánh xạ tên cột Val_x sang tên kỹ thuật chuyên ngành
    rename_map = {
        'Val_4': 'Speed_E1',
        'Val_5': 'Torque_E1',
        'Val_7': 'Melt_Pressure_1',
        'Val_11': 'Mass_Throughput',
        'Val_13': 'Temp_Zone_1',
        'Val_16': 'Temp_Zone_2',
        'Val_19': 'Temp_Zone_3',
        'Val_22': 'Temp_Zone_4',
        'Val_25': 'Melt_Temperature'
    }
    
    df.rename(columns=rename_map, inplace=True, errors='ignore') # đổi tên cột nếu có trong file, nếu không có thì bỏ qua
    return df

# --- GIAO DIỆN SIDEBAR ---
st.sidebar.image("ntp_logo.png", width=100)
st.sidebar.title("Hệ Thống SCADA")
# Thêm nút bật tắt chế độ thời gian thực ở thanh Sidebar
auto_refresh = st.sidebar.checkbox("🔄 Tự động cập nhật (5s/lần)", value=False)
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("Tải lên file dữ liệu Excel", type=["xlsx", "xls"])

if uploaded_file:
    data = load_and_clean_data(uploaded_file)
    
    # Bộ lọc thời gian
    start_date = data['trenddate'].min()
    end_date = data['trenddate'].max()
    date_range = st.sidebar.date_input("Khoảng thời gian:", [start_date, end_date])
    
    # Lọc dữ liệu theo thời gian
    if len(date_range) == 2:
        mask = (data['trenddate'].dt.date >= date_range[0]) & (data['trenddate'].dt.date <= date_range[1])
        df_filtered = data.loc[mask]
    else:
        df_filtered = data

    # --- MAIN DASHBOARD ---
    st.title("🏗️ Giám Sát Vận Hành Máy Đùn Baumueller")
    st.markdown(f"Dữ liệu từ **{start_date}** đến **{end_date}**")

    # 1. HÀNG CHỈ SỐ KPI (METRICS)
    m1, m2, m3, m4 = st.columns(4)
    
    last_speed = df_filtered['Speed_E1'].iloc[-1]
    last_torque = df_filtered['Torque_E1'].iloc[-1]
    last_pressure = df_filtered['Melt_Pressure_1'].iloc[-1]
    avg_throughput = df_filtered['Mass_Throughput'].mean()

    m1.metric("Tốc độ Trục E1", f"{last_speed:.1f} RPM", delta=f"{last_speed - 120:.1f}")
    m2.metric("Mô-men xoắn E1", f"{last_torque:.1f} %")
    m3.metric("Áp suất Nóng chảy", f"{last_pressure:.1f} Bar", delta_color="inverse")
    m4.metric("Sản lượng TB", f"{avg_throughput:.1f} kg/h")

    st.markdown("---")

    # 2. BIỂU ĐỒ XU HƯỚNG CƠ BẢN (TỐC ĐỘ & MÔ-MEN)
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Xu hướng Tốc độ & Mô-men")
        fig_speed = px.line(df_filtered, x='trenddate', y=['Speed_E1', 'Torque_E1'],
                             color_discrete_sequence=['#deff9a', '#4ade80'],
                             template="plotly_dark")
        fig_speed.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_speed, use_container_width=True)

    with col_right:
        st.subheader("🔥 Nhiệt độ các Vùng (Zones)")
        temp_cols = ['Temp_Zone_1', 'Temp_Zone_2', 'Temp_Zone_3', 'Temp_Zone_4']
        fig_temp = px.area(df_filtered, x='trenddate', y=temp_cols,
                            title="Biểu đồ nhiệt độ thực tế",
                            template="plotly_dark")
        st.plotly_chart(fig_temp, use_container_width=True)

    # 3. BIỂU ĐỒ ÁP SUẤT NÂNG CAO
    st.subheader("📈 Phân tích Áp suất Nóng chảy (Melt Pressure)")
    fig_pressure = go.Figure()
    fig_pressure.add_trace(go.Scatter(x=df_filtered['trenddate'], y=df_filtered['Melt_Pressure_1'],
                                     mode='lines', name='Pressure', line=dict(color='#ff7b72', width=2),
                                     fill='tozeroy'))
    
    # Thêm đường giới hạn an toàn (Threshold)
    fig_pressure.add_hline(y=200, line_dash="dash", line_color="red", annotation_text="Giới hạn an toàn")
    
    fig_pressure.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_pressure, use_container_width=True)

    # 4. CHI TIẾT DỮ LIỆU
    with st.expander("🔍 Xem chi tiết bảng dữ liệu"):
        st.dataframe(df_filtered.style.highlight_max(axis=0), use_container_width=True)
        
        # Nút tải báo cáo
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Tải báo cáo CSV", data=csv, file_name="extruder_report.csv", mime="text/csv")

else:
    # Trạng thái chờ khi chưa có file
    st.info("Vui lòng tải lên file dữ liệu CSV từ máy đùn ở thanh bên trái để bắt đầu.")

# --- CHẾ ĐỘ AUTO-REFRESH (ĐẶT Ở CUỐI FILE) ---
if auto_refresh:
    import time
    time.sleep(5) # Dừng 5 giây
    st.rerun()    # Tự động tải lại toàn bộ giao diện
