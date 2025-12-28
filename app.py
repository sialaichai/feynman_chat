import streamlit as st
import requests
import matplotlib.pyplot as plt
import numpy as np
import re
import os
import io
from gtts import gTTS
from duckduckgo_search import DDGS
import time

# Add this after imports
st.markdown("""
<style>
    /* Make equations look better */
    .stLatex {
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
# 2. PASSWORD AUTHENTICATION
# ============================================================
def check_login():
    """Check if user is logged in."""
    
    def authenticate():
        entered_password = st.session_state.get("login_password", "")
        stored_password = os.environ.get("APP_PASSWORD", "")
        
        if entered_password == stored_password:
            st.session_state["authenticated"] = True
            st.session_state["login_time"] = time.time()
            if "login_password" in st.session_state:
                del st.session_state["login_password"]
            st.rerun()
        else:
            st.session_state["authenticated"] = False
            st.error("Incorrect password.")
    
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if st.session_state["authenticated"]:
        return True
    
    # Show login screen
    st.set_page_config(page_title="Login - H2 Physics Bot", layout="centered")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 H2 Physics Tutor")
        st.markdown("**JPJC Physics Feynman Bot - Login Required**")
        
        if "APP_PASSWORD" not in os.environ:
            st.error("⚠️ Password not configured.")
            st.stop()
        
        with st.form("login_form"):
            password = st.text_input("Enter access password:", type="password", key="login_password")
            submit = st.form_submit_button("Login", type="primary")
            if submit:
                authenticate()
        
        st.markdown("---")
        st.caption("ℹ️ Contact instructor if password forgotten.")
    
    st.stop()
    return False

# ============================================================
# 3. MAIN APP (AFTER LOGIN)
# ============================================================
if not check_login():
    st.stop()

st.set_page_config(page_title="H2 Feynman Bot", page_icon="⚛️", layout="centered")

# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================
@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Generate audio from text."""
    try:
        # Clean text for speech
        clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'\[IMAGE:.*?\]', '', clean_text)
        clean_text = re.sub(r'\$.*?\$', 'equation', clean_text)
        
        if len(clean_text) > 10:
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
        if name in os.environ:
            return os.environ[name]
        return os.environ.get(name)

    cx = get_secret("GOOGLE_CX")
    
    # 1. Try Google Key 1
    key1 = get_secret("GOOGLE_SEARCH_KEY")
    if key1 and cx:
        url = google_search_api(query, key1, cx)
        if url: 
            return url

    # 2. Try Google Key 2
    key2 = get_secret("GOOGLE_SEARCH_KEY_2")
    if key2 and cx:
        url = google_search_api(query, key2, cx)
        if url: 
            return url

    # 3. Fallback to DuckDuckGo
    return duckduckgo_search_api(query)

def execute_plotting_code(code_snippet):
    """Execute plotting code."""
    try:
        plt.figure()
        local_env = {'plt': plt, 'np': np}
        exec(code_snippet, {}, local_env)
        st.pyplot(plt)
        plt.clf()
    except Exception as e:
        st.error(f"Graph Error: {e}")

# ============================================================
# 5. FIXED DISPLAY_MESSAGE FUNCTION
# ============================================================
def fix_deepseek_latex_inconsistency(text):
    """
    Fix DeepSeek's inconsistent LaTeX formatting in one pass.
    Handles: missing $, mixed formats, Greek letters, etc.
    """
    # 1. First, ensure all display math \[ \] becomes $$ $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # 2. Ensure all inline math \( \) becomes $ $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    
    # 3. Find and wrap equations that have = and \ but no $
    # Pattern: word= \frac or word= \lambda, etc.
    patterns_to_wrap = [
        # Equations with \frac without $
        (r'([a-zA-Zα-ωΑ-Ω_]+)\s*=\s*(\\frac\{[^}]+\}\{[^}]+\})', r'$\1 = \2$'),
        # Equations with \lambda, \theta, etc. without $
        (r'([a-zA-Zα-ωΑ-Ω_]+)\s*=\s*(\\[a-zA-Z]+)', r'$\1 = \2$'),
        # Plain Greek letters in equations (λ, θ, φ without \)
        (r'([λθφ])\s*_\{([^}]+)\}\s*=\s*(\\[^ ]+)', r'$\1_{\2} = \3$'),
    ]
    
    for pattern, replacement in patterns_to_wrap:
        text = re.sub(pattern, replacement, text)
    
    # 4. Ensure any remaining \frac{}{} without $ gets wrapped
    if '\\frac' in text and not re.search(r'\$.*\\frac.*\$', text):
        # Find the \frac and some context around it
        text = re.sub(r'([^$]*)(\\frac\{[^}]+\}\{[^}]+\})([^$]*)', 
                     r'\1$\2$\3', text)
    
    return text

