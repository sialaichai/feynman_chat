import streamlit as st
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import re
from PIL import Image

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

def display_message(role, content):
    """Parses message content to hide Python code behind an expander."""
    with st.chat_message(role):
        code_match = re.search(r'```python(.*?)```', content, re.DOTALL)
        if code_match and role == "assistant":
            python_code = code_match.group(1)
            text_without_code = content.replace(code_match.group(0), "")
            st.markdown(text_without_code)
            
            with st.expander("Show Graph Code (Python)"):
                st.code(python_code, language='python')
            execute_plotting_code(python_code)
        else:
            st.markdown(content)

# -----------------------------------------------------------------------------
# 3. SYSTEM INSTRUCTIONS (ROBUST + SCIPY FIX)
# -----------------------------------------------------------------------------
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman. Tutor for Singapore H2 Physics (Syllabus 9478).

**CORE TOOLS:**
1.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops to avoid index errors.
    * **Format:** Enclose strictly in ` ```python ` blocks.

2.  **Sketching (ASCII):** For diagrams (forces, circuits), use ASCII art in code blocks.

3.  **Vision:** Analyze uploaded images or camera photos if provided.

**PEDAGOGY (SOCRATIC):**
* Ask **ONE** simple question at a time.
* Use analogies first (e.g., Voltage = Pressure).
* **Do not** solve the math immediately. Guide the student.
* **Summary:** When they understand, provide a summary in a blockquote (`>`).

**Math:** Use LaTeX ($F=ma$) for formulas.
"""

# -----------------------------------------------------------------------------
# 4. SIDEBAR (WITH CAMERA & UPLOAD TABS)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg(https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg)", width=150)
    st.header("⚙️ Settings")
    topic = st.selectbox("Topic:", ["General", "Mechanics", "Waves", "Electricity", "Modern Physics", "Practicals"])
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
# --- DUAL INPUT MODE (Tabs) ---
    st.markdown("### 📸 Vision & Docs")
    
    tab_upload, tab_cam = st.tabs(["📂 File", "📷 Camera"])
    
    # We rename 'image_part' to 'visual_content' to reflect it can be a PDF too
    visual_content = None
    
    # Tab 1: File Uploader (Updated for PDF)
    with tab_upload:
        uploaded_file = st.file_uploader("Upload Image or PDF", type=["jpg", "png", "jpeg", "pdf"])
        
        if uploaded_file:
            # CHECK FILE TYPE
            if uploaded_file.type == "application/pdf":
                # PDF HANDLING: Read bytes and create a dictionary for Gemini
                visual_content = {
                    "mime_type": "application/pdf",
                    "data": uploaded_file.getvalue()
                }
                st.success(f"📄 PDF Loaded: {uploaded_file.name}")
            else:
                # IMAGE HANDLING: Use PIL
                image = Image.open(uploaded_file)
                st.image(image, caption="Image Loaded", use_container_width=True)
                visual_content = image

    # Tab 2: Camera Input (Images only)
    with tab_cam:
        camera_photo = st.camera_input("Take a photo")
        if camera_photo:
            image = Image.open(camera_photo)
            visual_content = image
            st.image(image, caption="Camera Photo", use_container_width=True)

    # Display the final selected image (from either source)
    if image_part:
        st.success("Image acquired!")
        st.image(image_part, caption="Ready to Analyze", use_container_width=True)

    st.divider()
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 5. MAIN CHAT LOGIC
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic: **{topic}** | Vision: **{'Active' if image_part else 'Inactive'}**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I can **see** diagrams (upload or snap a photo), **plot graphs**, and help you master physics. What's the problem?"})

for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"])

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("Key missing.")
        st.stop()

try:
        genai.configure(api_key=api_key)
        
        # 1. Define Model
        model_name = "gemini-1.5-flash" 
        model = genai.GenerativeModel(
            model_name=model_name, 
            system_instruction=SEAB_H2_MASTER_INSTRUCTIONS
        )
        
        # 2. Build Prompt
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        final_prompt = []
        
        # ATTACH CONTENT (Image OR PDF)
        if visual_content:
            final_prompt.append(visual_content) # API handles both PIL Images and PDF dictionaries
            final_prompt.append(f"analyzing this document/image. [Context: {topic}]")
        
        final_prompt.append(f"Conversation History:\n{history_text}\n\nUSER: {prompt}\nASSISTANT:")

        # 3. Generate
        with st.spinner("Thinking..."):
            response = model.generate_content(final_prompt)
        
        display_message("assistant", response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
            # --- DIAGNOSTIC MODE ---
            st.error(f"❌ Error: {e}")
            
            # If it's a 404 or Invalid Argument, we check the models
            if "404" in str(e) or "not found" in str(e).lower():
                st.warning(f"⚠️ Model '{model_name}' not found. Listing available models for your Key...")
                try:
                    available_models = []
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                    
                    if available_models:
                        st.success(f"✅ Your API Key has access to these models:")
                        st.code("\n".join(available_models))
                        st.info("Update the 'model_name' variable in app.py to one of these!")
                    else:
                        st.error("❌ Your API Key has NO access to content generation models. Check Google AI Studio settings.")
                except Exception as inner_e:
                    st.error(f"Could not list models: {inner_e}")
