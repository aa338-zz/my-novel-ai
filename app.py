import streamlit as st
from openai import OpenAI

# --- 1. 网页配置 ---
st.set_page_config(page_title="创世笔 (Genesis Pen)", page_icon="🖊️", layout="wide")

# --- 2. 会员系统 (简单版) ---
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
        st.write("请输入您的会员账号启动创作引擎。")
        
        c1, c2 = st.columns([1, 2]) # 稍微排版一下，好看点
        with c1:
            st.image("https://cdn-icons-png.flaticon.com/512/2921/2921222.png", width=100) # 加个装饰图
        with c2:
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            
            if st.button("🚀 登录"):
                if username in USERS and USERS[username] == password:
                    st.session_state["logged_in"] = True
                    st.toast("欢迎回来，大作家！", icon="🎉") # 漂亮的弹窗提示
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        st.stop()

check_login()

# ==========================================
# 登录成功后的主界面
# ==========================================

st.title("🖊️ 创世笔 (Genesis Pen)")
st.caption("VIP 专属通道 | 无限畅想模式")

with st.sidebar:
    st.header("⚙️ 创作控制台")
    
    # 🌟 重点变化：这里不再需要用户填 Key 了！
    # 代码会自动从 Secrets 里读取 Key
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 服务器连接正常 (VIP已激活)")
    else:
        st.error("⚠️ 未检测到 API Key，请联系管理员配置 Secrets")
        st.stop()

    st.divider()
    novel_genre = st.selectbox("📚 小说类型", ("玄幻修仙", "都市言情", "悬疑推理", "科幻未来", "武侠江湖"))
    novel_style = st.selectbox("🎨 文笔风格", ("爽文打脸", "细腻唯美", "暗黑深沉", "幽默吐槽"))
    
    if st.button("🚪 退出登录"):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 聊天记录初始化 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "创世神您好，今天我们要创造什么世界？"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- 核心创作逻辑 ---
if user_input := st.chat_input("输入剧情大纲、开头或人设..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 连接 DeepSeek
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    system_prompt = f"""
    你就是【创世笔】，一款专为顶尖作家打造的AI助手。
    当前任务：创作一本【{novel_genre}】小说。
    写作要求：
    1. 风格必须严格符合：【{novel_style}】。
    2. 拒绝平铺直叙，要有画面感，通过动作、对话推动剧情。
    3. 每次输出控制在500-800字左右，保持节奏紧凑。
    """
    
    # 把最新的剧情 + 系统设定发给 AI
    messages_to_send = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="deepseek-chat", messages=messages_to_send, stream=True
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})