def display_message(role, content, enable_voice=False):
    with st.chat_message(role):
        
        # STEP 1: Extract Python code blocks FIRST
        code_blocks = []
        display_content = content
        
        # Find and remove ALL Python code blocks from the displayed text
        for match in re.finditer(r'```python(.*?)```', content, re.DOTALL):
            code_blocks.append(match.group(1))  # Save the code
            # Remove the entire ```python ... ``` block from displayed content
            display_content = display_content.replace(match.group(0), "")
        
        # STEP 2: Extract image tags similarly
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE)
        image_result = None
        image_query = None
        
        if image_match and role == "assistant":
            image_query = image_match.group(1)
            display_content = display_content.replace(image_match.group(0), "")
        
        # STEP 3: ✅ ONLY FIX ADDED: Convert DeepSeek's LaTeX to Streamlit format
        # Convert \[ ... \] to $$ ... $$ (display math)
        display_content = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', display_content, flags=re.DOTALL)
        # Convert \( ... \) to $ ... $ (inline math)
        display_content = re.sub(r'\\\((.*?)\\\)', r'$\1$', display_content)
        # ADD THIS: Wrap standalone equations without $ 
        if '=' in display_content and '\\' in display_content and not '$' in display_content:
            # This finds patterns like: λ_{min} = \frac{hc}{eV}
            # And wraps them: $λ_{min} = \frac{hc}{eV}$
            display_content = re.sub(r'([a-zA-Zα-ωΑ-Ω_]+\s*=\s*\\[^ ]+.*?)(?=\s|$|\.|,)', r'$\1$', display_content)
        
        # STEP 3: Fix DeepSeek's inconsistent LaTeX
        #display_content = fix_deepseek_latex_inconsistency(display_content)
        
# STEP 4: Display the cleaned text (without code blocks)
        print(f"BEFORE MARKDOWN: {display_content}")
        st.markdown(display_content)
        
        # STEP 5: Handle Python code blocks - ONLY in expander
        if code_blocks and role == "assistant":
            # Execute the FIRST code block to generate the graph
            execute_plotting_code(code_blocks[0])
            
            # Create ONE expander for all code blocks
            with st.expander("📊 Show/Hide Graph Code"):
                for i, code in enumerate(code_blocks):
                    if len(code_blocks) > 1:
                        st.markdown(f"**Code block {i+1}:**")
                    st.code(code, language='python')
        
        # STEP 6: ✅ YOUR ORIGINAL IMAGE HANDLING - UNCHANGED
        if image_match and role == "assistant" and image_query:
            image_result = search_image(image_query)  # Calls YOUR complete search system
            if image_result and "Error" not in image_result:
                st.image(image_result, caption=f"Diagram: {image_query}")
                st.markdown(f"[🔗 Open Image in New Tab]({image_result})")
            else:
                st.warning(f"⚠️ Image Search Failed: {image_result}")
        
        # STEP 7: Handle voice (keep as is)
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            clean_text = re.sub(r'\$.*?\$', 'mathematical expression', content)  # ← CHANGE: content NOT display_content
            clean_text = re.sub(r'\\[a-zA-Z]+', '', clean_text)
            audio_bytes = generate_audio(clean_text)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3')
                
