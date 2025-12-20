import streamlit as st
import requests
import matplotlib.pyplot as plt
import numpy as np
import re
from PIL import Image
import os
import io
from gtts import gTTS
from duckduckgo_search import DDGS

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="H2 Feynman Bot",
    page_icon="⚛️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Generates MP3 audio from text, skipping code/image tags."""
    clean_text = re.sub(r'```.*?```', 'I have generated a graph.', text, flags=re.DOTALL)
    clean_text = re.sub(r'\[IMAGE:.*?\]', 'Here is a diagram.', clean_text)
    try:
        tts = gTTS(text=clean_text, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except:
        return None

def google_search_api(query, api_key, cx):
    """Helper: Performs a single Google Search."""
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "cx": cx,
            "key": api_key,
            "searchType": "image",
            "num": 3,
            "safe": "active"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code in [403, 429]:
            return None
            
        data = response.json()
        
        if "items" in data and len(data["items"]) > 0:
            for item in data["items"]:
                link = item["link"]
                if link.lower().endswith(('.jpg', '.jpeg', '.png')):
                    return link
            return data["items"][0]["link"]
            
    except Exception as e:
        print(f"Google API Exception: {e}")
        return None
    return None

def duckduckgo_search_api(query):
    """Improved Fallback search with headers and region."""
    try:
        with DDGS(timeout=20) as ddgs:
            results = ddgs.images(keywords=query, region='wt-wt', safesearch='moderate')
            first_result = next(results, None)
            if first_result:
                return first_result['image']
    except Exception as e:
        return f"Search Error: {e}"
    return "No image found."

@st.cache_data(show_spinner=False)
def search_image(query):
    """MASTER FUNCTION: Google Key 1 -> Google Key 2 -> DuckDuckGo"""
    
    def get_secret(name):
        if name in st.secrets:
            return st.secrets[name]
        return os.environ.get(name)

    cx = get_secret("GOOGLE_CX")
    
    key1 = get_secret("GOOGLE_SEARCH_KEY")
    if key1 and cx:
        url = google_search_api(query, key1, cx)
        if url: return url

    key2 = get_secret("GOOGLE_SEARCH_KEY_2")
    if key2 and cx:
        url = google_search_api(query, key2, cx)
        if url: return url

    return duckduckgo_search_api(query)
   
def execute_plotting_code(code_snippet):
    """Executes Python code to generate a Matplotlib plot inside Streamlit."""
    try:
        plt.figure()
        local_env = {'plt': plt, 'np': np}
        exec(code_snippet, {}, local_env)
        st.pyplot(plt)
        plt.clf()
    except Exception as e:
        st.error(f"Graph Error: {e}")

def display_message(role, content, enable_voice=False):
    with st.chat_message(role):
        
        text_to_display = content
        
        code_match = re.search(r'```python(.*?)```', content, re.DOTALL)
        if code_match and role == "assistant":
            text_to_display = text_to_display.replace(code_match.group(0), "")
        
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', text_to_display, re.IGNORECASE)
        image_result = None
        
        if image_match and role == "assistant":
            search_query = image_match.group(1)
            text_to_display = text_to_display.replace(image_match.group(0), "")
            image_result = search_image(search_query)

        st.markdown(text_to_display)

        if code_match and role == "assistant":
            with st.expander("Show Graph Code"):
                st.code(code_match.group(1), language='python')
            execute_plotting_code(code_match.group(1))
            
        if image_match and role == "assistant":
            if image_result and "Error" not in image_result:
                st.image(image_result, caption=f"Diagram: {image_match.group(1)}")
                st.markdown(f"[🔗 Open Image in New Tab]({image_result})")
            else:
                st.warning(f"⚠️ Image Search Failed: {image_result}")

        if enable_voice and role == "assistant" and len(text_to_display.strip()) > 0:
            audio_bytes = generate_audio(text_to_display)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3')

# -----------------------------------------------------------------------------
# 3. DEEPSEEK API INTEGRATION
# -----------------------------------------------------------------------------
def call_deepseek_api(messages, api_key, model="deepseek-chat"):
    """Call DeepSeek API with conversation history."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.deepseek.com/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"DeepSeek API Error: {e}")

# -----------------------------------------------------------------------------
# 4. SYSTEM INSTRUCTIONS
# -----------------------------------------------------------------------------
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:** Richard Feynman. Tutor for Singapore H2 Physics (9478).
**CORE DIRECTIVE:** STRICTLY adhere to the Syllabus SEAB H2 Physics 9478 topics and conventions. Reject non-included topics from UK A-level physics.

**CORE TOOLS:**
1.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops.
    * **Format:** Enclose strictly in ` ```python ` blocks.

2.  **Diagrams (Web Search):** If you need to show a diagram, YOU MUST USE THE TAG.
    * **Syntax:** `[IMAGE: <concise search query>]`
    * Example: "Here is the setup: [IMAGE: rutherford gold foil experiment diagram]"
    * **Rule:** Do NOT use markdown image links. Use `[IMAGE:...]` ONLY.

**Math:** Use LaTeX ($F=ma$) for formulas.
"""

CORE_PEDAGOGY = """
**PEDAGOGY (SOCRATIC):**
* Ask **ONE** simple question at a time, limit to 3 or less questions.
* Use analogies first.
* **Do not** solve the math immediately. Guide the student.
* **The "I Give Up" Clause:** Only provide the full solution if the student explicitly says "I give up" or "Just tell me the answer."
* **Summary:** When they understand, provide a summary in a blockquote (`>`).
"""

USER_LEVEL_INSTRUCTIONS = {
    "Beginner": """
**USER LEVEL: BEGINNER**
* **Approach:** Highly supportive, patient, and simplifying.
* **Instruction:** Break down complex concepts into very small, digestible steps. Use everyday analogies extensively. Avoid dense jargon initially. Assume the student is encountering this for the first time.
""",
    "Intermediate": """
**USER LEVEL: INTERMEDIATE**
* **Approach:** Encouraging and standard academic.
* **Instruction:** Balance conceptual understanding with mathematical rigor. Use standard H2 Physics terminology. Guide the student through standard problem-solving procedures without over-simplifying.
""",
    "Advance": """
**USER LEVEL: ADVANCE**
* **Approach:** Rigorous, concise, and challenging.
* **Instruction:** Move quickly through basic definitions. Focus on derivations, assumptions, and complex application. Challenge the student with extension questions. Skip basic algebraic steps.
"""
}

# -----------------------------------------------------------------------------
# 5. MAIN PAGE LAYOUT & SETTINGS
# -----------------------------------------------------------------------------
st.title("⚛️ JPJC H2Physics Feynman Bot (DeepSeek)")

# --- SETTINGS EXPANDER (Topic, Key, Diagnostics) ---
with st.expander("⚙️ Settings", expanded=False):
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=100)
    
    topic = st.selectbox("Topic:", ["General / Any", "Measurement & Uncertainty", "Kinematics & Dynamics", 
            "Forces & Turnings Effects", "Work, Energy, Power", "Circular Motion", 
            "Gravitational Fields", "Thermal Physics", "Oscillations & Waves", 
            "Electricity & DC Circuits", "Electromagnetism (EMI/AC)", "Modern Physics (Quantum/Nuclear)", 
            "Paper 4: Practical Skills (Spreadsheets)"])
    
    api_key = None
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    else:
        api_key = st.text_input("Enter DeepSeek API Key", type="password")
    
    # Model selection
    model_name = st.selectbox(
        "Model:",
        ["deepseek-chat", "deepseek-coder"],
        index=0,
        help="deepseek-chat: General purpose, deepseek-coder: Better for code generation"
    )
    
    st.divider()
    
    # --- DIAGNOSTIC ---
    st.markdown("**🔑 Secrets Diagnostic**")
    if "GOOGLE_CX" in st.secrets:
        st.success("✅ GOOGLE_CX found!")
    else:
        st.error("❌ GOOGLE_CX is missing from secrets.")
            
    if "GOOGLE_SEARCH_KEY" in st.secrets:
        st.success("✅ GOOGLE_SEARCH_KEY found!")
    else:
        st.error("❌ GOOGLE_SEARCH_KEY is missing from secrets.")
            
    if "GOOGLE_SEARCH_KEY_2" in st.secrets:
        st.success("✅ GOOGLE_SEARCH_KEY_2 found!")
    else:
        st.warning("⚠️ GOOGLE_SEARCH_KEY_2 missing (Optional).")

