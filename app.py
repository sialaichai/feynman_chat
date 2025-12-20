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

# KaTeX for beautiful LaTeX rendering (ADD AT THE TOP)
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" integrity="sha384-n8MVd4RsNIU0tAv4ct0nTaAbDJwPJzDEaqSD1odI+WdtXRGWt2kTvGFasHpSy3SV" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" integrity="sha384-XjKyOOlGwcjNTAIQHIpgOno0Hl1YQqzUOEleOLALmuqehneUG+vnGctmUb0ZY0l8" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05" crossorigin="anonymous"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        renderMathInElement(document.body, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\]', display: true}
            ],
            throwOnError: false,
            strict: false  // Be more forgiving with LaTeX errors
        });
    });
</script>

<style>
    /* Make equations blend with text */
    .katex { 
        font-size: 1.05em !important; 
        display: inline !important;
        margin: 0 0.1em !important;
    }
    .katex-display { 
        margin: 0.8em 0 !important; 
        text-align: center;
    }
    p { 
        line-height: 1.7; 
        margin-bottom: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. PASSWORD AUTHENTICATION (Runs first before anything else)
# -----------------------------------------------------------------------------
def check_login():
    """Check if user is logged in. Shows login screen if not."""
    
    def authenticate():
        """Check if entered password matches the one in secrets."""
        entered_password = st.session_state.get("login_password", "")
        stored_password = st.secrets.get("APP_PASSWORD", "")
        
        if entered_password == stored_password:
            st.session_state["authenticated"] = True
            st.session_state["login_time"] = time.time()
            # Clear the password from session state
            if "login_password" in st.session_state:
                del st.session_state["login_password"]
            st.rerun()
        else:
            st.session_state["authenticated"] = False
            st.error("Incorrect password. Please try again.")
    
    # Initialize authentication state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    # Check session timeout (optional: 24 hours)
    if "login_time" in st.session_state:
        session_duration = time.time() - st.session_state["login_time"]
        if session_duration > 86400:  # 24 hours in seconds
            st.session_state["authenticated"] = False
            if "login_time" in st.session_state:
                del st.session_state["login_time"]
            st.warning("Session expired. Please log in again.")
    
    # If authenticated, return True
    if st.session_state["authenticated"]:
        return True
    
    # Show login screen
    st.set_page_config(page_title="Login - H2 Physics Bot", layout="centered")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 H2 Physics Tutor")
        st.markdown("**JPJC Physics Feynman Bot - Login Required**")
        
        # Check if password is configured
        if "APP_PASSWORD" not in st.secrets:
            st.error("⚠️ Password not configured in app settings.")
            st.info("Please add 'APP_PASSWORD = \"your_password\"' to Streamlit Cloud Secrets.")
            st.stop()
        
        # Login form
        with st.form("login_form"):
            password = st.text_input(
                "Enter access password:", 
                type="password",
                key="login_password"
            )
            submit = st.form_submit_button("Login", type="primary")
            
            if submit:
                authenticate()
        
        st.markdown("---")
        st.caption("ℹ️ Contact your instructor if you've forgotten the password.")
        st.caption("Login persists until you close the browser tab.")
    
    st.stop()
    return False

# -----------------------------------------------------------------------------
# 2. MAIN APPLICATION (Only runs after successful login)
# -----------------------------------------------------------------------------

# This is the main gate - stop if not authenticated
if not check_login():
    st.stop()

# -----------------------------------------------------------------------------
# 3. PAGE CONFIGURATION (For the main app)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="H2 Feynman Bot",
    page_icon="⚛️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 4. HELPER FUNCTIONS (From your original script)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Generates MP3 audio from text with proper LaTeX-to-speech conversion."""
    
    def clean_for_speech(content):
        """Clean text for natural speech with full LaTeX support."""
        # First, extract and preserve code blocks
        content = re.sub(r'```python.*?```', '[PYTHON_CODE]', content, flags=re.DOTALL)
        content = re.sub(r'```.*?```', '[CODE_BLOCK]', content, flags=re.DOTALL)
        
        # Extract and preserve image tags
        content = re.sub(r'\[IMAGE:.*?\]', '[IMAGE]', content)
        
        # Remove markdown formatting (bold, italics) but keep text
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        
        # Convert ALL LaTeX to speech (both inline $...$ and display $$...$$)
        latex_expressions = re.findall(r'\$.*?\$', content)
        for latex_expr in latex_expressions:
            # Convert LaTeX to speech
            spoken_form = latex_to_speech(latex_expr)
            # Replace in content
            content = content.replace(latex_expr, f' {spoken_form} ')
        
        # Also handle display math $$...$$
        display_math = re.findall(r'\$\$.*?\$\$', content, re.DOTALL)
        for math_expr in display_math:
            spoken_form = latex_to_speech(math_expr)
            content = content.replace(math_expr, f' {spoken_form} ')
        
        # Restore placeholders with natural descriptions
        content = content.replace('[PYTHON_CODE]', 'I generated a graph.')
        content = content.replace('[CODE_BLOCK]', '')
        content = content.replace('[IMAGE]', 'Here is a diagram.')
        
        # Final cleanup
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Handle common physics abbreviations
        content = re.sub(r'\bF_([BE])\b', r'F \1', content)
        content = re.sub(r'\bE_([kpt])\b', r'E \1', content)
        content = re.sub(r'\bv_([0-9])\b', r'v \1', content)
        
        return content
    
    try:
        # Clean the text
        clean_text = clean_for_speech(text)
        
        # Generate audio if we have meaningful content
        if len(clean_text) > 10:  # Avoid very short audio
            tts = gTTS(text=clean_text, lang='en', slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            return audio_fp
        return None
    except Exception as e:
        print(f"Audio generation error: {e}")
        return None

def latex_to_speech(text):
    """
    Converts LaTeX mathematical expressions to spoken English.
    Handles fractions, roots, powers, integrals, Greek letters, and common physics notation.
    """
    
    # First, protect text inside \text{} commands
    def protect_text(match):
        return f" TEXTSTART {match.group(1)} TEXTEND "
    
    text = re.sub(r'\\text\{([^}]+)\}', protect_text, text)
    
    # Dictionary of LaTeX to speech mappings
    replacements = [
        # Greek letters (common in physics)
        (r'\\alpha', 'alpha'),
        (r'\\beta', 'beta'),
        (r'\\gamma', 'gamma'),
        (r'\\Gamma', 'capital gamma'),
        (r'\\delta', 'delta'),
        (r'\\Delta', 'capital delta'),
        (r'\\epsilon', 'epsilon'),
        (r'\\varepsilon', 'epsilon'),
        (r'\\zeta', 'zeta'),
        (r'\\eta', 'eta'),
        (r'\\theta', 'theta'),
        (r'\\Theta', 'capital theta'),
        (r'\\vartheta', 'theta'),
        (r'\\iota', 'iota'),
        (r'\\kappa', 'kappa'),
        (r'\\lambda', 'lambda'),
        (r'\\Lambda', 'capital lambda'),
        (r'\\mu', 'mu'),
        (r'\\nu', 'nu'),
        (r'\\xi', 'xi'),
        (r'\\Xi', 'capital xi'),
        (r'\\pi', 'pi'),
        (r'\\Pi', 'capital pi'),
        (r'\\rho', 'rho'),
        (r'\\sigma', 'sigma'),
        (r'\\Sigma', 'capital sigma'),
        (r'\\tau', 'tau'),
        (r'\\phi', 'phi'),
        (r'\\varphi', 'phi'),
        (r'\\Phi', 'capital phi'),
        (r'\\chi', 'chi'),
        (r'\\psi', 'psi'),
        (r'\\Psi', 'capital psi'),
        (r'\\omega', 'omega'),
        (r'\\Omega', 'capital omega'),
        
        # Square roots and roots
        (r'\\sqrt\{([^}]+)\}', r'square root of \1'),
        (r'\\sqrt\[(\d+)\]\{([^}]+)\}', r'\1-th root of \2'),
        
        # Fractions
        (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 over \2'),
        (r'\\dfrac\{([^}]+)\}\{([^}]+)\}', r'\1 over \2'),
        (r'\\tfrac\{([^}]+)\}\{([^}]+)\}', r'\1 over \2'),
        
        # Powers and subscripts
        (r'([a-zA-Zα-ωΑ-Ω])\^\{([^}]+)\}', r'\1 to the power of \2'),
        (r'([a-zA-Zα-ωΑ-Ω])\^(\d+)', r'\1 to the power of \2'),
        (r'([a-zA-Zα-ωΑ-Ω])_\{([^}]+)\}', r'\1 sub \2'),
        (r'([a-zA-Zα-ωΑ-Ω])_([a-zA-Z0-9])', r'\1 sub \2'),
        
        # Common functions
        (r'\\sin', 'sine'),
        (r'\\cos', 'cosine'),
        (r'\\tan', 'tangent'),
        (r'\\cot', 'cotangent'),
        (r'\\sec', 'secant'),
        (r'\\csc', 'cosecant'),
        (r'\\log', 'log'),
        (r'\\ln', 'natural log'),
        (r'\\exp', 'exponential'),
        
        # Integrals and derivatives
        (r'\\int', 'integral'),
        (r'\\iint', 'double integral'),
        (r'\\iiint', 'triple integral'),
        (r'\\oint', 'contour integral'),
        (r'\\partial', 'partial'),
        (r'\\nabla', 'nabla'),
        (r'\\mathrm\{d\}', 'd'),  # for dx, dy, etc
        
        # Common physics operators
        (r'\\vec\{([^}]+)\}', r'\1 vector'),
        (r'\\hat\{([^}]+)\}', r'\1 hat'),
        (r'\\overline\{([^}]+)\}', r'average of \1'),
        (r'\\langle', 'left angle bracket'),
        (r'\\rangle', 'right angle bracket'),
        
        # Limits
        (r'\\lim_\{([^}]+)\}', r'limit as \1'),
        (r'\\sum_\{([^}]+)\}', r'sum over \1'),
        (r'\\prod_\{([^}]+)\}', r'product over \1'),
        
        # Brackets and parentheses
        (r'\\left\(', '('),
        (r'\\right\)', ')'),
        (r'\\left\[', '['),
        (r'\\right\]', ']'),
        (r'\\left\\{', '{'),
        (r'\\right\\}', '}'),
        
        # Common constants
        (r'\\hbar', 'h bar'),
        (r'\\ell', 'script l'),
        
        # Remove remaining LaTeX commands (gentle cleanup)
        (r'\\[a-zA-Z]+', ' '),
        
        # Clean up braces
        (r'\{', ' '),
        (r'\}', ' '),
        
        # Handle special characters
        (r'\^', ' to the power of '),
        (r'_', ' sub '),
        (r'\$', ''),
        
        # Restore protected text
        (r'TEXTSTART ([^T]+) TEXTEND', r'\1'),
    ]
    
    # Apply all replacements
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    
    # Final cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

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
        
        # STEP 1: Extract Python code blocks
        code_blocks = []
        display_content = content
        
        for match in re.finditer(r'```python(.*?)```', content, re.DOTALL):
            code_blocks.append(match.group(1))
            display_content = display_content.replace(match.group(0), "")
        
        # STEP 2: Extract image tags
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE)
        image_query = None
        
        if image_match and role == "assistant":
            image_query = image_match.group(1)
            display_content = display_content.replace(image_match.group(0), "")
        
        # STEP 3: FIXED - Proper regex patterns
        # Fix the problematic pattern that caused the error
        display_content = re.sub(r'u \\\\cos \\\\theta t', r'$u \\cos \\theta$ t', display_content)
        display_content = re.sub(r'u \\\\sin \\\\theta t', r'$u \\sin \\theta$ t', display_content)
        
        # STEP 4: Better approach - Comprehensive LaTeX fix
        # Fix ALL LaTeX patterns systematically
        def fix_broken_latex(text):
            """Fix broken LaTeX formatting."""
            # Pattern 1: Fix raw LaTeX commands (no $)
            # Match \command or \command{...} without $ before or after
            patterns = [
                # Fractions: \frac{1}{2} -> $\frac{1}{2}$
                (r'(?<!\$)\\\\frac\{([^}]+)\}\{([^}]+)\}(?!\$\w)', r'$\\frac{\1}{\2}$'),
                
                # Trigonometric: \cos\theta -> $\cos\theta$
                (r'(?<!\$)\\\\(cos|sin|tan)\s*([a-zA-Zα-ωΑ-Ω]+)(?!\$\w)', r'$\\\1 \2$'),
                
                # Greek letters: \theta -> $\theta$
                (r'(?<!\$)\\\\(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|phi|chi|psi|omega)(?!\$\w)', r'$\\\1$'),
                
                # Subscripts: a_y -> $a_y$
                (r'(?<!\$)([a-zA-Z])_([a-zA-Z0-9])(?!\$\w)', r'$\1_\2$'),
                
                # Powers: t^2 -> $t^2$
                (r'(?<!\$)([a-zA-Z])\^([0-9])(?!\$\w)', r'$\1^{\2}$'),
            ]
            
            for pattern, replacement in patterns:
                text = re.sub(pattern, replacement, text)
            
            return text
        
        # Apply the fix
        display_content = fix_broken_latex(display_content)
        
        # STEP 5: SIMPLE RENDERING - Just use markdown with KaTeX
        # Split into lines to handle each line separately
        lines = display_content.split('\n')
        
        for line in lines:
            if not line.strip():
                st.write("")  # Empty line
                continue
            
            # Check if this line is mostly LaTeX
            latex_count = len(re.findall(r'\$', line))
            if latex_count >= 2:  # Has at least one LaTeX expression
                st.markdown(line, unsafe_allow_html=False)
            else:
                # No LaTeX or minimal - render as is
                st.markdown(line, unsafe_allow_html=False)
        
        # STEP 6: Handle Python code blocks
        if code_blocks and role == "assistant":
            if code_blocks:  # Check if not empty
                execute_plotting_code(code_blocks[0])
            
            with st.expander("📊 Show/Hide Graph Code"):
                for i, code in enumerate(code_blocks):
                    if len(code_blocks) > 1:
                        st.markdown(f"**Code block {i+1}:**")
                    st.code(code, language='python')
        
        # STEP 7: Handle images
        if image_match and role == "assistant" and image_query:
            try:
                image_result = search_image(image_query)
                if image_result and "Error" not in str(image_result):
                    st.image(image_result, caption=f"Diagram: {image_query}")
                    st.markdown(f"[🔗 Open Image in New Tab]({image_result})")
                else:
                    st.warning(f"⚠️ Could not find image for: {image_query}")
            except Exception as e:
                st.warning(f"⚠️ Image search error: {str(e)[:50]}...")
        
        # STEP 8: Handle voice
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            try:
                audio_bytes = generate_audio(display_content)
                if audio_bytes:
                    st.audio(audio_bytes, format='audio/mp3')
            except Exception as e:
                st.error(f"Audio error: {str(e)[:50]}...")
                
# -----------------------------------------------------------------------------
# 5. DEEPSEEK API INTEGRATION
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
        # The key fix: Add a timeout parameter (e.g., 120 seconds)
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise Exception("The request timed out. The server is taking too long to respond.")
    except Exception as e:
        raise Exception(f"DeepSeek API Error: {e}")

# -----------------------------------------------------------------------------
# 6. SYSTEM INSTRUCTIONS
# -----------------------------------------------------------------------------

SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:** Richard Feynman. Tutor for Singapore H2 Physics (9478).

**FORMATTING RULES - CRITICAL:**
1. **MATHEMATICAL EXPRESSIONS - USE DOLLAR SIGNS:**
   - For **inline equations**, you MUST use single dollar signs: `$F = ma$` 
   - For **display equations**, use double dollar signs: `$$E = mc^2$$`
   - **NEVER** use parentheses like ( \vec{E} ) or ( v = E/B )
   - **ALWAYS** use proper LaTeX with $ delimiters: `$\vec{E}$` and `$v = \frac{E}{B}$`

2. **Greek Letters and Vectors:**
   - Electric field: `$\vec{E}$` NOT ( \vec{E} )
   - Velocity: `$v = \frac{E}{B}$` NOT ( v = E/B )
   - Use: `$\alpha$, $\beta$, $\gamma$, $\theta$, $\phi$`


3. **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops.
    * **Format:** Enclose strictly in ` ```python ` blocks.

4. **Diagrams (Web Search):** If you need to show a diagram, YOU MUST USE THE TAG.
    * **Syntax:** `[IMAGE: <concise search query>]`
    * Example: "Here is the setup: [IMAGE: rutherford gold foil experiment diagram]"
    * **Rule:** Do NOT use markdown image links. Use `[IMAGE:...]` ONLY.

**Content Directive:** STRICTLY adhere to the Syllabus SEAB H2 Physics 9478 topics.

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
# 7. MAIN PAGE LAYOUT & SETTINGS
# -----------------------------------------------------------------------------
st.title("⚛️ JPJC H2Physics Feynman Bot (DeepSeek)")

# Add logout button to sidebar
with st.sidebar:
    if st.button("🚪 Logout", use_container_width=True):
        # Clear authentication state
        st.session_state["authenticated"] = False
        if "login_time" in st.session_state:
            del st.session_state["login_time"]
        # Also clear chat history
        if "messages" in st.session_state:
            del st.session_state["messages"]
        st.rerun()

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
# 8. MAIN CHAT LOGIC
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
