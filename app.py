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
# KA-TEX SETUP - MUST BE AT THE VERY TOP
# ============================================================
st.markdown("""
<!DOCTYPE html>
<html>
<head>
    <!-- KaTeX CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <style>
        /* Force KaTeX to render properly */
        .katex { 
            font-size: 1.1em !important; 
            display: inline !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .katex-display { 
            margin: 1em 0 !important;
            text-align: center;
        }
        /* Fix for common LaTeX issues */
        .stMarkdown p {
            line-height: 1.7;
            margin-bottom: 0.5em;
        }
        /* Remove extra line breaks */
        br { display: none; }
    </style>
</head>
<body>
</body>
</html>

<script>
// This is the FIX: Load KaTeX AFTER Streamlit content is ready
document.addEventListener('DOMContentLoaded', function() {
    // Load KaTeX dynamically
    function loadScript(src, callback) {
        var script = document.createElement('script');
        script.src = src;
        script.onload = callback;
        document.head.appendChild(script);
    }
    
    // Load KaTeX and auto-render
    loadScript('https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js', function() {
        loadScript('https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js', function() {
            // Wait for Streamlit to finish rendering
            setTimeout(renderAllMath, 1000);
        });
    });
    
    function renderAllMath() {
        if (typeof renderMathInElement !== 'undefined') {
            // Render math in the entire document
            renderMathInElement(document.body, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError: false,
                strict: false,
                trust: true
            });
            
            // Also try to render any new elements that appear
            setInterval(function() {
                renderMathInElement(document.body, {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false}
                    ],
                    throwOnError: false
                });
            }, 2000);
        }
    }
});
</script>
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
        
        # Step 1: Extract Python code blocks
        code_blocks = []
        display_content = content
        
        # Find and remove Python code blocks
        for match in re.finditer(r'```python(.*?)```', content, re.DOTALL):
            code_blocks.append(match.group(1))
            display_content = display_content.replace(match.group(0), '')
        
        # Step 2: Extract and process image tags
        image_matches = list(re.finditer(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE))
        image_queries = []
        
        if image_matches and role == "assistant":
            # Remove all image tags from display content
            for match in reversed(image_matches):  # Reverse to avoid index issues
                image_query = match.group(1)
                image_queries.append(image_query)
                display_content = display_content[:match.start()] + display_content[match.end():]
        
        # Step 3: Fix LaTeX formatting issues
        # Remove unwanted line breaks in equations (fixes the "t\nt" issue)
        display_content = re.sub(r'(\$[^$]+)\n([^$]+\$)', r'\1\2', display_content)
        
        # Fix: Wrap common LaTeX patterns without $ in $
        # 1. Fractions: \frac{1}{2} -> $\frac{1}{2}$
        fractions = re.findall(r'(?<!\$)\\frac\{[^}]+\}\{[^}]+\}(?!\$)', display_content)
        for frac in set(fractions):  # Use set to avoid duplicates
            display_content = display_content.replace(frac, f'${frac}$')
        
        # 2. Trigonometric functions: \sin\theta -> $\sin\theta$
        trig_patterns = [
            (r'\\sin\\?theta', r'$\\sin\\theta$'),
            (r'\\cos\\?theta', r'$\\cos\\theta$'),
            (r'\\tan\\?theta', r'$\\tan\\theta$'),
            (r'\\left\\$', r'\\left('),  # Fix broken \left$
            (r'\\right\\$', r'\\right)'), # Fix broken \right$
        ]
        
        for pattern, replacement in trig_patterns:
            display_content = re.sub(pattern, replacement, display_content)
        
        # 3. Variables with subscripts/superscripts: t^2 -> $t^2$, a_y -> $a_y$
        display_content = re.sub(r'(?<!\$)([a-zA-Z])_([a-zA-Z0-9])(?!\$\w)', r'$\1_\2$', display_content)
        display_content = re.sub(r'(?<!\$)([a-zA-Z])\^([0-9])(?!\$\w)', r'$\1^{\2}$', display_content)
        
        # Step 4: Render the main content
        # Just use markdown - KaTeX will handle the LaTeX
        st.markdown(display_content, unsafe_allow_html=False)
        
        # Step 5: Handle Python code blocks
        if code_blocks and role == "assistant" and code_blocks[0].strip():
            execute_plotting_code(code_blocks[0])
            with st.expander("📊 Show/Hide Graph Code"):
                st.code(code_blocks[0], language='python')
        
        # Step 6: Handle image search and display
        if image_queries and role == "assistant":
            for image_query in image_queries:
                try:
                    image_result = search_image(image_query)
                    if image_result and "Error" not in str(image_result):
                        st.image(image_result, caption=f"Diagram: {image_query}")
                        st.markdown(f"[🔗 Open Image in New Tab]({image_result})")
                    else:
                        st.warning(f"⚠️ Could not find image for: {image_query}")
                except Exception as e:
                    st.warning(f"⚠️ Image search error: {str(e)[:50]}...")
        
        # Step 7: Handle voice
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            try:
                audio_bytes = generate_audio(display_content)
                if audio_bytes:
                    st.audio(audio_bytes, format='audio/mp3')
            except Exception as e:
                st.error(f"Audio error: {str(e)[:50]}...")
            
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
