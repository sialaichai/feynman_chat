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
        
        # Step 1: Generic LaTeX cleaner for ALL DeepSeek output
        def clean_deepseek_latex(text):
            """
            Generic cleaner for DeepSeek's LaTeX output.
            Fixes common issues without targeting specific patterns.
            """
            # 1. Remove ALL $ symbols first (DeepSeek uses them incorrectly)
            text = text.replace('$', '')
            
            # 2. Fix common LaTeX typos (FIXED: using list of tuples)
            replacement_patterns = [
                (r'\\co\s*s', r'\\cos'),        # \co s -> \cos
                (r'\\s\s*in', r'\\sin'),        # \s in -> \sin
                (r'\\t\s*an', r'\\tan'),        # \t an -> \tan
                (r'\\the\s*ta', r'\\theta'),    # \the ta -> \theta
            ]
            
            for pattern, replacement in replacement_patterns:
                text = re.sub(pattern, replacement, text)
            
            # 3. Remove extra whitespace in equations
            text = re.sub(r'\s+', ' ', text)
            
            # 4. Wrap complete equations in $
            # Look for = followed by LaTeX commands
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    cleaned_lines.append('')
                    continue
                    
                if '=' in line and ('\\' in line or 'frac' in line):
                    # This looks like an equation line
                    parts = line.split('=', 1)  # Split on first = only
                    if len(parts) == 2:
                        # Wrap the equation part in $
                        left_side = parts[0].strip()
                        right_side = parts[1].strip()
                        if right_side:
                            cleaned_lines.append(f'{left_side} = ${right_side}$')
                        else:
                            cleaned_lines.append(line)
                    else:
                        cleaned_lines.append(line)
                else:
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
        
        # Clean the content
        display_content = clean_deepseek_latex(content)
        
        # Step 2: Extract code blocks (after cleaning)
        code_match = re.search(r'```python(.*?)```', display_content, re.DOTALL)
        code_content = None
        if code_match:
            code_content = code_match.group(1)
            display_content = display_content.replace(code_match.group(0), '')
        
        # Step 3: Extract image tags
        image_matches = list(re.finditer(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE))
        image_queries = []
        if image_matches and role == "assistant":
            for match in reversed(image_matches):
                image_queries.append(match.group(1))
                display_content = display_content[:match.start()] + display_content[match.end():]
        
        # Step 4: RENDER CLEANED CONTENT
        # Process line by line
        lines = display_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                st.write("")  # Empty line
                continue
            
            # Check what type of content this is
            if '$' in line:
                # Already has $ - render as markdown
                st.markdown(line)
            elif '=' in line and ('\\' in line or 'frac' in line):
                # Equation without $ - try to render it
                # First, try st.latex() for the equation part
                try:
                    # Extract just the equation
                    if '=' in line:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            eq_text = parts[1].strip()
                            # Try to render with st.latex()
                            st.markdown(f'{parts[0].strip()} = ')
                            st.latex(eq_text)
                        else:
                            st.markdown(line)
                    else:
                        st.markdown(line)
                except:
                    # If st.latex fails, fall back to markdown
                    st.markdown(line)
            else:
                # Plain text
                st.markdown(line)
        
        # Step 5: Handle code execution
        if code_match and role == "assistant" and code_content and code_content.strip():
            execute_plotting_code(code_content)
            with st.expander("📊 Show/Hide Graph Code"):
                st.code(code_content, language='python')
        
        # Step 6: Handle images
        if image_queries and role == "assistant":
            for query in image_queries:
                try:
                    img_url = search_image(query)
                    if img_url and "Error" not in str(img_url):
                        st.image(img_url, caption=f"Diagram: {query}")
                except:
                    pass
        
        # Step 7: Handle voice
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            try:
                audio = generate_audio(display_content)
                if audio:
                    st.audio(audio, format='audio/mp3')
            except:
                pass
                
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
1. **Write equations in plain LaTeX WITHOUT $ symbols:**
   - Write: y = x \tan\theta - \frac{g x^{2}}{2 u^{2} \cos^{2}\theta}
   - NOT: $y = x $\tan$\theta$$ - $\frac{g $x^{2}${2 $u^{2}$ \co$s^{2}$\theta}$$

2. **Use correct LaTeX commands:**
   - \cos NOT \co s
   - \theta NOT \the ta
   - \tan NOT \t an

3. **Keep equations on one line.**

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
