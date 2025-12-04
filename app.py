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
# 2. SYSTEM INSTRUCTIONS (SEAB H2 SYLLABUS)
# -----------------------------------------------------------------------------
SEAB_H2_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman, the Nobel Prize-winning physicist, acting as a supportive but rigorous tutor for the **Singapore GCE A-Level H2 Physics (Syllabus 9478)**.

**Your Goal:**
Help the student build deep conceptual intuition while strictly adhering to the SEAB 9478 requirements.

**OPERATIONAL RULES:**
1.  **The "Explain Like I'm 5" (ELI5) Protocol:**
    * Start with a real-world analogy (e.g., Voltage as "water pressure").
    * ONLY introduce technical jargon *after* the concept is understood.

2.  **The "Test Me" (Feynman Technique) Protocol:**
    * If the student asks to be tested, DO NOT give a multiple-choice quiz.
    * Ask them to explain a concept back to you.
    * Critique their explanation: "You used the word 'momentum' but I don't think you know what it means. Try again without that word."

3.  **SEAB 9478 SYLLABUS SPECIFICS:**
    * **Math Level:** Use standard H2 Physics notation. 
    * **Topics:** Newtonian Mechanics, Thermal Physics, Waves, Electricity & Magnetism, Modern Physics (Quantum/Nuclear).
    * **Practicals:** Emphasize Excel skills for Paper 4 and linearization of graphs ($y = mx + c$).

4.  **Formatting:**
    * Use LaTeX for ALL math. Inline: $F=ma$. Block: $$E = mc^2$$.
    * Keep answers concise and conversational.
"""

# -----------------------------------------------------------------------------
# 3. SIDEBAR (Settings & Picture)
# -----------------------------------------------------------------------------
with st.sidebar:
    # --- FEYNMAN PICTURE ---
    st.image(
        "https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", 
        caption="\"I think I can safely say that nobody understands quantum mechanics.\"",
        use_container_width=True
    )
    
    st.header("⚙️ Settings")
    
    # Topic Selector
    topic = st.selectbox(
        "Current Revision Topic:",
        ["General / Any", "Measurement", "Kinematics & Dynamics", "Forces", 
         "Work & Energy", "Waves & Superposition", "Electricity & DC Circuits", 
         "Electromagnetism (EMI)", "Modern Physics", "Practicals (Paper 4)"]
    )
    
    # API Key Handling
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    # Clear Chat Button
    if st.button("🧹 Start New Topic", type="primary"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 4. CHAT LOGIC
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic Focus: **{topic}** | Mode: **Explain & Test**")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add an initial greeting from Feynman
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! I'm ready to talk physics. We can discuss **concepts**, or I can **test your understanding**. What's confusing you today?"
    })

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- SUGGESTED QUESTIONS (Quick Click Buttons) ---
# Only show these if the chat is empty (or just the greeting)
if len(st.session_state.messages) < 2:
    st.markdown("### Suggested Questions:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌊 Explain Superposition"):
            st.session_state.messages.append({"role": "user", "content": "Explain the Principle of Superposition like I'm 12."})
            st.rerun()
    with col2:
        if st.button("🧠 Test me on Quantum"):
            st.session_state.messages.append({"role": "user", "content": "Test my understanding of the Photoelectric Effect. Ask me a hard conceptual question."})
            st.rerun()

# --- CHAT INPUT ---
if prompt := st.chat_input("Type here... (e.g., 'Why is the sky blue?' or 'Test me')"):
    
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Check API Key
    if not api_key:
        st.error("Please provide an API Key in the sidebar.")
        st.stop()

    # 3. Generate Response
    try:
        genai.configure(api_key=api_key)
        
        # NOTE: Using 'gemini-1.5-flash' as it is the standard stable version.
        # If 'gemini-2.5-flash' worked for you, feel free to change it below.
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=SEAB_H2_INSTRUCTIONS
        )
        
        # Create history format for API
        history_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            history_api.append({"role": role, "parts": [m["content"]]})

        # Start Chat (exclude the last message which is the new prompt)
        chat = model.start_chat(history=history_api[:-1])
        
        # Inject Context (Invisible to user, helpful for AI)
        context_prompt = f"[Context: Student is studying {topic}. Strict adherence to SEAB 9478.]\n\n{prompt}"
        
        response = chat.send_message(context_prompt)
        
        # Display AI Response
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
