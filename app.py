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
# 2. HELPER FUNCTION: PLOT EXECUTOR
# -----------------------------------------------------------------------------
def execute_plotting_code(code_snippet):
    """Executes Python code to generate a Matplotlib plot inside Streamlit."""
    try:
        plt.figure() # Create new figure
        local_env = {'plt': plt, 'np': np}
        exec(code_snippet, {}, local_env)
        st.pyplot(plt)
        plt.clf() # Clear memory
    except Exception as e:
        st.error(f"Graph Error: {e}")

# -----------------------------------------------------------------------------
# 3. SYSTEM INSTRUCTIONS (THE MASTER PROMPT)
# -----------------------------------------------------------------------------
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman. Tutor for Singapore H2 Physics (Syllabus 9478).

**CORE TOOLS & BEHAVIORS:**

1.  **The Visualizer (Two Modes):**
    * **Mode A (Data/Functions):** If the user asks to "Plot", "Graph", or visualize a formula (like Sine waves or Projectile Motion), **WRITE PYTHON CODE**.
        * Use `matplotlib.pyplot` and `numpy`.
        * Enclose strictly in ` ```python ` blocks.
    * **Mode B (Schematics):** If the user asks for a diagram of objects (like a Free Body Diagram, a Circuit, or Lenses), **DRAW ASCII ART**.
        * Use code blocks for alignment.

2.  **The Socratic Guide:**
    * Ask **ONE** simple question at a time.
    * Use analogies (Voltage = Water Pressure).
    * **Do not** solve the math until the student understands the *concept*.

3.  **Vision Capabilities:**
    * If the user uploads an image, analyze it specifically.
    * Identify the forces, components, or circuit parts in the image before explaining.

4.  **The Closure:**
    * When the student understands, provide a **Summary** in a quote block (`>`).

**Syllabus:** SEAB 9478 (Mechanics, Thermal, Waves, Electricity, Modern Physics).
**Math:** Use LaTeX ($F=ma$) for text formulas.
"""

# -----------------------------------------------------------------------------
# 4. SIDEBAR (Settings & Image Upload)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("[https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg](https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg)", width=150)
    st.header("⚙️ Settings")
    
    topic = st.selectbox("Topic:", ["General", "Mechanics", "Waves", "Electricity", "Modern Physics", "Practicals"])
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()

    # --- IMAGE UPLOADER ---
    st.markdown("### 📸 Vision Input")
    uploaded_file = st.file_uploader("Upload a diagram/question", type=["jpg", "png", "jpeg"])
    
    image_part = None
    if uploaded_file:
        image_part = Image.open(uploaded_file)
        st.image(image_part, caption="Image Loaded", use_container_width=True)
        st.success("Ready to analyze!")

    st.divider()
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 5. CHAT LOGIC
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic: **{topic}** | Vision: **{'On' if image_part else 'Off'}** | Graphing: **On**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I can **see** your diagrams, **plot** graphs with code, and **sketch** concepts. What are we solving?"})

# Display History (Text + Rendered Graphs)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Check for previous code graphs
        if "```python" in msg["content"]:
            code_match = re.search(r'```python(.*?)```', msg["content"], re.DOTALL)
            if code_match:
                with st.expander("Show Graph Code"):
                    st.code(code_match.group(1), language='python')
                execute_plotting_code(code_match.group(1))

# Handle Input
if prompt := st.chat_input("Ask a question..."):
    
    # User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("Key missing.")
        st.stop()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=SEAB_H2_MASTER_INSTRUCTIONS
        )
        
        # --- BUILD CONTENT (TEXT + OPTIONAL IMAGE) ---
        # Note: We can't easily put images in "chat history" objects for the API yet,
        # so we send a "fresh" prompt containing the history context + the new image.
        
        # 1. Convert past history to a text block (Context)
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        
        # 2. Prepare the payload
        final_prompt_parts = []
        
        # If there is an image, it goes first
        if image_part:
            final_prompt_parts.append(image_part)
            final_prompt_parts.append(f"analyzing the image above. [Context: {topic}]")
        
        # Add the conversation history + new prompt
        final_prompt_parts.append(f"Conversation History:\n{history_text}\n\nUSER: {prompt}\nASSISTANT:")

        # 3. Generate
        with st.spinner("Thinking..."):
            response = model.generate_content(final_prompt_parts)
        
        # 4. Display Response
        with st.chat_message("assistant"):
            st.markdown(response.text)
            
            # CHECK FOR PYTHON CODE (Graphing)
            if "```python" in response.text:
                code_match = re.search(r'```python(.*?)```', response.text, re.DOTALL)
                if code_match:
                    st.toast("Plotting Graph...", icon="📈")
                    execute_plotting_code(code_match.group(1))
                    
        st.session_state.messages.append({"role": "assistant", "content": response.text})

except Exception as e:
        # --- DIAGNOSTIC MODE ---
        st.error(f"❌ Connection Error: {e}")
        st.warning("🔍 Attempting to list available models for your API Key...")
        
        try:
            st.markdown("### Available Models:")
            found_flash = False
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    st.code(m.name)
                    if "flash" in m.name:
                        found_flash = True
            
            if found_flash:
                st.success("✅ 'Flash' is available! The server just needs the updated requirements.txt.")
            else:
                st.error("⚠️ No 'Flash' model found. Try using 'models/gemini-pro' instead.")
                
        except Exception as debug_err:
            st.error(f"Could not list models. Check your API Key permissions. ({debug_err})")
