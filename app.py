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

# ============================================================
# 1. KA-TEX SETUP (MUST BE AT THE VERY TOP)
# ============================================================
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" integrity="sha384-n8MVd4RsNIU0tAv4ct0nTaAbDJwPJzDEaqSD1odI+WdtXRGWt2kTvGFasHpSy3SV" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" integrity="sha384-XjKyOOlGwcjNTAIQHIpgOno0Hl1YQqzUOEleOLALmuqehneUG+vnGctmUb0ZY0l8" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05" crossorigin="anonymous"></script>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for Streamlit to load content
    setTimeout(function() {
        renderMathInElement(document.body, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\]', display: true}
            ],
            throwOnError: false,
            strict: 'ignore'
        });
    }, 100);
});
</script>

<style>
    .katex { font-size: 1.05em; }
    .katex-display { margin: 1em 0; text-align: center; }
    .stMarkdown p { line-height: 1.6; margin-bottom: 0.8em; }
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
        
        # Step 1: Extract and remove code blocks
        display_content = content
        code_blocks = []
        
        for match in re.finditer(r'```python(.*?)```', content, re.DOTALL):
            code_blocks.append(match.group(1))
            display_content = display_content.replace(match.group(0), '')
        
        # Step 2: Extract and remove image tags
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE)
        image_query = None
        
        if image_match and role == "assistant":
            image_query = image_match.group(1)
            display_content = display_content.replace(image_match.group(0), '')
        
        # Step 3: CRITICAL - Fix LaTeX delimiters for KaTeX
        # KaTeX needs \( \) or $$ $$, but DeepSeek gives [ ] 
        # Convert [ ... ] to $$ ... $$ for display math
        display_content = re.sub(r'\[\s*(.*?)\s*\]', r'$$\1$$', display_content, flags=re.DOTALL)
        
        # Also ensure inline math uses $...$ format
        # Convert ( ... ) to $...$ if it contains LaTeX
        display_content = re.sub(r'\(([^)]*\\[^)]*)\)', r'$\1$', display_content)
        
        # Step 4: Clean up newlines in equations
        display_content = re.sub(r'\$\$(.*?)\$\$', 
                                lambda m: f'$${m.group(1).replace(chr(10), " ").replace(chr(13), " ")}$$', 
                                display_content, flags=re.DOTALL)
        
        # Step 5: SIMPLE RENDERING - KaTeX will handle it
        st.markdown(display_content, unsafe_allow_html=False)
        
        # Step 6: Handle code execution
        if code_blocks and role == "assistant" and code_blocks[0].strip():
            execute_plotting_code(code_blocks[0])
            with st.expander("📊 Show/Hide Graph Code"):
                st.code(code_blocks[0], language='python')
        
        # Step 7: Handle images
        if image_match and role == "assistant" and image_query:
            img_url = search_image(image_query)
            if img_url and "Error" not in str(img_url):
                st.image(img_url, caption=f"Diagram: {image_query}")
        
        # Step 8: Handle voice
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

**CRITICAL FORMATTING RULES FOR MATHEMATICS:**
1. **ALWAYS use $ for inline equations:** $F = ma$, $v = u + at$
2. **ALWAYS use $$ for display equations:**
   $$E = mc^2$$
   $$y = (u \sin \theta) t - \frac{1}{2} g t^2$$
3. **NEVER use [ ] brackets for equations**
4. **NEVER put equations on separate lines**
5. **Keep equations inline with text**

**Graphing:** Use ```python blocks for plotting code.
**Diagrams:** Use [IMAGE: query] tags.

**Content:** STRICTLY adhere to H2 Physics 9478 syllabus.
"""

CORE_PEDAGOGY = """
**PEDAGOGY (SOCRATIC):**
* Ask ONE simple question at a time.
* Use analogies first.
* Guide the student, don't solve immediately.
* Only provide full solution if student says "I give up".
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