# --- USER LEVEL SELECTION ---
user_level = st.radio("Competency Level:", ["Beginner", "Intermediate", "Advance"], horizontal=True, index=1)

# --- CENTRAL CONTROL ROW (Voice & Clear Chat) ---
col_voice, col_clear = st.columns(2)
with col_voice:
    enable_voice = st.toggle("🗣️ Read Aloud", value=False)
with col_clear:
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 6. MAIN CHAT LOGIC
# -----------------------------------------------------------------------------
st.caption(f"Topic: **{topic}** | Level: **{user_level}** | Model: **{model_name}**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello JPJC Physics students! I can **find diagrams** and **plot graphs**. What can I explain?"
    })

for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"], enable_voice)

# Standard text input only
user_input = st.chat_input("Ask a physics question...")

if user_input:
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not api_key:
        st.error("DeepSeek API Key missing. Please enter it in Settings.")
        st.stop()

    try:
        # Build conversation history for DeepSeek
        messages = []
        
        # Add system instruction first
        current_pedagogy = CORE_PEDAGOGY + "\n" + USER_LEVEL_INSTRUCTIONS[user_level]
        full_system_message = f"{SEAB_H2_MASTER_INSTRUCTIONS}\n\n{current_pedagogy}\n\nCurrent Topic: {topic}"
        
        messages.append({
            "role": "system", 
            "content": full_system_message
        })
        
        # Add conversation history (last 10 messages)
        recent_messages = st.session_state.messages[-10:]
        for msg in recent_messages:
            if msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})
            else:
                messages.append({"role": "user", "content": msg["content"]})
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        with st.spinner("Processing..."):
            response_text = call_deepseek_api(messages, api_key, model_name)
        
        display_message("assistant", response_text, enable_voice)
        st.session_state.messages.append({"role": "assistant", "content": response_text})

    except Exception as e:
        st.error(f"❌ Error: {e}")
        
        # Check for API key errors
        if "401" in str(e):
            st.error("Invalid API Key. Please check your DeepSeek API key.")
        elif "429" in str(e):
            st.error("Rate limit exceeded. Please wait a moment before trying again.")
        else:
            st.error(f"API Error: {e}")
