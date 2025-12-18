import streamlit as st
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import re
from PIL import Image
import os
import io
import requests
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
    # Clean text so the bot doesn't read code or tags out loud
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
            return None # Failover trigger
            
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
    """Helper: Fallback search using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
            if results:
                return results[0]['image']
    except Exception as e:
        return f"Search Error: {e}"
    return "No image found."

@st.cache_data(show_spinner=False)
def search_image(query):
    """MASTER FUNCTION: Google Key 1 -> Google Key 2 -> DuckDuckGo"""
    
    # Helper to find keys in EITHER st.secrets OR os.environ
    def get_secret(name):
        if name in st.secrets:
            return st.secrets[name]
        return os.environ.get(name)

    cx = get_secret("GOOGLE_CX")
    
    # 1. Try Google Key 1
    key1 = get_secret("GOOGLE_SEARCH_KEY")
    if key1 and cx:
        url = google_search_api(query, key1, cx)
        if url: return url

    # 2. Try Google Key 2
    key2 = get_secret("GOOGLE_SEARCH_KEY_2")
    if key2 and cx:
        url = google_search_api(query, key2, cx)
        if url: return url

    # 3. Fallback to DuckDuckGo
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
        
        # 1. Check for Python Code
        code_match = re.search(r'```python(.*?)```', content, re.DOTALL)
        if code_match and role == "assistant":
            text_to_display = text_to_display.replace(code_match.group(0), "")
        
        # 2. Check for [IMAGE: query] Tags
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', text_to_display, re.IGNORECASE)
        image_result = None
        
        if image_match and role == "assistant":
            search_query = image_match.group(1)
            text_to_display = text_to_display.replace(image_match.group(0), "")
            image_result = search_image(search_query)

        # --- DISPLAY ---
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
# 3. SYSTEM INSTRUCTIONS
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
* Ask **ONE** simple question at a time.
* Use analogies first.
* **Do not** solve the math immediately. Guide the student, keep to 3 or less questions.
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
# 4. MAIN PAGE LAYOUT & SETTINGS
# -----------------------------------------------------------------------------
st.title("⚛️ JPJC H2Physics Feynman Bot")


# --- SETTINGS EXPANDER (Topic, Key, Diagnostics) ---
with st.expander("⚙️ Settings", expanded=False):
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=100)
    
    topic = st.selectbox("Topic:", ["General / Any", "Measurement & Uncertainty", "Kinematics & Dynamics", 
            "Forces & Turnings Effects", "Work, Energy, Power", "Circular Motion", 
            "Gravitational Fields", "Thermal Physics", "Oscillations & Waves", 
            "Electricity & DC Circuits", "Electromagnetism (EMI/AC)", "Modern Physics (Quantum/Nuclear)", 
            "Paper 4: Practical Skills (Spreadsheets)"])
    
    api_key = None
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")
    
    st.divider()
    
    # --- DIAGNOSTIC: Moved Inside Settings ---
    st.markdown("**🔑 Secrets Diagnostic**")
    # Check CX
    if "GOOGLE_CX" in st.secrets:
        st.success("✅ GOOGLE_CX found!")
    else:
        st.error("❌ GOOGLE_CX is missing from secrets.")
            
    # Check Key 1
    if "GOOGLE_SEARCH_KEY" in st.secrets:
        st.success("✅ GOOGLE_SEARCH_KEY found!")
    else:
        st.error("❌ GOOGLE_SEARCH_KEY is missing from secrets.")
            
    # Check Key 2
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
# 5. MAIN CHAT LOGIC
# -----------------------------------------------------------------------------
st.caption(f"Topic: **{topic}** | Level: **{user_level}**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello JPJC Physics students! I can **find diagrams** and **plot graphs**. What can I explain?"})

for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"], enable_voice)

# Standard text input only
user_input = st.chat_input("Ask a physics question...")

if user_input:
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not api_key:
        st.error("Key missing.")
        st.stop()

    try:
        genai.configure(api_key=api_key)
        
        # --- MODEL: Using 2.5-flash as requested ---
        model_name = "gemini-2.5-flash" 
        
        model = genai.GenerativeModel(
            model_name=model_name, 
            system_instruction=SEAB_H2_MASTER_INSTRUCTIONS
        )
        
        # Only keep the last 10 messages to save tokens
        recent_messages = st.session_state.messages[-10:] 
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_messages if m['role'] != 'system'])
        
        # Determine Level Instruction
        current_pedagogy = CORE_PEDAGOGY + "\n" + USER_LEVEL_INSTRUCTIONS[user_level]

        final_prompt = []
        final_prompt.append(f"USER TEXT: {user_input}")
        final_prompt.append(f"Context: {topic}")
        final_prompt.append(f"INSTRUCTIONS:\n{current_pedagogy}")
        final_prompt.append(f"Conversation History:\n{history_text}\n\nASSISTANT:")

        with st.spinner("Processing..."):
            response = model.generate_content(final_prompt)
        
        display_message("assistant", response.text, enable_voice)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"❌ Error: {e}")
        
        # Check for Model Availability Errors
        if "404" in str(e) or "not found" in str(e).lower() or "not supported" in str(e).lower():
            st.warning(f"⚠️ Model '{model_name}' failed. Listing available models for your API Key...")
            try:
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                
                if available_models:
                    st.success(f"✅ Your Key works! Available models:")
                    st.code("\n".join(available_models))
                    st.info("Update 'model_name' in line 165 of app.py to one of these.")
                else:
                    st.error("❌ Your API Key has NO access to content generation models.")
            except Exception as inner_e:
                st.error(f"Could not list models: {inner_e}")
