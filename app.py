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
        plt.figure() # Create new figure
        local_env = {'plt': plt, 'np': np}
        exec(code_snippet, {}, local_env)
        st.pyplot(plt)
        plt.clf() # Clear memory
    except Exception as e:
        st.error(f"Graph Error: {e}")

def display_message(role, content):
    """
    Parses message content. 
    If Python code is found: Hides it in an expander, renders text, then runs code.
    If no code: Just renders text.
    """
    with st.chat_message(role):
        # Regex to find ```python ... ``` blocks
        code_match = re.search(r'```python(.*?)```', content, re.DOTALL)
        
        if code_match and role == "assistant":
            # 1. Extract the code
            python_code = code_match.group(1)
            
            # 2. Remove the raw code block from the text so it isn't shown twice
            # We replace the code block with a small note or empty string
            text_without_code = content.replace(code_match.group(0), "")
            st.markdown(text_without_code)
            
            # 3. Show the code inside a collapsed expander
            with st.expander("Show Graph Code (Python)"):
                st.code(python_code, language='python')
            
            # 4. Execute and display the graph
            execute_plotting_code(python_code)
        else:
            # Standard text message
            st.markdown(content)

# -----------------------------------------------------------------------------
# 3. SYSTEM INSTRUCTIONS
# -----------------------------------------------------------------------------
SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman. Tutor for Singapore H2 Physics (Syllabus 9478).

**CORE TOOLS:**
1.  **Graphing (Python):** If asked to plot/graph, WRITE PYTHON CODE using `matplotlib` and `numpy`. Enclose strictly in ` ```python ` blocks.
2.  **Sketching (ASCII):** For diagrams (forces, circuits), use ASCII art in code blocks.
3.  **Vision:** Analyze uploaded images if provided.

**PEDAGOGY (SOCRATIC):**
* Ask **ONE** simple question at a time.
* Use analogies first (e.g., Voltage = Pressure).
* **Do not** solve the math immediately. Guide the student.
* **Summary:** When they understand, provide a summary in a blockquote (`>`).

**Math:** Use LaTeX ($F=ma$) for formulas.
"""

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    # Fixed URL (Removed Markdown brackets to prevent crash)
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=150)
    st.header("⚙️ Settings")
    
    topic = st.selectbox("Topic:", ["General", "Mechanics", "Waves", "Electricity", "Modern Physics", "Practicals"])
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()

    st.markdown("### 📸 Vision Input")
    uploaded_file = st.file_uploader("Upload a diagram/question", type=["jpg", "png", "jpeg"])
    
    image_part = None
    if uploaded_file:
        image_part = Image.open(uploaded_file)
        st.image(image_part, caption="Image Loaded", use_container_width=True)

    st.divider()
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 5. MAIN CHAT LOGIC
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic: **{topic}** | Vision: **{'On' if image_part else 'Off'}**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I can **plot graphs**, see diagrams, and help you understand physics deeply. What's on your mind?"})

# --- DISPLAY HISTORY (Using the new cleaner function) ---
for msg in st.session_state.messages:
    display_message(msg["role"], msg["content"])

# --- HANDLE INPUT ---
if prompt := st.chat_input("Ask a question..."):
    
    # Show User Message
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
        
        # Prepare Context
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        
        final_prompt_parts = []
        if image_part:
            final_prompt_parts.append(image_part)
            final_prompt_parts.append(f"analyzing the image. [Context: {topic}]")
        
        final_prompt_parts.append(f"Conversation History:\n{history_text}\n\nUSER: {prompt}\nASSISTANT:")

        # Generate
        with st.spinner("Thinking..."):
            response = model.generate_content(final_prompt_parts)
        
        # Display Assistant Message (Using the new cleaner function)
        display_message("assistant", response.text)
                    
        # Save to history
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
