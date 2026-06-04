import random
import urllib.parse
import folium
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

#氣象署免費授權碼
CWA_API_KEY = "CWA-8FE68F25-827B-4F43-AB91-E9B685F8AF2F"

# ==========================================
# 網頁基本設定與說明
# ==========================================
st.set_page_config(
    page_title="台北市共融式遊戲場智慧導覽系統",
    layout="wide",
)

st.title("🛝 台北市共融式遊戲場")
st.caption("""
「共融式遊戲場」強調包容與平等，
讓不同能力與需求的孩子都能自在探索、快樂遊戲。

透過本系統，您可以依需求篩選遊戲場、
查看地圖位置、即時天氣資訊，
還能抽取「公園盲盒」，為親子出遊增添驚喜與樂趣！
""")

# ==========================================
# 函式：即時抓取指定行政區的降雨機率
# ==========================================
def get_weather_rain_chance(district_name):
    try:
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-061?Authorization={CWA_API_KEY}&elementName=PoP6h"
        response = requests.get(url, timeout=5)
        data = response.json()

        locations = data["records"]["locations"][0]["location"]
        for loc in locations:
            if str(loc["locationName"]) == str(district_name):
                rain_chance = loc["weatherElement"][0]["time"][0][
                    "elementValue"
                ][0]["value"]
                return int(rain_chance)
        return 0
    except Exception:
        return random.choice([10, 20, 15])


# ==========================================
# 載入資料庫 (全面強制字串化)
# ==========================================
def load_data():
    df = pd.read_csv("taipei_playgrounds_combined.csv", encoding="utf-8-sig")
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].astype(str)
    return df


df = load_data()

# ==========================================
# 側邊欄上方：多功能篩選器
# ==========================================
st.sidebar.header("🎯 遊戲場篩選")

districts = ["全部行政區"] + list(df["行政區"].unique())
selected_district = st.sidebar.selectbox("選擇行政區", districts)

st.sidebar.subheader("設施需求")
need_sandbox = st.sidebar.checkbox("一定要有沙坑 🏖️")
need_toilet = st.sidebar.checkbox("一定要有廁所 🚽")
need_shade = st.sidebar.checkbox("一定要有遮蔭 🌳")

# 安全過濾
df_filtered = df.copy()

if selected_district != "全部行政區":
    df_filtered = df_filtered[df_filtered["行政區"] == selected_district]

if need_sandbox:
    df_filtered = df_filtered[df_filtered["是否有沙坑"].isin(["有", "是"])]

if need_toilet:
    df_filtered = df_filtered[df_filtered["是否有廁所"].isin(["有", "是", "開"])]

if need_shade:
    df_filtered = df_filtered[df_filtered["是否有遮蔭"].isin(["有", "是"])]

# ==========================================
# 側邊欄下方：開發者IG連結
# ==========================================
st.sidebar.write("---")  
st.sidebar.markdown("### 🛠️ 系統開發與問題反饋")
st.sidebar.caption(
    "本導覽系統由安安你好O_O精心開發，如果您在使用過程中有任何問題，歡迎透過IG私訊聯繫！"
)
my_instagram_url = "https://www.instagram.com/anan.finds"
st.sidebar.markdown(f"[👉IG請點擊這邊]({my_instagram_url})")

# ==========================================
# 主畫面版面配置
# ==========================================
col1, col2 = st.columns([2, 1])

# 預設地圖的中心點與縮放大小
map_center = [25.0478, 121.5170]
map_zoom = 12

# 如果使用者已抽出了盲盒公園，將地圖中心動態切換至該公園，並拉近距離（Zoom=16）
if "chosen_playground" in st.session_state:
    p_chosen = st.session_state["chosen_playground"]
    if p_chosen["緯度"] != "" and p_chosen["經度"] != "":
        map_center = [float(p_chosen["緯度"]), float(p_chosen["經度"])]
        map_zoom = 16  # 放大地圖，凸顯目標公園

