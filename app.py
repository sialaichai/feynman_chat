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
        stored_password = st.secrets.get("APP_PASSWORD", "")
        
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
        
        if "APP_PASSWORD" not in st.secrets:
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

def search_image(query):
    """Search for images."""
    try:
        with DDGS(timeout=10) as ddgs:
            results = ddgs.images(keywords=query, max_results=1)
            for result in results:
                return result['image']
    except:
        pass
    return None

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
def display_message(role, content, enable_voice=False):
    with st.chat_message(role):
        
        # Step 1: Extract code blocks and image tags
        display_content = content
        
        # Extract Python code
        code_match = re.search(r'```python(.*?)```', display_content, re.DOTALL)
        code_content = None
        if code_match:
            code_content = code_match.group(1)
            display_content = display_content.replace(code_match.group(0), '')
        
        # Extract image tags
        image_matches = list(re.finditer(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE))
        image_queries = []
        if image_matches and role == "assistant":
            for match in reversed(image_matches):
                image_queries.append(match.group(1))
                display_content = display_content[:match.start()] + display_content[match.end():]
        
        # Step 2: FIX DEEPSEEK'S BROKEN FORMATTING
        # This is the key fix for your specific problem
        
        # Fix 1: Remove line breaks in variable names (t\nt -> t)
        display_content = re.sub(r'(\b[a-zA-Zθφ])\s*\n\s*\1\b', r'\1', display_content)
        
        # Fix 2: Remove line breaks around equals signs (y\n=\nx -> y = x)
        display_content = re.sub(r'(\b[a-zA-Z])\s*\n\s*=\s*\n\s*([a-zA-Z])', r'\1 = \2', display_content)
        
        # Fix 3: Fix the \co\n\cos issue
        display_content = re.sub(r'\\co\s*\n\s*\\cos', r'\\cos', display_content)
        
        # Fix 4: Ensure ALL LaTeX math has $ delimiters
        # Find patterns like \tan\theta, \frac{1}{2}, etc. without $
        latex_patterns = [
            (r'(?<!\$)\\frac\{([^}]+)\}\{([^}]+)\}(?!\$\w)', r'$\\frac{\1}{\2}$'),
            (r'(?<!\$)\\(tan|sin|cos)\\?theta(?!\$\w)', r'$\\\1\\theta$'),
            (r'(?<!\$)([a-zA-Z])\^\{?([0-9]+)\}?(?!\$\w)', r'$\1^{\2}$'),
            (r'(?<!\$)\\theta(?!\$\w)', r'$\\theta$'),
        ]
        
        for pattern, replacement in latex_patterns:
            display_content = re.sub(pattern, replacement, display_content)
        
        # Fix 5: Fix equations that start with variable= but no $
        # Pattern: y=x\tan\theta (no space, no $)
        display_content = re.sub(
            r'(\b[a-zA-Z])=([^$\s].*?\\[^$]+)(?=\s|$|\.|,)',
            r'\1 = $\2$',
            display_content
        )
        
        # Step 3: RENDER THE CONTENT PROPERLY
        # Split into paragraphs to handle different content types
        paragraphs = display_content.split('\n\n')
        
        for para in paragraphs:
            if not para.strip():
                continue
                
            # Check if this is mostly an equation
            lines = para.strip().split('\n')
            
            if len(lines) == 1 and '=' in para and ('\\' in para or '$' in para):
                # Single line equation - render with st.latex()
                eq_text = para.strip()
                # Remove $ delimiters for st.latex()
                if eq_text.startswith('$') and eq_text.endswith('$'):
                    eq_text = eq_text[1:-1]
                try:
                    st.latex(eq_text)
                except:
                    st.markdown(f'${eq_text}$')
            else:
                # Multi-line or text content - render as markdown
                for line in lines:
                    if line.strip():
                        st.markdown(line.strip())
        
        # Step 4: Handle code execution
        if code_match and role == "assistant" and code_content and code_content.strip():
            execute_plotting_code(code_content)
            with st.expander("📊 Show/Hide Graph Code"):
                st.code(code_content, language='python')
        
        # Step 5: Handle images
        if image_queries and role == "assistant":
            for query in image_queries:
                try:
                    img_url = search_image(query)
                    if img_url and "Error" not in str(img_url):
                        st.image(img_url, caption=f"Diagram: {query}")
                    else:
                        st.warning(f"Image not found: {query}")
                except:
                    st.warning(f"Image search failed for: {query}")
        
        # Step 6: Handle voice
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            audio = generate_audio(display_content)
            if audio:
                st.audio(audio, format='audio/mp3')
            
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

**MATHEMATICAL FORMATTING - THIS IS CRITICAL:**
1. **ALWAYS use $ around EVERY mathematical expression:**
   - CORRECT: $u \sin\theta$, $\frac{1}{2} g t^2$, $t = \frac{x}{u \cos\theta}$
   - WRONG: u \sin\theta, \frac{1}{2} g t^2, t = \frac{x}{u \cos\theta}
   
2. **NEVER put variables on separate lines:**
   - WRONG: The vertical position at time 
     t
     t is: y = ...
   - CORRECT: The vertical position at time $t$ is: $y = ...$
   
3. **Keep equations simple and on one line:**
   - Use: $y = x \tan\theta - \frac{g x^2}{2 u^2 \cos^2\theta}$
   - Not: y = x tanθ - \frac{gx^2}{2u^2cos^2θ}

4.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops.
    * **Format:** Enclose strictly in ` ```python ` blocks.

5.  **Diagrams (Web Search):** If you need to show a diagram, YOU MUST USE THE TAG.
    * **Syntax:** `[IMAGE: <concise search query>]`
    * Example: "Here is the setup: [IMAGE: rutherford gold foil experiment diagram]"
    * **Rule:** Do NOT use markdown image links. Use `[IMAGE:...]` ONLY.




**Content:** STRICTLY adhere to H2 Physics 9478 syllabus.
"""

CORE_PEDAGOGY = """
**PEDAGOGY (SOCRATIC):**
* Only provide full solution if student says "I give up".
* Ask ONE simple question at a time.
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
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = st.text_input("DeepSeek API Key:", type="password")
    
    model_name = st.selectbox("Model:", ["deepseek-chat", "deepseek-coder"])
    user_level = st.radio("Level:", ["Beginner", "Intermediate", "Advance"], horizontal=True, index=1)
    enable_voice = st.toggle("🗣️ Read Aloud")

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
