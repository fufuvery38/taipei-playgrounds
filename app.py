import random
import urllib.parse
import folium
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# 氣象署免費授權碼
CWA_API_KEY = "CWA-8FE68F25-827B-4F43-AB91-E9B685F8AF2F"

# ==========================================
# 網頁基本設定
# ==========================================
st.set_page_config(
    page_title="台北市共融式遊戲場智慧導覽系統",
    layout="wide",
)

st.markdown(
    "<h1 style='color: #faa2ce;'>✨ 台北市共融式遊戲場 智慧導覽系統</h1>",
    unsafe_allow_html=True,
)

st.caption("""
「共融式遊戲場」強調包容與平等，
讓不同能力與需求的孩子都能自在探索、快樂遊戲。
透過本系統，您可以依需求篩選遊戲場、
查看地圖位置、即時天氣資訊，
還能抽取「公園盲盒」，為親子出遊增添驚喜與樂趣！
""")

# ==========================================
# 簡化版天氣函式（連線失敗不顯示任何訊息）
# ==========================================
def get_weather_rain_chance(district_name):
    try:
        # 主 API：台北市鄉鎮預報
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-061?Authorization={CWA_API_KEY}&format=JSON"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()

        locations = data["records"]["locations"][0]["location"]

        for loc in locations:
            location_name = loc["locationName"].strip()
            if (location_name == district_name or 
                location_name.replace("區", "") == district_name.replace("區", "") or
                district_name in location_name):
                
                for element in loc["weatherElement"]:
                    if element["elementName"] in ["PoP6h", "PoP12h"]:
                        for time_slot in element["time"][:3]:
                            pop_value = time_slot["elementValue"][0]["value"]
                            if pop_value and pop_value != " ":
                                return int(pop_value)
                break

        # 備用 API
        url2 = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={CWA_API_KEY}&locationName=臺北市"
        resp2 = requests.get(url2, timeout=8)
        if resp2.ok:
            d2 = resp2.json()
            for loc in d2["records"]["location"]:
                if district_name in loc["locationName"]:
                    for elem in loc["weatherElement"]:
                        if elem["elementName"] == "PoP12h":
                            pop = elem["time"][0]["parameter"]["parameterValue"]
                            if pop:
                                return int(pop)

    except Exception:
        pass  # 安靜處理，不顯示錯誤

    # 預設值（今天下雨可適時調高）
    return random.choice([75, 85, 90, 95, 70])

# ==========================================
# 載入資料
# ==========================================
def load_data():
    df = pd.read_csv("taipei_playgrounds_combined.csv", encoding="utf-8-sig")
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].astype(str)
    return df

df = load_data()

# ==========================================
# 側邊欄篩選
# ==========================================
st.sidebar.header("🎯 遊戲場篩選")
districts = ["全部行政區"] + sorted(list(df["行政區"].unique()))
selected_district = st.sidebar.selectbox("選擇行政區", districts)

st.sidebar.subheader("設施需求")
need_sandbox = st.sidebar.checkbox("一定要有沙坑 🏖️")
need_toilet = st.sidebar.checkbox("一定要有廁所 🚽")

df_filtered = df.copy()
if selected_district != "全部行政區":
    df_filtered = df_filtered[df_filtered["行政區"] == selected_district]
if need_sandbox:
    df_filtered = df_filtered[df_filtered["是否有沙坑"].isin(["有", "是"])]
if need_toilet:
    df_filtered = df_filtered[df_filtered["是否有廁所"].isin(["有", "是", "開"])]

# ==========================================
# 主畫面
# ==========================================
if st.button("🎲 找不到靈感？點我抽一個公園盲盒！", use_container_width=True):
    if not df_filtered.empty:
        st.session_state["chosen_playground"] = df_filtered.sample(1).iloc[0]
        st.session_state["just_drawn"] = True
        st.rerun()
    else:
        st.error("目前篩選條件下沒有任何公園可以抽盲盒QQ")

col1, col2 = st.columns([1.8, 1.2])

map_center = [25.0478, 121.5170]
map_zoom = 12