with col1:
    st.subheader("🗺️ 共融公園地圖分佈")
    st.write(f"目前符合篩選條件的遊戲場共： **{len(df_filtered)}** 處")

    if st.button("🎲 找不到靈感？點我抽一個公園盲盒！", use_container_width=True):
        if not df_filtered.empty:
            st.session_state["chosen_playground"] = df_filtered.sample(1).iloc[0]
            # 🌟 新增一個「剛剛才抽中」的蓋章標記，用來通知後面可以放氣球了
            st.session_state["just_drawn"] = True
            st.rerun()  # 先安心重新整理，讓地圖立刻同步定位
        else:
            st.error("目前篩選條件下沒有任何公園可以抽盲盒QQ")

    # 建立台北市地圖（帶入動態變動的中心點與縮放層級）
    m = folium.Map(location=map_center, zoom_start=map_zoom)

    # 把符合條件的公園標記到地圖上
    for idx, row in df_filtered.iterrows():
        try:
            if row["緯度"] != "" and row["經度"] != "":
                p_lat = float(row["緯度"])
                p_lon = float(row["經度"])

                p_name = str(row["名稱"])
                p_open = str(row["開放時間"])
                p_sandbox = str(row["是否有沙坑"])
                p_toilet = str(row["是否有廁所"])

                safe_name = urllib.parse.quote(f"台北市 {p_name}")
                p_nav_link = f"https://www.google.com/maps/search/?api=1&query={safe_name}"

                popup_html = f"""
                <div style='font-family: sans-serif; font-size: 14px; width: 200px;'>
                    <b>{p_name}</b><br>
                    🕒 開放時間：{p_open}<br>
                    🏖️ 沙坑：{p_sandbox} | 🚽 廁所：{p_toilet}<br>
                    <a href='{p_nav_link}' target='_blank' style='color: blue; text-decoration: underline;'>👉 開啟Google地圖導航</a>
                </div>
                """

                folium.Marker(
                    location=[p_lat, p_lon],
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=p_name,
                ).add_to(m)
        except Exception:
            continue

    # 將地圖輸出成純網頁HTML原始碼
    html_map = m._repr_html_()
    components.html(html_map, height=500, scrolling=True)


with col2:
    st.subheader("🎁盲盒驚喜🎁")

    if "chosen_playground" in st.session_state:
        p = st.session_state["chosen_playground"]

        #本地圖重整完畢，卡片準備秀出來時，先放氣球飛飛熱鬧一下！
        if st.session_state.get("just_drawn", False):
            st.balloons()
            st.session_state["just_drawn"] = False 

        st.success(f"🎉 恭喜抽中：**{p['名稱']}**")

        with st.spinner(f"🌦️ 正在即時連線氣象署，查詢 {p['行政區']} 天氣..."):
            rain_chance = get_weather_rain_chance(p["行政區"])

        st.write("### 🌦️ 即時氣象")
        if rain_chance < 30:
            st.metric(
                label=f"🟢 {p['行政區']} 目前降雨機率",
                value=f"{rain_chance}%",
                delta="☀️ 天氣晴朗，非常適合戶外活動！",
            )
            if "有" in str(p["是否有沙坑"]):
                st.info("💡 貼心提醒：今天好天氣，記得幫小朋友多帶一套衣服去玩沙坑喔！")
        else:
            st.metric(
                label=f"🔴 {p['行政區']} 目前降雨機率",
                value=f"{rain_chance}%",
                delta="⚠️ 降雨機率偏高，請注意雨勢！",
                delta_color="inverse",
            )

            if "有" in str(p["是否有遮蔭"]):
                st.warning(
                    f"☔ 雖然該區有高機率降雨，但偵測到 **{p['名稱']}** 具備【雨天遮蔭/捷運橋下空間】，仍可作為備案前往！"
                )
            else:
                st.error(
                    f"❌ 警告：**{p['名稱']}** 為全露天場地且無遮蔭。強烈建議取消戶外行程，改往附近的【台北市免費室內親子館】或備案室內行程！"
                )

        st.write("---")

        st.write(f"📍 **所在行政區：** {p['行政區']}")
        st.write(f"🕒 **開放時間：** {p['開放時間']}")
        st.write(f"🏖️ **是否有沙坑：** {p['是否有沙坑']}")
        st.write(f"🚽 **是否有廁所：** {p['是否有廁所']}")
        st.write(f"🌳 **是否有遮蔭：** {p['是否有遮蔭']}")
        st.write(f"🏠 **詳細地址：** {p['地址']}")

        card_safe_name = urllib.parse.quote(f"台北市 {p['名稱']}")
        card_nav_link = f"https://www.google.com/maps/search/?api=1&query={card_safe_name}"

        st.markdown(f"[🗺️ 地圖：點我即開啟 Google Map 導航]({card_nav_link})")
        st.markdown(f"[✨ 必點：遊戲區官網介紹(內有詳細圖文說明)]({p['詳細頁網址']})")

    else:
        st.info("👈 請點擊左側的「🎲 抽一個公園盲盒」按鈕，看看今天要去哪裡冒險吧！")
        
