# -*- coding: utf-8 -*-
import time
import io
import zipfile
import re
import json
from typing import List, Dict, Optional, Tuple

import streamlit as st
from openai import OpenAI

# =========================================================
# GENESIS · 创世笔 (Streamlit Cloud 版)
# - 修复：蓝图“生成/重写后文字闪一下消失，结果不更新”的同步 bug
# - 加强：登录安全 / client 管理 / 上下文压缩 / 违禁词按段落定位
# =========================================================

# ----------------------------
# 0) 页面配置
# ----------------------------
st.set_page_config(page_title="GENESIS · 创世笔", page_icon="⚡", layout="wide")

# ----------------------------
# 1) CSS（轻量）
# ----------------------------
st.markdown(
    """
<style>
.stApp {background-color: #f7f8fa;}
section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e9ecef;}
div[data-testid="stVerticalBlock"] {gap: 0.5rem;}
.blueprint-box {border: 1px solid #e9ecef; background: #fff; padding: 16px; border-radius: 12px;}
.small-muted {color: #6c757d; font-size: 12px;}
.badword {background: rgba(255,0,0,0.10); padding: 0 3px; border-radius: 4px;}
hr {border-top: 1px solid #e9ecef;}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# 2) 工具函数：secrets / 登录 / client / 流式输出 / 上下文压缩 / 扫描
# =========================================================

def _secrets_get(key: str, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def load_users() -> Dict[str, str]:
    """
    Streamlit Cloud 推荐在 .streamlit/secrets.toml 里配置：
    USERS = { vip="666", admin="admin" }
    """
    users = _secrets_get("USERS", None)
    if isinstance(users, dict) and users:
        return {str(k): str(v) for k, v in users.items()}
    # 兜底（生产不要用）
    return {"vip": "666", "admin": "admin"}

def login_guard():
    if st.session_state.get("logged_in"):
        return

    # 冷却
    if "auth_fail_count" not in st.session_state:
        st.session_state["auth_fail_count"] = 0
    if "auth_lock_until" not in st.session_state:
        st.session_state["auth_lock_until"] = 0.0

    now = time.time()
    lock_until = float(st.session_state["auth_lock_until"])
    if now < lock_until:
        wait = int(lock_until - now)
        st.error(f"登录失败次数过多，已锁定 {wait}s")
        st.stop()

    st.sidebar.markdown("## 🔐 登录")
    u = st.sidebar.text_input("账号", key="login_user")
    p = st.sidebar.text_input("密码", type="password", key="login_pass")
    if st.sidebar.button("登录", use_container_width=True):
        users = load_users()
        ok = (u in users) and (p == users[u])
        if ok:
            st.session_state["logged_in"] = True
            st.session_state["auth_fail_count"] = 0
            st.session_state["auth_lock_until"] = 0.0
            st.sidebar.success("登录成功")
            st.rerun()
        else:
            st.session_state["auth_fail_count"] += 1
            if st.session_state["auth_fail_count"] >= 3:
                st.session_state["auth_lock_until"] = time.time() + 60
                st.session_state["auth_fail_count"] = 0
                st.sidebar.error("错误 3 次，锁定 60 秒")
            else:
                st.sidebar.error("账号或密码错误")
    st.stop()

def get_client() -> OpenAI:
    """
    DeepSeek 用 OpenAI SDK 的常见方式：
    - base_url: https://api.deepseek.com
    - api_key: 你在 DeepSeek 控制台的 key
    """
    api_key = _secrets_get("DEEPSEEK_API_KEY", "") or st.session_state.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        st.sidebar.warning("请在 Streamlit Cloud 的 Secrets 配置 DEEPSEEK_API_KEY")
        st.stop()

    base_url = _secrets_get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return OpenAI(api_key=api_key, base_url=base_url)

def stream_chat_completion(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> str:
    """
    可靠的流式输出：自己迭代流，拼接 delta。
    这样可以稳定拿到最终文本，不会出现“写几行就消失/拿不到结果”的问题。
    """
    placeholder = st.empty()
    acc = ""

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for event in stream:
            delta = ""
            try:
                delta = event.choices[0].delta.content or ""
            except Exception:
                delta = ""
            if delta:
                acc += delta
                placeholder.markdown(acc)
    except Exception as e:
        st.error(f"调用模型失败：{e}")
        return acc.strip()

    return acc.strip()

def compact_history(msgs: List[Dict[str, str]], keep_last: int = 14, max_chars: int = 9000) -> List[Dict[str, str]]:
    """
    简单压缩：保留最后 keep_last 条，并做字符上限裁剪。
    """
    if not msgs:
        return []
    trimmed = msgs[-keep_last:]
    out = []
    total = 0
    for m in reversed(trimmed):
        content = str(m.get("content", ""))
        role = m.get("role", "user")
        total += len(content)
        out.append({"role": role, "content": content})
        if total >= max_chars:
            break
    return list(reversed(out))

def split_paragraphs(text: str) -> List[str]:
    parts = re.split(r"\n\s*\n+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]

def scan_badwords_by_paragraph(text: str, badwords: List[str]) -> Tuple[List[Dict], str]:
    """
    返回：命中列表 + 高亮后的文本（按段落高亮）
    """
    if not text:
        return [], ""
    badwords = [w.strip() for w in badwords if w and w.strip()]
    if not badwords:
        return [], text

    paras = split_paragraphs(text)
    hits = []
    highlighted_paras = []
    for i, para in enumerate(paras, start=1):
        p_hl = para
        found = []
        for w in badwords:
            if w and w in para:
                found.append(w)
                p_hl = p_hl.replace(w, f"<span class='badword'>{w}</span>")
        if found:
            hits.append({"para": i, "words": sorted(set(found)), "preview": para[:120]})
        highlighted_paras.append(p_hl)

    highlighted = "<br><br>".join(highlighted_paras).replace("\n", "<br>")
    return hits, highlighted

def sync_editor(editor_key: str, new_text: str):
    """
    ✅ 关键修复点：
    Streamlit 的 text_area 一旦有 key，之后 value 参数不会再覆盖。
    所以模型生成新内容后，必须同步写入 editor_key，
    否则 UI 会继续显示“旧内容”，并立刻把旧内容写回结果变量，造成你说的 bug。
    """
    st.session_state[editor_key] = new_text

# =========================================================
# 3) Session 初始化
# =========================================================
def init_state():
    defaults = dict(
        first_visit=True,

        bp_idea_prompt="",
        bp_idea_result="",
        bp_char_prompt="",
        bp_char_result="",
        bp_outline_prompt="",
        bp_outline_result="",

        global_genre="都市",
        global_tone="爽文 / 节奏快",
        global_pov="第三人称",
        global_length="每章 1800~2500 字",
        global_taboo="",
        global_model="deepseek-chat",
        global_temperature=0.7,

        chapter_titles=[],
        chapters={},
        chat_messages=[],
        current_chapter_title="第1章",
        current_chapter_draft="",
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
login_guard()
client = get_client()

# =========================================================
# 4) 首次引导
# =========================================================
if st.session_state.get("first_visit"):
    st.title("⚡ GENESIS · 创世笔")
    st.caption("蓝图 → 正文 → 工具 → 导出，一站式写小说工作台（已修复蓝图重写闪退/不更新问题）")
    st.markdown(
        """
- **创世蓝图**：脑洞、人设、剧情细纲，支持“修改意见→重写”
- **沉浸写作**：左大纲右正文，支持续写/改写
- **工具箱**：违禁词扫描、润色、分支建议
- **发书控制台**：打包导出 TXT / ZIP
        """
    )
    if st.button("🚀 开始创作", type="primary"):
        st.session_state["first_visit"] = False
        st.rerun()
    st.stop()

# =========================================================
# 5) Sidebar：全局设置
# =========================================================
st.sidebar.markdown("## 🎚️ 全局设置")
st.sidebar.selectbox("题材/风格", ["都市", "玄幻", "科幻", "言情", "悬疑", "历史", "同人", "轻小说"], key="global_genre")
st.sidebar.selectbox("叙事视角", ["第一人称", "第三人称", "多视角"], key="global_pov")
st.sidebar.text_input("基调（如：爽/虐/甜/黑色幽默）", key="global_tone")
st.sidebar.selectbox("章字数目标", ["每章 1200~1800 字", "每章 1800~2500 字", "每章 2500~3500 字"], key="global_length")
st.sidebar.text_area("违禁词（用逗号/空格分隔）", key="global_taboo", height=90)
st.sidebar.selectbox("模型", ["deepseek-chat", "deepseek-reasoner"], key="global_model")
st.sidebar.slider("温度 temperature", 0.0, 1.2, float(st.session_state["global_temperature"]), 0.05, key="global_temperature")
st.sidebar.markdown("---")
if st.sidebar.button("🧹 清空当前章节对话", use_container_width=True):
    st.session_state["chat_messages"] = []
    st.sidebar.success("已清空")

# =========================================================
# 6) Tabs
# =========================================================
tab_blueprint, tab_write, tab_tools, tab_publish = st.tabs(
    ["🗺️ 创世蓝图 (策划)", "✍️ 沉浸写作 (正文)", "🔮 灵感工具箱", "💾 发书控制台"]
)

# =========================================================
# TAB 1: 创世蓝图
# =========================================================
planner_sys = (
    "你是一名资深网络小说策划/编辑。输出要具体、可写、可落地，避免空话。"
    "内容要符合用户题材、基调、视角。"
)

def blueprint_call(result_key: str, editor_key: str, user_prompt: str, extra_user: Optional[str] = None):
    messages = [{"role": "system", "content": planner_sys}]
    if extra_user:
        messages.append({"role": "user", "content": extra_user})
    messages.append({"role": "user", "content": user_prompt})

    text = stream_chat_completion(
        client=client,
        model=st.session_state["global_model"],
        messages=messages,
        temperature=float(st.session_state["global_temperature"]),
    )
    st.session_state[result_key] = text
    sync_editor(editor_key, text)  # ✅ 修复同步
    st.toast("✅ 已更新到编辑框")

with tab_blueprint:
    st.subheader("🗺️ 创世蓝图")
    st.caption("提示：生成/重写后，内容会自动同步到下面的编辑框（已修复你说的“闪一下又变回旧内容”）")

    # 1) 脑洞
    st.markdown("#### 1️⃣ 核心脑洞")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)

    idea_in = st.text_area("✍️ 点子/关键词（越具体越好）",
                           value=st.session_state.get("bp_idea_prompt", ""),
                           height=110,
                           key="idea_in_safe")
    c1, c2 = st.columns([1, 4])
    if c1.button("💡 生成脑洞", key="gen_idea"):
        st.session_state["bp_idea_prompt"] = idea_in
        prompt = (
            f"题材：{st.session_state['global_genre']}；基调：{st.session_state['global_tone']}；视角：{st.session_state['global_pov']}。\n"
            f"基于点子：{idea_in}\n"
            f"请输出：1) 一句话核心梗；2) 主冲突；3) 爽点/看点；4) 结局走向（可选）。总字数 200~260 字。"
        )
        blueprint_call("bp_idea_result", "idea_res_edit", prompt)

    if st.session_state.get("bp_idea_result"):
        st.markdown("---")
        st.text_area("✅ AI 生成结果（可直接编辑最终版）",
                     key="idea_res_edit",
                     height=160)
        st.session_state["bp_idea_result"] = st.session_state["idea_res_edit"]

        cr1, cr2 = st.columns([3, 1])
        fb = cr1.text_input("修改意见", placeholder="如：更炸裂、更甜、更悬疑…", key="fb_idea")
        if cr2.button("🔄 让他重写", key="rw_idea"):
            prompt = (
                f"当前脑洞：{st.session_state['bp_idea_result']}\n"
                f"修改意见：{fb}\n"
                f"请重写，保持 200~260 字，信息密度更高。"
            )
            blueprint_call("bp_idea_result", "idea_res_edit", prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    # 2) 人设
    st.markdown("#### 2️⃣ 角色档案")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)

    char_in = st.text_area("✍️ 角色要求（选填：职业、性格、禁忌、CP…）",
                           value=st.session_state.get("bp_char_prompt", ""),
                           height=110,
                           key="char_in_safe")
    cc1, cc2 = st.columns([1, 4])
    if cc1.button("👥 生成人设", key="gen_char"):
        if not st.session_state.get("bp_idea_result"):
            st.error("请先生成并确认【核心脑洞】")
        else:
            st.session_state["bp_char_prompt"] = char_in
            prompt = (
                f"题材：{st.session_state['global_genre']}；基调：{st.session_state['global_tone']}；视角：{st.session_state['global_pov']}。\n"
                f"核心脑洞：{st.session_state['bp_idea_result']}\n"
                f"额外要求：{char_in}\n"
                "请输出：主角（姓名/身份/目标/缺陷/能力/人设反差/成长线）+ 关键配角 2~3 个（各 4~6 行）。"
            )
            blueprint_call("bp_char_result", "char_res_edit", prompt)

    if st.session_state.get("bp_char_result"):
        st.markdown("---")
        st.text_area("✅ 人设结果（可编辑）", key="char_res_edit", height=220)
        st.session_state["bp_char_result"] = st.session_state["char_res_edit"]

        crr1, crr2 = st.columns([3, 1])
        fb2 = crr1.text_input("修改意见", placeholder="如：男主更腹黑/女主更独立…", key="fb_char")
        if crr2.button("🔄 重写人设", key="rw_char"):
            prompt = (
                f"当前人设：{st.session_state['bp_char_result']}\n"
                f"修改意见：{fb2}\n"
                "请重写，保留可写性和戏剧冲突，条理清晰。"
            )
            blueprint_call("bp_char_result", "char_res_edit", prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    # 3) 细纲
    st.markdown("#### 3️⃣ 剧情细纲")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)

    out_in = st.text_area("✍️ 细纲要求（选填：章节数/节奏/反转点…）",
                          value=st.session_state.get("bp_outline_prompt", ""),
                          height=110,
                          key="out_in_safe")
    oc1, oc2 = st.columns([1, 4])
    if oc1.button("🧱 生成细纲", key="gen_outline"):
        if not st.session_state.get("bp_idea_result"):
            st.error("请先生成并确认【核心脑洞】")
        else:
            st.session_state["bp_outline_prompt"] = out_in
            prompt = (
                f"题材：{st.session_state['global_genre']}；基调：{st.session_state['global_tone']}；视角：{st.session_state['global_pov']}。\n"
                f"核心脑洞：{st.session_state['bp_idea_result']}\n"
                f"人设：{st.session_state.get('bp_char_result','（无）')}\n"
                f"额外要求：{out_in}\n"
                "请输出：10~16 个章节要点（按序号），每条包含：该章目标/冲突/爽点/悬念收尾。"
            )
            blueprint_call("bp_outline_result", "out_res_edit", prompt)

    if st.session_state.get("bp_outline_result"):
        st.markdown("---")
        st.text_area("✅ 细纲结果（可编辑）", key="out_res_edit", height=260)
        st.session_state["bp_outline_result"] = st.session_state["out_res_edit"]

        orr1, orr2 = st.columns([3, 1])
        fb3 = orr1.text_input("修改意见", placeholder="如：前3章更快进入主线，增加一次反转…", key="fb_out")
        if orr2.button("🔄 重写细纲", key="rw_outline"):
            prompt = (
                f"当前细纲：{st.session_state['bp_outline_result']}\n"
                f"修改意见：{fb3}\n"
                "请重写成 10~16 条，节奏更强，悬念更清晰。"
            )
            blueprint_call("bp_outline_result", "out_res_edit", prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### 🎚️ 导演控制台")
    st.info("写正文时会自动引用：题材/基调/视角/细纲/人设（如果你编辑了蓝图，这里就是最终版）")

# =========================================================
# TAB 2: 沉浸写作
# =========================================================
with tab_write:
    st.subheader("✍️ 沉浸写作")
    left, right = st.columns([1, 1.25], gap="large")

    with left:
        st.markdown("### 📌 你的蓝图（对照用）")
        st.markdown("**核心脑洞**")
        st.write(st.session_state.get("bp_idea_result") or "（尚未生成）")
        st.markdown("**角色档案**")
        st.write(st.session_state.get("bp_char_result") or "（尚未生成）")
        st.markdown("**剧情细纲**")
        st.write(st.session_state.get("bp_outline_result") or "（尚未生成）")

        st.markdown("---")
        st.markdown("### 📚 章节管理")
        title = st.text_input("当前章节标题", value=st.session_state.get("current_chapter_title", "第1章"), key="chap_title_in")
        st.session_state["current_chapter_title"] = title

        if st.button("➕ 新建章节", use_container_width=True):
            t = st.session_state["current_chapter_title"].strip() or f"第{len(st.session_state['chapters'])+1}章"
            if t not in st.session_state["chapters"]:
                st.session_state["chapters"][t] = ""
                st.session_state["chapter_titles"] = list(st.session_state["chapters"].keys())
            st.toast("已创建/切换章节")
            st.rerun()

        if st.session_state["chapters"]:
            pick = st.selectbox("切换到章节", options=list(st.session_state["chapters"].keys()),
                                index=max(0, list(st.session_state["chapters"].keys()).index(st.session_state["current_chapter_title"]) if st.session_state["current_chapter_title"] in st.session_state["chapters"] else 0))
            st.session_state["current_chapter_title"] = pick
        else:
            st.caption("还没有章节，先点【新建章节】")

    with right:
        st.markdown("### 📝 正文编辑区")
        cur_title = st.session_state["current_chapter_title"]
        if cur_title not in st.session_state["chapters"]:
            st.session_state["chapters"][cur_title] = ""
        draft_key = "chapter_editor"
        if draft_key not in st.session_state:
            st.session_state[draft_key] = st.session_state["chapters"][cur_title]
        if st.session_state.get("last_chapter_title") != cur_title:
            st.session_state["last_chapter_title"] = cur_title
            st.session_state[draft_key] = st.session_state["chapters"][cur_title]

        st.text_area("正文（你也可以先手写，然后让 AI 续写/改写）", key=draft_key, height=420)
        st.session_state["chapters"][cur_title] = st.session_state[draft_key]

        st.markdown("---")
        st.markdown("### 🤖 AI 写作助手")
        user_req = st.text_input("本次指令（如：继续写到一个悬念点；加一场冲突；把节奏加快…）", key="write_req")

        b1, b2, b3 = st.columns([1, 1, 1])
        if b1.button("🚀 续写", use_container_width=True):
            sys_p = (
                f"你是一名网文写作助手。题材：{st.session_state['global_genre']}；基调：{st.session_state['global_tone']}；视角：{st.session_state['global_pov']}；字数：{st.session_state['global_length']}。"
                "遵循蓝图设定，避免跳戏，输出正文而不是大纲。"
            )
            blueprint = f"脑洞：{st.session_state.get('bp_idea_result','')}\n人设：{st.session_state.get('bp_char_result','')}\n细纲：{st.session_state.get('bp_outline_result','')}"
            current = st.session_state["chapters"][cur_title]

            msgs = st.session_state["chat_messages"]
            msgs.append({"role": "user", "content": f"【蓝图】\n{blueprint}\n\n【当前章节标题】{cur_title}\n【已写内容】\n{current[-3500:]}\n\n【写作要求】{user_req or '请自然续写，推进剧情并以悬念收尾。'}"})
            send = [{"role": "system", "content": sys_p}] + compact_history(msgs)

            text = stream_chat_completion(client, st.session_state["global_model"], send, temperature=float(st.session_state["global_temperature"]))
            if text:
                st.session_state["chapters"][cur_title] = (current.rstrip() + "\n\n" + text).strip()
                st.session_state[draft_key] = st.session_state["chapters"][cur_title]
            st.session_state["chat_messages"] = msgs
            st.toast("✅ 已续写并追加到正文")
            st.rerun()

        if b2.button("🪄 改写润色", use_container_width=True):
            sys_p = "你是中文文学润色编辑。保持剧情不变，提升语言、节奏和画面感。"
            current = st.session_state["chapters"][cur_title]
            if not current.strip():
                st.warning("正文为空，先写一点再润色")
            else:
                send = [{"role": "system", "content": sys_p},
                        {"role": "user", "content": f"请润色以下正文，保留段落结构：\n{current}"}]
                text = stream_chat_completion(client, st.session_state["global_model"], send, temperature=0.6)
                if text:
                    st.session_state["chapters"][cur_title] = text
                    st.session_state[draft_key] = text
                st.toast("✅ 已润色并替换正文")
                st.rerun()

        if b3.button("🧯 检查违禁词", use_container_width=True):
            bad = re.split(r"[,\s]+", st.session_state.get("global_taboo", "").strip())
            hits, highlighted = scan_badwords_by_paragraph(st.session_state["chapters"][cur_title], bad)
            if not hits:
                st.success("未发现命中")
            else:
                st.warning(f"命中 {len(hits)} 个段落")
                for h in hits:
                    st.write(f"段落 {h['para']}：{', '.join(h['words'])}｜{h['preview']}…")
                st.markdown(highlighted, unsafe_allow_html=True)

# =========================================================
# TAB 3: 工具箱
# =========================================================
with tab_tools:
    st.subheader("🔮 灵感工具箱")

    tool = st.radio("选择工具", ["违禁词扫描（全文）", "分支建议", "章节标题生成"], horizontal=True)

    if tool == "违禁词扫描（全文）":
        txt = st.text_area("粘贴全文或某一章内容", height=260)
        bad = st.text_input("违禁词（逗号/空格分隔）", value=st.session_state.get("global_taboo", ""))
        if st.button("开始扫描"):
            hits, highlighted = scan_badwords_by_paragraph(txt, re.split(r"[,\s]+", bad.strip()))
            if not hits:
                st.success("未发现命中")
            else:
                st.warning(f"命中 {len(hits)} 个段落")
                st.markdown(highlighted, unsafe_allow_html=True)
                st.json(hits)

    elif tool == "分支建议":
        base = st.text_area("当前剧情片段（粘贴一段）", height=220)
        if st.button("生成 3 个分支"):
            if not base.strip():
                st.warning("先粘贴内容")
            else:
                send = [{"role": "system", "content": "你是网文剧情策划。给出可写、冲突强的分支。"},
                        {"role": "user", "content": f"基于以下片段，给出 3 个不同走向分支，每个 5~8 行：\n{base}"}]
                text = stream_chat_completion(client, st.session_state["global_model"], send, temperature=0.8)
                st.write(text)

    elif tool == "章节标题生成":
        theme = st.text_input("本章主题/事件关键词", placeholder="如：初遇、误会、反转、Boss登场…")
        if st.button("生成 10 个标题"):
            send = [{"role": "system", "content": "你是网络小说编辑。标题要抓人，符合题材。"},
                    {"role": "user", "content": f"题材：{st.session_state['global_genre']}。给出 10 个章节标题，围绕主题：{theme}。每行一个。"}]
            text = stream_chat_completion(client, st.session_state["global_model"], send, temperature=0.9)
            st.write(text)

# =========================================================
# TAB 4: 导出
# =========================================================
with tab_publish:
    st.subheader("💾 发书控制台")
    st.caption("把你写的章节导出成 TXT / ZIP（本地下载后就能发给别人/投稿）")

    if not st.session_state["chapters"]:
        st.info("你还没有任何章节内容，去【沉浸写作】先写一章吧。")
    else:
        st.markdown("### 📚 章节列表")
        for t, content in st.session_state["chapters"].items():
            st.markdown(f"**{t}**")
            st.caption(content[:120].replace("\n", " ") + ("..." if len(content) > 120 else ""))

        st.markdown("---")
        book_title = st.text_input("书名（用于导出文件名）", value="我的小说")

        merged = []
        for t, content in st.session_state["chapters"].items():
            merged.append(t)
            merged.append(content.strip())
            merged.append("\n")
        merged_txt = "\n".join(merged).strip() + "\n"

        st.download_button(
            "⬇️ 下载：整本 TXT",
            data=merged_txt.encode("utf-8"),
            file_name=f"{book_title}.txt",
            mime="text/plain",
            use_container_width=True,
        )

        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
            for t, content in st.session_state["chapters"].items():
                safe = re.sub(r"[^\w\u4e00-\u9fa5\-]+", "_", t)
                zf.writestr(f"{safe}.txt", content.strip() + "\n")
            zf.writestr("_merged.txt", merged_txt)

            blueprint = {
                "idea": st.session_state.get("bp_idea_result", ""),
                "characters": st.session_state.get("bp_char_result", ""),
                "outline": st.session_state.get("bp_outline_result", ""),
                "settings": {
                    "genre": st.session_state.get("global_genre"),
                    "tone": st.session_state.get("global_tone"),
                    "pov": st.session_state.get("global_pov"),
                    "length": st.session_state.get("global_length"),
                },
            }
            zf.writestr("_blueprint.json", json.dumps(blueprint, ensure_ascii=False, indent=2))

        mem.seek(0)
        st.download_button(
            "⬇️ 下载：ZIP（每章一个文件 + 蓝图）",
            data=mem,
            file_name=f"{book_title}.zip",
            mime="application/zip",
            use_container_width=True,
        )