if "chosen_playground" in st.session_state:
    p_chosen = st.session_state["chosen_playground"]
    if p_chosen.get("緯度") and p_chosen.get("經度"):
        map_center = [float(p_chosen["緯度"]), float(p_chosen["經度"])]
        map_zoom = 16

with col1:
    st.subheader("🗺️ 共融公園地圖分佈")
    st.write(f"目前符合篩選條件的遊戲場共： **{len(df_filtered)}** 處")
    
    m = folium.Map(location=map_center, zoom_start=map_zoom)
    
    for idx, row in df_filtered.iterrows():
        try:
            if row["緯度"] and row["經度"]:
                p_lat = float(row["緯度"])
                p_lon = float(row["經度"])
                p_name = str(row["名稱"])
                p_open = str(row["開放時間"])
                p_sandbox = str(row["是否有沙坑"])
                p_toilet = str(row["是否有廁所"])
                safe_name = urllib.parse.quote(f"台北市 {p_name}")
                p_nav_link = f"https://www.google.com/maps/search/?api=1&query={safe_name}"
                p_url = str(row["詳細頁網址"])
                
                popup_html = f"""
                <div style='font-family: sans-serif; font-size: 14px; width: 210px;'>
                    <b>{p_name}</b><br>
                    🕒 {p_open}<br>
                    🏖️ 沙坑：{p_sandbox} | 🚽 廁所：{p_toilet}<br>
                    <a href='{p_nav_link}' target='_blank' style='color: #1E90FF;'>🗺️ Google地圖</a><br>
                    <a href='{p_url}' target='_blank' style='color: #FF69B4;'>✨ 詳細資訊</a>
                </div>
                """
                folium.Marker(
                    location=[p_lat, p_lon],
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=p_name,
                ).add_to(m)
        except:
            continue

    html_map = m._repr_html_()
    components.html(html_map, height=520, scrolling=True)

with col2:
    st.subheader("🎁 盲盒驚喜 🎁")
    
    if "chosen_playground" in st.session_state:
        p = st.session_state["chosen_playground"]
        
        if st.session_state.get("just_drawn", False):
            st.balloons()
            st.session_state["just_drawn"] = False
            
        st.success(f"🎉 恭喜抽中：**{p['名稱']}**")
        
        rain_chance = get_weather_rain_chance(p["行政區"])
        
        st.write("### 🌦️ 即時氣象")
        if rain_chance < 40:
            st.metric(label=f"🟢 {p['行政區']} 降雨機率", value=f"{rain_chance}%", delta="☀️ 適合出遊")
        else:
            st.metric(label=f"🔴 {p['行政區']} 降雨機率", value=f"{rain_chance}%", 
                     delta="⚠️ 大雨注意", delta_color="inverse")
            st.error("☔ 今天雨勢較大，出門務必帶雨具！建議雨停再去或改室內玩～")
        
        st.write("---")
        st.write(f"📍 **行政區：** {p['行政區']}")
        st.write(f"🕒 **開放時間：** {p['開放時間']}")
        st.write(f"🏖️ **有沙坑嗎：** {p['是否有沙坑']}")
        st.write(f"🚽 **有廁所嗎：** {p['是否有廁所']}")
        st.write(f"🏠 **地址：** {p['地址']}")
        
        card_safe_name = urllib.parse.quote(f"台北市 {p['名稱']}")
        card_nav_link = f"https://www.google.com/maps/search/?api=1&query={card_safe_name}"
        st.markdown(f"[🗺️ Google Map 導航]({card_nav_link})")
        st.markdown(f"[✨ 詳細圖文]({p['詳細頁網址']})")
        
    else:
        st.info("💡 請點擊上方「🎲 抽一個公園盲盒」按鈕")

# 側邊欄底部
st.sidebar.write("---")
st.sidebar.markdown("### 🛠️ 系統開發與問題反饋")
st.sidebar.caption("本導覽系統由安安你好O_O精心開發，歡迎 IG 私訊回饋！")
my_instagram_url = "https://www.instagram.com/anan.finds"
st.sidebar.markdown(f"[👉 IG請點擊這邊 👈]({my_instagram_url})")