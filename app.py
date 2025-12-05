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
# 3. SYSTEM INSTRUCTIONS
# -----------------------------------------------------------------------------
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman. Tutor for Singapore H2 Physics (Syllabus 9478).

**CORE TOOLS:**
1.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops.
    * **Format:** Enclose strictly in ` ```python ` blocks.

2.  **Sketching (ASCII):** For diagrams (forces, circuits), use ASCII art in code blocks.

3.  **Multimodal Vision & Audio:** * **Vision:** Analyze uploaded images/PDFs.
    * **Audio:** If the user speaks, transcribe the physics question internally and answer it.

**PEDAGOGY (SOCRATIC):**
* Ask **ONE** simple question at a time.
* Use analogies first.
* **Do not** solve the math immediately. Guide the student.
* **Summary:** When they understand, provide a summary in a blockquote (`>`).

**Math:** Use LaTeX ($F=ma$) for formulas.
"""

# -----------------------------------------------------------------------------
# 4. SIDEBAR (TRIPLE INPUT)
# -----------------------------------------------------------------------------
with st.sidebar:
    # --- FIX 1: CLEAN URL (No Markdown brackets) ---
    st.image("[https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg](https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg)", width=150)
    
    st.header("⚙️ Settings")
    topic = st.selectbox("Topic:", ["General", "Mechanics", "Waves", "Electricity", "Modern Physics", "Practicals"])
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    # --- MULTIMODAL INPUTS ---
    st.markdown("### 📸 Vision & 🎙️ Voice")
    
    tab_upload, tab_cam, tab_mic = st.tabs(["📂 File", "📷 Cam", "🎙️ Voice"])
    
    visual_content = None
    audio_content = None
    
    # Tab 1: File Uploader
    with tab_upload:
        uploaded_file = st.file_uploader("Upload Image/PDF", type=["jpg", "png", "jpeg", "pdf"])
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                visual_content = {"mime_type": "application/pdf", "data": uploaded_file.getvalue()}
                st.success(f"📄 PDF: {uploaded_file.name}")
            else:
                image = Image.open(uploaded_file)
                st.image(image, caption="Image Loaded", use_container_width=True)
                visual_content = image

    # Tab 2: Camera
    with tab_cam:
        camera_photo = st.camera_input("Take a photo")
        if camera_photo:
            image = Image.open(camera_photo)
            visual_content = image
            st.image(image, caption="Camera Photo", use_container_width=True)

    # Tab 3: Microphone
    with tab_mic:
        voice_recording = st.audio_input("Record a question")
        if voice_recording:
            audio_content = {"mime_type": "audio/wav", "data": voice_recording.read()} 
            st.audio(voice_recording)
            st.success("Audio captured!")

    st.divider()
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 5. MAIN CHAT LOGIC
# -----------------------------------------------------------------------------
mode_label = "Text"
if visual_content: mode_label = "Vision"
if audio_content: mode_label = "Voice"

st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic: **{topic}** | Mode: **{mode_label}**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I can **see** (images/PDFs), **hear** your questions (Voice), and **plot graphs**. How can I help?"})

for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"])

# Allow empty text prompt IF there is audio or image
user_input = st.chat_input("Type OR Record/Upload...")

# Trigger if user typed text OR uploaded media/audio
if user_input or audio_content or visual_content:
    
    user_display_text = user_input if user_input else ""
    if audio_content and not user_input: user_display_text = "🎤 *(Sent Audio Message)*"
    elif visual_content and not user_input: user_display_text = "📸 *(Sent Image/PDF)*"
    
    if user_display_text:
        st.session_state.messages.append({"role": "user", "content": user_display_text})
        with st.chat_message("user"):
            st.markdown(user_display_text)

    if not api_key:
        st.error("Key missing.")
        st.stop()

    # --- GENERATION LOGIC ---
    try:
        genai.configure(api_key=api_key)
        
        # --- MODEL SELECTION ---
        model_name = "gemini-2.5-flash" 
        
        model = genai.GenerativeModel(
            model_name=model_name, 
            system_instruction=SEAB_H2_MASTER_INSTRUCTIONS
        )
        
        # Build Context
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        final_prompt = []
        
        # 1. Add Visuals
        if visual_content:
            final_prompt.append(visual_content)
            final_prompt.append(f"Analyze this image/document. [Context: {topic}]")
            
        # 2. Add Audio
        if audio_content:
            final_prompt.append(audio_content)
            final_prompt.append(f"Listen to this student's question about {topic}. Respond textually.")

        # 3. Add Text
        if user_input:
            final_prompt.append(f"USER TEXT: {user_input}")

        final_prompt.append(f"Conversation History:\n{history_text}\n\nASSISTANT:")

        with st.spinner("Processing..."):
            response = model.generate_content(final_prompt)
        
        display_message("assistant", response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        # --- FIX 2: DIAGNOSTIC MODE RESTORED ---
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