# ============================================================
# 6. DEEPSEEK API
# ============================================================
def call_deepseek_api(messages, api_key, model="deepseek-chat"):
    """Call DeepSeek API."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = "https://api.deepseek.com/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"DeepSeek API Error: {e}")

# ============================================================
# 7. SYSTEM INSTRUCTIONS (UPDATED FOR BETTER LATEX)
# ============================================================
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:** Richard Feynman. Tutor for Singapore H2 Physics (9478).

**IMPORTANT FOR IMAGES:**
- When showing a diagram, ALWAYS include descriptive text BEFORE the [IMAGE: ...] tag
- Example: "Here's a diagram showing helical motion: [IMAGE: charged particle helical motion in magnetic field 3d diagram]"
- NEVER respond with ONLY an [IMAGE: ...] tag


**MATHEMATICAL FORMATTING:**
1. **For displayed equations (centered, on own line), use:** \[ equation \]
   Example: \[ F = ma \], \[ E = mc^2 \]

2. **For inline equations (within text), use:** \( equation \)
   Example: The acceleration due to gravity is \( g = 9.81 \text{ m/s}^2 \).

3. **Use standard LaTeX commands inside these:**
   - Fractions: \frac{numerator}{denominator}
   - Greek letters: \alpha, \beta, \gamma, \theta, \phi
   - Trigonometric: \sin, \cos, \tan
   
4. **Keep equations on one line.**

5.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops.
    * **Format:** Enclose strictly in ` ```python ` blocks.

6.  **Diagrams (Web Search):** If you need to show a diagram, YOU MUST USE THE TAG.
    * **Syntax:** `[IMAGE: <concise search query>]`
    * Example: "Here is the setup: [IMAGE: rutherford gold foil experiment diagram]"
    * **Rule:** Do NOT use markdown image links. Use `[IMAGE:...]` ONLY.

**Mathematics**
*No cross product"
*No dot product"

**Content:** STRICTLY adhere to H2 Physics 9478 syllabus.
"""

CORE_PEDAGOGY = """
**PEDAGOGY (SOCRATIC):**
* Only provide full solution if student says "I give up".
* Ask ONE simple question at a time, not more than 3 questions.
* Use analogies first.
* Guide the student, don't solve immediately.

"""

USER_LEVEL_INSTRUCTIONS = {
    "Beginner": "**Beginner:** Simple steps, everyday analogies.",
    "Intermediate": "**Intermediate:** Balance concepts and math.",
    "Advance": "**Advanced:** Focus on derivations, skip basics."
}

# ============================================================
# 8. MAIN APP UI
# ============================================================
st.title("⚛️ JPJC H2Physics Feynman Bot")

# Sidebar
with st.sidebar:
    if st.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    topic = st.selectbox("Topic:", ["General / Any", "Kinematics & Dynamics", "Forces", 
                                    "Work, Energy, Power", "Circular Motion", "Gravitational Fields"])
    
    # API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = st.text_input("DeepSeek API Key:", type="password")
    
    model_name = st.selectbox("Model:", ["deepseek-chat", "deepseek-coder"])
    user_level = st.radio("Level:", ["Beginner", "Intermediate", "Advance"], horizontal=True, index=1)
    enable_voice = st.toggle("🗣️ Read Aloud")

#with st.sidebar:
    if st.button("Test Image Search System"):
        test_query = "physics diagram"
        st.write(f"Testing search for: {test_query}")
        
        # Test each component
        cx = os.environ.get("GOOGLE_CX", "Not set")
        key1 = os.environ.get("GOOGLE_SEARCH_KEY", "Not set")
        
        st.write(f"GOOGLE_CX: {'✅ Set' if cx != 'Not set' else '❌ Missing'}")
        st.write(f"GOOGLE_SEARCH_KEY: {'✅ Set' if key1 != 'Not set' else '❌ Missing'}")
        
        # Test the search
        result = search_image(test_query)
        st.write(f"Search result: {result}")
        
        if result and result.startswith("http"):
            st.image(result, caption="Test Image", width=300)
            st.success("✅ Image search working!")
        else:
            st.error("❌ Image search failed")


# Chat interface
st.caption(f"Topic: {topic} | Level: {user_level}")

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", 
        "content": "Hello! I'm your H2 Physics tutor. What would you like to learn today?"
    }]

for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"], enable_voice)

# User input
if prompt := st.chat_input("Ask a physics question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    if not api_key:
        st.error("API Key missing.")
        st.stop()
    
    try:
        # Build messages for API
        messages = [{"role": "system", "content": f"{SEAB_H2_MASTER_INSTRUCTIONS}\n{CORE_PEDAGOGY}\n{USER_LEVEL_INSTRUCTIONS[user_level]}\nTopic: {topic}"}]
        
        # Add conversation history
        for msg in st.session_state.messages[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Get response
        with st.spinner("Thinking..."):
            response = call_deepseek_api(messages, api_key, model_name)
        
        # Display response
        display_message("assistant", response, enable_voice)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
    except Exception as e:
        st.error(f"Error: {e}")
