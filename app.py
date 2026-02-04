import streamlit as st
import requests
import matplotlib.pyplot as plt
import numpy as np
import re
import os
import io
from gtts import gTTS
from duckduckgo_search import DDGS

# ============================================================
# 1. PAGE CONFIG & STYLING
# ============================================================
st.set_page_config(page_title="H2 Feynman Bot", page_icon="⚛️", layout="centered")

st.markdown("""
<style>
    /* Make equations look better */
    .st {
        font-size: 1.1em;
        margin: 10px 0;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 5px;
        border-left: 4px solid #4CAF50;
    }
    
    /* Improve text readability */
    .stMarkdown {
        font-size: 16px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. INSTRUCTIONS & CONSTANTS
# ============================================================

SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:** Richard Feynman. Tutor for Singapore H2 Physics (9478).

**CORE DIRECTIVES:**
1.  **Socratic Method:** Ask ONE simple question at a time but do not ask more than 5 questions in total. Do not solve immediately. Be encouraging and enthusiastic.
2.  **Formatting:**
    * Use LaTeX for math: $F=ma$ (inline) or $$E=mc^2$$ (block).
    * **Bold** key terms.
3.  **Tools:**
    * **Graphs:** Write `python` code using `matplotlib` and `numpy`.
    * **Images:** Use `[IMAGE: concise search query]` to show diagrams. Example: "Here is the setup: [IMAGE: youngs double slit diagram]"

**STRICTLY adhere to SEAB H2 Physics 9478 syllabus.**
"""

USER_LEVEL_INSTRUCTIONS = {
    "Beginner": "**Beginner:** Simple steps, everyday analogies. Avoid complex jargon initially.",
    "Intermediate": "**Intermediate:** Balance concepts and math. Assume basic knowledge.",
    "Advance": "**Advanced:** Focus on deep concepts and derivations, skip basics."
}

# ============================================================
# 3. AUTHENTICATION
# ============================================================
def check_login():
    """Check if user is logged in."""
    # If no password env var is set, skip login
    if "APP_PASSWORD" not in os.environ:
        return True 

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if st.session_state["authenticated"]:
        return True
    
    # Show login screen
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 H2 Physics Tutor")
        with st.form("login_form"):
            entered_password = st.text_input("Enter access password:", type="password")
            if st.form_submit_button("Login", type="primary"):
                stored_password = os.environ.get("APP_PASSWORD", "")
                if entered_password == stored_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
    
    st.stop()
    return False

if not check_login():
    st.stop()

# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================
@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Generate audio from text, skipping code/image tags."""
    try:
        # Clean text for speech
        clean_text = re.sub(r'```.*?```', 'I have generated a graph.', text, flags=re.DOTALL)
        clean_text = re.sub(r'\[IMAGE:.*?\]', 'Here is a diagram.', clean_text)
        clean_text = re.sub(r'\$.*?\$', 'equation', clean_text) # Skip reading raw latex
        
        if len(clean_text) > 5:
            tts = gTTS(text=clean_text, lang='en')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            return audio_fp
    except:
        pass
    return None

def google_search_api(query, api_key, cx):
    """Helper: Performs a single Google Search."""
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query, "cx": cx, "key": api_key,
            "searchType": "image", "num": 1, "safe": "active"
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["link"]
    except Exception:
        return None
    return None

def duckduckgo_search_api(query):
    """Helper: Fallback search using DuckDuckGo."""
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
    cx = os.environ.get("GOOGLE_CX")
    key1 = os.environ.get("GOOGLE_SEARCH_KEY")
    key2 = os.environ.get("GOOGLE_SEARCH_KEY_2")

    if key1 and cx:
        url = google_search_api(query, key1, cx)
        if url: return url
    if key2 and cx:
        url = google_search_api(query, key2, cx)
        if url: return url

    return duckduckgo_search_api(query)

def execute_plotting_code(code_snippet):
    """Execute plotting code safely."""
    try:
        plt.figure()
        local_env = {'plt': plt, 'np': np}
        exec(code_snippet, {}, local_env)
        st.pyplot(plt)
        plt.clf()
    except Exception as e:
        st.error(f"Graph Error: {e}")

def fix_latex(text):
    """Fix inconsistent LaTeX formatting for Streamlit."""
    # Convert \[ ... \] to $$ ... $$ (display math)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # Convert \( ... \) to $ ... $ (inline math)
    #text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    # Wrap standalone equations that use = and \ but miss $
    if '=' in text and '\\' in text and not '$' in text:
        text = re.sub(r'([a-zA-Zα-ωΑ-Ω_]+\s*=\s*\\[^ ]+.*?)(?=\s|$|\.|,)', r'$\1$', text)
    return text

def display_message(role, content, enable_voice=False):
    with st.chat_message(role):
        # 1. Extract Python Code
        code_blocks = []
        display_content = content
        for match in re.finditer(r'```python(.*?)```', content, re.DOTALL):
            code_blocks.append(match.group(1))
            display_content = display_content.replace(match.group(0), "")
        
        # 2. Extract Image Tags
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE)
        image_query = None
        if image_match and role == "assistant":
            image_query = image_match.group(1)
            display_content = display_content.replace(image_match.group(0), "")
        
        # 3. Fix LaTeX
        display_content = fix_latex(display_content)
        
        # 4. Render Text
        st.markdown(display_content)
        
        # 5. Render Code/Graph
        if code_blocks and role == "assistant":
            execute_plotting_code(code_blocks[0])
            with st.expander("📊 Show Graph Code"):
                st.code(code_blocks[0], language='python')

        # 6. Render Image
        if image_match and role == "assistant" and image_query:
            image_result = search_image(image_query)
            if image_result and "Error" not in image_result:
                st.image(image_result, caption=f"Diagram: {image_query}")
            else:
                st.warning(f"⚠️ Image Search Failed: {image_result}")
        
        # 7. Audio
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            audio_bytes = generate_audio(content)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3')

# ============================================================
# 5. DEEPSEEK API CALL
# ============================================================

def call_deepseek(messages, api_key, system_instruction):
    """Call DeepSeek API."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = "https://api.deepseek.com/chat/completions"
    
    # Prepend system instruction
    full_messages = [{"role": "system", "content": system_instruction}] + messages
    
    payload = {
        "model": "deepseek-chat",  # You can change this to "deepseek-coder" if needed
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ============================================================
# 6. MAIN APP UI
# ============================================================
st.title("⚛️ JPJC H2Physics Feynman Bot")

# Sidebar Configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=150)
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.header("⚙️ Configuration")
    
    # DeepSeek API Key only
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if not deepseek_key:
        deepseek_key = st.text_input("DeepSeek API Key:", type="password", 
                                    help="Get your API key from https://platform.deepseek.com/api_keys")
    
    st.divider()
    
    topic = st.selectbox("Topic:", [
        "General / Any", "Measurement & Uncertainty", "Kinematics & Dynamics", 
        "Forces & Turnings Effects", "Work, Energy, Power", "Circular Motion", 
        "Gravitational Fields", "Thermal Physics", "Oscillations & Waves", 
        "Electricity & DC Circuits", "Electromagnetism (EMI/AC)", 
        "Modern Physics (Quantum/Nuclear)"
    ])
    
    # USER LEVEL SELECTION
    user_level = st.select_slider(
        "Level:", 
        options=["Beginner", "Intermediate", "Advance"], 
        value="Intermediate"
    )
    
    enable_voice = st.toggle("🗣️ Read Aloud")
    
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your JPJC Physics tutor. What concept shall we explore today?"}]
        st.rerun()

# Chat Logic
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", 
        "content": "Hello! I'm your JPJC Physics tutor. What concept shall we explore today?"
    }]

# Display History
for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"], enable_voice)

# User Input
if prompt := st.chat_input("Ask a physics question..."):
    
    if not deepseek_key:
        st.error("⚠️ Please provide a DeepSeek API Key in the sidebar.")
        st.stop()

    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_message("user", prompt)
    
    # Prepare System Prompt with Level Instructions
    level_instruction_text = USER_LEVEL_INSTRUCTIONS.get(user_level, "")
    current_instruction = f"{SEAB_H2_MASTER_INSTRUCTIONS}\n\n{level_instruction_text}\nTopic: {topic}"
    
    response_text = ""
    used_model = "DeepSeek"

    with st.spinner("Thinking..."):
        try:
            response_text = call_deepseek(st.session_state.messages, deepseek_key, current_instruction)
            used_model = "DeepSeek"
        except Exception as e:
            st.error(f"DeepSeek API Error: {e}. Please check your API key and internet connection.")
    
    if response_text:
        # Save and Display
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        display_message("assistant", response_text, enable_voice)
    elif not response_text:
        st.error("❌ API call failed. Please check your key or internet connection.")
