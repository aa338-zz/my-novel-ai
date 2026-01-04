import streamlit as st
from openai import OpenAI

# --- 1. 网页配置 ---
st.set_page_config(page_title="创世笔 (Genesis Pen)", page_icon="🖊️", layout="wide")

# --- 2. 会员系统 ---
USERS = {
    "vip001": "123456",
    "vip002": "888888",
    "admin": "admin"
}

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.header("🔒 创世笔 - 会员登录")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image("https://cdn-icons-png.flaticon.com/512/2921/2921222.png", width=100)
        with c2:
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            if st.button("🚀 登录"):
                if username in USERS and USERS[username] == password:
                    st.session_state["logged_in"] = True
                    st.toast("欢迎回来，大作家！", icon="🎉")
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        st.stop()

check_login()

# ==========================================
# 主界面
# ==========================================

st.title("🖊️ 创世笔 (Genesis Pen)")
st.caption("VIP 专属通道 | 拒绝 AI 味，只写真故事")

with st.sidebar:
    st.header("⚙️ 创作控制台")
    
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎连接正常")
    else:
        st.error("⚠️ 未配置 Secrets")
        st.stop()

    st.divider()
    
    # --- ✨ 新增：创造力调节滑块 ---
    st.subheader("🌡️ 脑洞温度 (建议 1.0 - 1.3)")
    creativity = st.slider("越往右越像人，越往左越死板", 0.0, 1.5, 1.2, 0.1)
    
    st.subheader("📚 投喂设定")
    novel_genre = st.selectbox("小说类型", ("玄幻修仙", "都市言情", "悬疑推理", "科幻未来", "武侠江湖"))
    
    world_setting = st.text_area(
        "在此粘贴世界观/大纲/人物小传：",
        height=200,
        placeholder="在这里把你的点子倒给它..."
    )
    
    if st.button("🚪 退出登录"):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 聊天记录 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "大纲扔给我，剩下的交给我。"}]

for msg in st.session_state.messages: