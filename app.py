import streamlit as st
import google.generativeai as genai

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="H2 Physics Feynman Bot",
    page_icon="⚛️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. THE BRAIN: SYSTEM INSTRUCTIONS (SEAB 9478 SYLLABUS EDITION)
# -----------------------------------------------------------------------------
SEAB_H2_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman, the Nobel Prize-winning physicist, acting as a supportive but rigorous tutor for the **Singapore GCE A-Level H2 Physics (Syllabus 9478, 2026 onwards)**.

**Your Goal:**
Help the student build deep conceptual intuition while strictly adhering to the SEAB 9478 requirements.

**OPERATIONAL RULES:**
1.  **The "Explain Like I'm 5" (ELI5) Protocol:**
    * Start with a real-world analogy.
    * ONLY introduce technical jargon *after* the concept is understood.

2.  **The "Test Me" (Feynman Technique) Protocol:**
    * If the student asks to be tested, DO NOT give a multiple-choice quiz.
    * Ask them to explain a concept back to you.
    * Critique their explanation gently.

3.  **SEAB 9478 SYLLABUS SPECIFICS:**
    * **Math Level:** Use standard H2 Physics notation. Calculus ($dy/dx$) is allowed for definitions but focus on algebra for solving.
    * **Topics:** Newtonian Mechanics, Thermal Physics, Waves, Electricity & Magnetism, Modern Physics.
    * **Practicals:** If asked, emphasize Excel skills for Paper 4 and linearization of graphs.

4.  **Formatting:**
    * Use LaTeX for ALL math. Inline: $F=ma$. Block: $$E = mc^2$$.
"""

# -----------------------------------------------------------------------------
# 3. SIDEBAR & SETTINGS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=150, caption="Prof. Feynman")
    st.title("Settings")
    
    topic = st.selectbox(
        "Current Revision Topic:",
        ["General / Any", "Measurement", "Kinematics", "Forces", "Energy", 
         "Waves", "Electricity", "Electromagnetism", "Modern Physics", "Practicals"]
    )
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    if st.button("🧹 Start New Topic", type="primary"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 4. CHAT LOGIC (Using Standard Library)
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")
st.markdown(f"**Focus:** `{topic}`")

if "messages" not in st.session_state:
    st.session_state.messages = []
    # Note: The standard library handles system instructions differently, 
    # so we don't add it to the message history list here.

# Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle Input
if prompt := st.chat_input("Ask about a concept..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if api_key:
        try:
            # --- STANDARD LIBRARY SETUP ---
            genai.configure(api_key=api_key)
            
            # Create Model with System Instruction
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",  # Using Flash (Fast & Reliable)
                system_instruction=SEAB_H2_INSTRUCTIONS
            )
            
            # Build Context String
            final_prompt = f"[CONTEXT: Student is revising '{topic}'. Adhere to SEAB 9478 syllabus.]\n\nUser Question: {prompt}"
            
            # Create Chat Object (History is managed manually for display, 
            # but we pass the full context here for simplicity or maintain a chat object)
            
            # Ideally, we convert session_state to the format the API expects,
            # but for a simple Q&A bot, sending the prompt with instructions works well.
            # To keep history context, we use start_chat:
            
            history_for_api = []
            for msg in st.session_state.messages:
                # Map 'assistant' to 'model' for the API
                role = "model" if msg["role"] == "assistant" else "user"
                history_for_api.append({"role": role, "parts": [msg["content"]]})
            
            chat = model.start_chat(history=history_for_api[:-1]) # Load history excluding latest prompt
            response = chat.send_message(final_prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("Please provide an API Key in the sidebar.")
