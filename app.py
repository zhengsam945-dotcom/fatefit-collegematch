import streamlit as st
from openai import OpenAI
from datetime import date, datetime

# ---------------------------
# Small helpers (local, no DB)
# ---------------------------
def parse_birthdate(s: str):
    """Parse YYYY-MM-DD to date or return None."""
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None

def sun_sign(d: date) -> str:
    """Return Western sun sign name from date."""
    m, day = d.month, d.day
    # Boundaries (approx standard)
    if (m == 3 and day >= 21) or (m == 4 and day <= 19): return "Aries"
    if (m == 4 and day >= 20) or (m == 5 and day <= 20): return "Taurus"
    if (m == 5 and day >= 21) or (m == 6 and day <= 20): return "Gemini"
    if (m == 6 and day >= 21) or (m == 7 and day <= 22): return "Cancer"
    if (m == 7 and day >= 23) or (m == 8 and day <= 22): return "Leo"
    if (m == 8 and day >= 23) or (m == 9 and day <= 22): return "Virgo"
    if (m == 9 and day >= 23) or (m == 10 and day <= 22): return "Libra"
    if (m == 10 and day >= 23) or (m == 11 and day <= 21): return "Scorpio"
    if (m == 11 and day >= 22) or (m == 12 and day <= 21): return "Sagittarius"
    if (m == 12 and day >= 22) or (m == 1 and day <= 19): return "Capricorn"
    if (m == 1 and day >= 20) or (m == 2 and day <= 18): return "Aquarius"
    return "Pisces"

def astro_element(sign: str) -> str:
    fire = {"Aries","Leo","Sagittarius"}
    earth = {"Taurus","Virgo","Capricorn"}
    air = {"Gemini","Libra","Aquarius"}
    water = {"Cancer","Scorpio","Pisces"}
    if sign in fire: return "Fire"
    if sign in earth: return "Earth"
    if sign in air: return "Air"
    return "Water"

def playful_wuxing(d: date) -> str:
    """
    娱乐版五行：不用精确八字排盘，做一个稳定可复现的映射。
    用 (month + day) % 5 映射到 金木水火土。
    """
    elements = ["Metal(金)", "Wood(木)", "Water(水)", "Fire(火)", "Earth(土)"]
    idx = (d.month + d.day) % 5
    return elements[idx]

def build_prompt(user_payload: dict) -> str:
    # Fixed output format to feel like a product report
    return f"""
You are an “AI Metaphysical + Rational College Advisor.”
Your job: generate a FUN but responsible college-selection report.
Important rules:
- Do NOT predict admissions outcomes or guarantee acceptance.
- Do NOT claim supernatural certainty. Treat metaphysics as reflective entertainment.
- Provide actionable next steps and questions the user can use for real research.
- If the user provides no school list, recommend school *types* and environments (not specific schools).
- If a school list is provided, rank them and explain each.

Write in Chinese, with occasional short English keywords where useful.

USER INPUT (JSON):
{user_payload}

OUTPUT MUST FOLLOW THIS EXACT MARKDOWN STRUCTURE:

## 0) 免责声明
- 1–2 句：这是自我探索/娱乐，不是录取预测；鼓励用官网与数据验证。

## 1) Summary
- 3 bullet points: 画像关键词、最适合的环境、最不适合的坑

## 2) 玄学画像
- 五行倾向：用用户给的“Wuxing_hint”
- 星座：Sun_sign + Astro_element
- 解释：2–4 bullets（优势/压力点/需要的环境）

## 3) Preference Map
Provide a table with these 8 dimensions and 0–10 scores + one-line rationale each:
- School size (small vs large)
- City vs college town
- Competition intensity
- Support/mentorship need
- Interdisciplinary freedom
- Pre-professional/career focus
- Research intensity
- Social energy (quiet vs active)

## 4) Recommendations
- Give 4–6 recommendations. Each item must have:
  - “玄学理由” (1 sentence)
  - “理性理由” (1 sentence)
  - “可执行动作” (1 sentence)

## 5) 如果用户提供了候选学校列表：必须排序并逐一点评（强制）
If School_list is non-empty:
- First output a ranked list top to bottom with a score (0–100).
- Then you MUST review EVERY school in School_list (no skipping).
- Output exactly N mini-reviews where N = len(School_list).
- Each mini-review MUST follow this exact template:

### {rank}. {school_name} — {score}/100
- 玄学理由：...
- 理性理由：...

- Hard rule: Do NOT write “例如/for example”. Do NOT only review one school.
- Hard rule: The school_name must match the user’s list (copy exactly).
If School_list is empty:
- Provide 6 example “school archetypes” (not specific schools).

If School_list is empty:
- Provide 6 example “school archetypes” (not specific schools), e.g., “Urban research powerhouse”, “Small supportive LAC”, etc.

## 6) Next Steps
- Provide a checklist of 6–10 steps, including:
  - what to verify on official sites
  - what to ask admissions/current students
  - what to look for in course catalogs / research centers
""".strip()

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="FateFit AI选校顾问", layout="wide")
st.title("🔮FateFit AI选校顾问")
st.caption("不用数据库：你输入信息 → 一键生成“好玩但相对靠谱”的选校建议报告（玄学 + 理性双通道）。")

