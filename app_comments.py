# --- IMPORTS ---
# These are the "tools" we grab from the toolbox before we start building.
import streamlit as st                  # The framework that creates the website/app
import google.generativeai as genai     # The library that talks to Google's AI models
import matplotlib.pyplot as plt         # A library for drawing graphs (math plotting)
import numpy as np                      # A library for heavy math calculations (used by graphs)
import re                               # "Regular Expressions" - a tool to find patterns in text
from PIL import Image                   # "Pillow" - a library to open and manipulate images

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
# This must be the very first Streamlit command. It sets the browser tab title and icon.
st.set_page_config(
    page_title="H2 Feynman Bot",
    page_icon="⚛️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS (Custom tools we build)
# -----------------------------------------------------------------------------

def execute_plotting_code(code_snippet):
    """
    This function takes a string of Python code (written by the AI), 
    runs it, and displays the resulting graph.
    """
    try:
        # Create a new blank figure so we don't draw on top of old graphs
        plt.figure()
        
        # 'local_env' is a safe sandbox. We give the code access to 'plt' and 'np' only.
        local_env = {'plt': plt, 'np': np}
        
        # 'exec' runs the string as if it were python code
        exec(code_snippet, {}, local_env)
        
        # Show the plot in the Streamlit app
        st.pyplot(plt)
        
        # Clean up memory
        plt.clf()
    except Exception as e:
        # If the AI wrote bad code, show a red error box instead of crashing
        st.error(f"Graph Error: {e}")

def display_message(role, content):
    """
    This function handles showing messages in the chat.
    It is smart: it checks if the message contains hidden Python code.
    """
    with st.chat_message(role):
        # We use Regex (re) to look for text inside ```python ... ``` blocks.
        # re.DOTALL means "look across multiple lines"
        code_match = re.search(r'```python(.*?)```', content, re.DOTALL)
        
        # If we find code AND the message is from the Assistant (the AI):
        if code_match and role == "assistant":
            # 1. Extract just the code part
            python_code = code_match.group(1)
            
            # 2. Remove the raw code from the text so the user doesn't see it twice
            text_without_code = content.replace(code_match.group(0), "")
            st.markdown(text_without_code)
            
            # 3. Put the code inside a collapsible box (Expander) to keep UI clean
            with st.expander("Show Graph Code (Python)"):
                st.code(python_code, language='python')
            
            # 4. Run the code to draw the graph
            execute_plotting_code(python_code)
        else:
            # If no code is found, just show the text normally
            st.markdown(content)

# -----------------------------------------------------------------------------
# 3. SYSTEM INSTRUCTIONS (The "Brain")
# -----------------------------------------------------------------------------
# This variable holds the "Personality" of the chatbot. 
# We send this to Google first so the AI knows how to behave.
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman. Tutor for Singapore H2 Physics (Syllabus 9478).

**CORE TOOLS:**
1.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE.
    * **Libraries:** Use ONLY `matplotlib.pyplot`, `numpy`, and `scipy`.
    * **CRITICAL RULE:** Use **Vectorized Operations** (e.g., `y = np.sin(x)`) instead of `for` loops to avoid index errors.
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
# 4. SIDEBAR (Settings & Inputs)
# -----------------------------------------------------------------------------
with st.sidebar:
    # Display the Feynman picture. Note: We use a clean URL string here.
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg(https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg)", width=150)
    
    st.header("⚙️ Settings")
    
    # Dropdown menu to set the context
    topic = st.selectbox("Topic:", ["General", "Mechanics", "Waves", "Electricity", "Modern Physics", "Practicals"])
    
    # Retrieve the API Key from Streamlit Secrets (secure storage)
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        # Fallback: Ask user to type it if not found in secrets
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    # --- MULTIMODAL INPUTS ---
    st.markdown("### 📸 Vision & 🎙️ Voice")
    
    # Create 3 tabs for different input methods to keep the UI clean
    tab_upload, tab_cam, tab_mic = st.tabs(["📂 File", "📷 Cam", "🎙️ Voice"])
    
    # Initialize variables to None (empty) so the code doesn't break if tabs aren't used
    visual_content = None
    audio_content = None
    
    # Tab 1: Uploading Files (Images or PDFs)
    with tab_upload:
        uploaded_file = st.file_uploader("Upload Image/PDF", type=["jpg", "png", "jpeg", "pdf"])
        if uploaded_file:
            # PDFs and Images are handled differently by the Gemini API
            if uploaded_file.type == "application/pdf":
                # For PDFs, we read the raw data bytes
                visual_content = {"mime_type": "application/pdf", "data": uploaded_file.getvalue()}
                st.success(f"📄 PDF: {uploaded_file.name}")
            else:
                # For Images, we open them with PIL so we can display them
                image = Image.open(uploaded_file)
                st.image(image, caption="Image Loaded", use_container_width=True)
                visual_content = image

    # Tab 2: Using the Webcam/Phone Camera
    with tab_cam:
        camera_photo = st.camera_input("Take a photo")
        if camera_photo:
            image = Image.open(camera_photo)
            visual_content = image
            st.image(image, caption="Camera Photo", use_container_width=True)

    # Tab 3: Recording Audio
    with tab_mic:
        voice_recording = st.audio_input("Record a question")
        if voice_recording:
            # We package the audio bytes to send to Gemini
            audio_content = {"mime_type": "audio/wav", "data": voice_recording.read()} 
            st.audio(voice_recording) # Playback for user confirmation
            st.success("Audio captured!")

    # Reset Button
    st.divider()
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = [] # Wipe memory
        st.rerun() # Refresh app

# -----------------------------------------------------------------------------
# 5. MAIN CHAT LOGIC
# -----------------------------------------------------------------------------

# Dynamic title based on what mode we are in
mode_label = "Text"
if visual_content: mode_label = "Vision"
if audio_content: mode_label = "Voice"

st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic: **{topic}** | Mode: **{mode_label}**")

# Initialize Chat History in Session State
# This acts as the "Short Term Memory" of the app.
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add a welcome message from the bot
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I can **see** (images/PDFs), **hear** your questions (Voice), and **plot graphs**. How can I help?"})

# Loop through history and display past messages
# We use our custom 'display_message' function to ensure graphs render correctly
for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"])

# Text Input Box
# We allow this to be empty IF the user provided audio or an image
user_input = st.chat_input("Type OR Record/Upload...")

# CHECK: Did the user do anything? (Type text OR upload image OR record audio)
if user_input or audio_content or visual_content:
    
    # Figure out what to show in the chat log
    user_display_text = user_input if user_input else ""
    if audio_content and not user_input: user_display_text = "🎤 *(Sent Audio Message)*"
    elif visual_content and not user_input: user_display_text = "📸 *(Sent Image/PDF)*"
    
    # Display the user's action in the chat
    if user_display_text:
        st.session_state.messages.append({"role": "user", "content": user_display_text})
        with st.chat_message("user"):
            st.markdown(user_display_text)

    # Stop here if no API Key provided
    if not api_key:
        st.error("Key missing.")
        st.stop()

    # --- START GENERATION ---
    try:
        # Authenticate with Google
        genai.configure(api_key=api_key)
        
        # Load the Model (Using 2.5 Flash as requested)
        model_name = "gemini-2.5-flash" 
        
        # Initialize the model with our Feynman instructions
        model = genai.GenerativeModel(
            model_name=model_name, 
            system_instruction=SEAB_H2_MASTER_INSTRUCTIONS
        )
        
        # --- CONTEXT BUILDING ---
        # We need to turn the chat history list into a single string so the AI remembers context.
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        
        # Construct the final package to send to Google
        final_prompt = []
        
        # 1. Add Visuals (if any) - These must go first in the list
        if visual_content:
            final_prompt.append(visual_content)
            final_prompt.append(f"Analyze this image/document. [Context: {topic}]")
            
        # 2. Add Audio (if any)
        if audio_content:
            final_prompt.append(audio_content)
            final_prompt.append(f"Listen to this student's question about {topic}. Respond textually.")

        # 3. Add Text (if any)
        if user_input:
            final_prompt.append(f"USER TEXT: {user_input}")

        # 4. Add the history so it remembers previous turns
        final_prompt.append(f"Conversation History:\n{history_text}\n\nASSISTANT:")

        # Show a "Thinking..." spinner while waiting for Google
        with st.spinner("Processing..."):
            response = model.generate_content(final_prompt)
        
        # Display the AI's response using our helper function (handles graphs)
        display_message("assistant", response.text)
        
        # Save the response to memory
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        # --- ERROR HANDLING ---
        st.error(f"❌ Error: {e}")
        
        # Specific help for "404" errors (Model not found)
        if "404" in str(e) or "not found" in str(e).lower() or "not supported" in str(e).lower():
            st.warning(f"⚠️ Model '{model_name}' failed. Listing available models for your API Key...")
            try:
                # Ask Google: "Which models can I use?"
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                
                # Show the valid list to the user
                if available_models:
                    st.success(f"✅ Your Key works! Available models:")
                    st.code("\n".join(available_models))
                    st.info("Update 'model_name' in line 165 of app.py to one of these.")
                else:
                    st.error("❌ Your API Key has NO access to content generation models.")
            except Exception as inner_e:
                st.error(f"Could not list models: {inner_e}")