with st.sidebar:
    st.header("🔌 Provider / API Key")

    provider = st.selectbox("选择后端", ["OpenRouter", "Groq", "OpenAI"], index=0)

    if provider == "OpenRouter":
        api_key = st.text_input("OpenRouter API Key", type="password")
        base_url = "https://openrouter.ai/api/v1"
        # 选一个便宜/常用的模型（你也可以之后换）
        model = st.text_input("Model", value="openai/gpt-4.1-mini")
        # OpenRouter 推荐带一些 headers（可选）
        extra_headers = {
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "FateFit College (Streamlit)"
        }

    elif provider == "Groq":
        api_key = st.text_input("Groq API Key", type="password")
        base_url = "https://api.groq.com/openai/v1"
        model = st.text_input("Model", value="llama-3.1-70b-versatile")
        extra_headers = {}

    else:  # OpenAI
        api_key = st.text_input("OpenAI API Key", type="password")
        base_url = "https://api.openai.com/v1"
        model = st.selectbox("Model", ["gpt-4.1-mini", "gpt-4.1"], index=0)
        extra_headers = {}

    st.divider()
    st.header("🎯 输出偏好")
    humor = st.slider("玄学趣味浓度", 0, 10, 6)
    rigor = st.slider("理性严谨度", 0, 10, 7)
    st.caption("建议：趣味 6–8，严谨 6–8，输出最像“既好玩又靠谱”。")

colA, colB = st.columns([1, 1])

with colA:
    st.subheader("🧾 基本信息")
    birth = st.text_input("生日（YYYY-MM-DD）", placeholder="例如：2006-04-15")
    birth_time = st.text_input("出生时间（可选）", placeholder="例如：08:30 / 不确定")
    birth_place = st.text_input("出生地（可选）", placeholder="例如：Hangzhou, China / Los Angeles, CA")

    st.subheader("🧠 你的现实偏好（可选，但强烈建议填）")
    w_academic = st.slider("更看重学术资源", 0, 10, 7)
    w_career = st.slider("更看重职业/实习机会", 0, 10, 7)
    w_life = st.slider("更看重生活体验（城市/气候/节奏）", 0, 10, 6)
    w_support = st.slider("更看重支持系统（导师/社群/国际生友好）", 0, 10, 8)

with colB:
    st.subheader("🏫 选校任务")
    goal = st.selectbox("你要解决的问题", ["选校", "选城市", "选专业方向", "转学定位与策略"], index=0)

    major_interest = st.text_input("你的兴趣方向（可选）", placeholder="例如：medical sociology / public health / policy / consulting")
    constraints = st.text_area("硬约束（可选）", height=110,
                              placeholder="例如：预算、地理范围、是否需要奖学金、是否必须大城市、想避开什么氛围…")

    st.subheader("📌 候选学校列表（可选）")
    st.caption("可以为空；如果你填了，系统会对这些学校做排序点评。")
    school_list_raw = st.text_area("每行一个学校名", height=170,
                                   placeholder="USC\nUCLA\nPomona College\nVanderbilt\n...")

generate = st.button("✨ 生成选校报告", type="primary")

if generate:
    if not api_key:
        st.error("请先在左侧输入 OpenAI API Key。")
        st.stop()

    d = parse_birthdate(birth)
    if not d:
        st.error("生日格式不对：请用 YYYY-MM-DD，例如 2006-04-15。")
        st.stop()

    sign = sun_sign(d)
    element = astro_element(sign)
    wuxing_hint = playful_wuxing(d)

    school_list = [x.strip() for x in school_list_raw.splitlines() if x.strip()]

    user_payload = {
        "Goal": goal,
        "Birthdate": str(d),
        "Birth_time": birth_time.strip() if birth_time.strip() else "Not provided",
        "Birth_place": birth_place.strip() if birth_place.strip() else "Not provided",
        "Sun_sign": sign,
        "Astro_element": element,
        "Wuxing_hint": wuxing_hint,
        "Weights": {
            "Academic_resources": w_academic,
            "Career_opportunities": w_career,
            "Life_experience": w_life,
            "Support_system": w_support
        },
        "Interest": major_interest.strip() if major_interest.strip() else "Not provided",
        "Constraints": constraints.strip() if constraints.strip() else "Not provided",
        "School_list": school_list,
        "Style_controls": {
            "Humor_level_0to10": humor,
            "Rigor_level_0to10": rigor
        }
    }

    prompt = build_prompt(user_payload)

    client = OpenAI(api_key=api_key, base_url=base_url, default_headers=extra_headers)
    with st.spinner("生成中…"):
        resp = client.responses.create(
            model=model,
            input=prompt
        )

    st.subheader("📄 你的报告")
    st.markdown(resp.output_text)
