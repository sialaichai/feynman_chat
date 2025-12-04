import streamlit as st
import google.generativeai as genai

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="H2 Physics Feynman Bot by SiaLC",
    page_icon="⚛️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. SYSTEM INSTRUCTIONS (SOCRATIC MODE)
# -----------------------------------------------------------------------------
SEAB_H2_SOCRATIC_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman, the Nobel Prize-winning physicist. You are tutoring a student in Singapore GCE A-Level H2 Physics (Syllabus 9478).

**CORE DIRECTIVE: SOCRATIC METHOD (GUIDE, DON'T TELL)**
1.  **NEVER give the final answer immediately.**
2.  When a student asks a question, break it down into small steps.
3.  Ask the student a leading question to help them figure out the first step.
    * *Example:* If asked "How do I find the velocity?", reply: "Well, what energy changes are happening here? Is Potential Energy turning into something else?"
4.  **Wait for their response** before moving to the next step.
5.  If they get it wrong, gently correct the specific misconception and ask them to try that step again.

**Operational Rules:**
* **Tone:** Encouraging, curious, patient. "Let's think about this...", "Imagine you are standing on the electron..."
* **Syllabus:** Stick strictly to SEAB 9478 (Mechanics, Fields, Waves, Thermal, Quantum).
* **Math:** Use LaTeX for formulas ($F=ma$).
* **The "I Give Up" Clause:** Only provide the full solution if the student explicitly says "I give up" or "Just tell me the answer."

**Handling Specific Topics:**
* **Mechanics:** Ask them to describe the Free Body Diagram before doing math.
* **Fields:** Ask them to visualize the field lines first.
* **Practicals:** Ask them "What would be the independent variable here?" before designing the experiment.
"""

# -----------------------------------------------------------------------------
# 3. SIDEBAR (Settings & Picture)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", 
        caption="\"I would rather have questions that can't be answered than answers that can't be questioned.\"",
        use_container_width=True
    )
    
    st.header("⚙️ Settings")
    
    topic = st.selectbox(
        "Current Topic:",
        ["General / Any", "Measurement", "Kinematics & Dynamics", "Forces", 
         "Work & Energy", "Waves & Superposition", "Electricity & DC Circuits", 
         "Electromagnetism (EMI)", "Modern Physics", "Practicals (Paper 4)"]
    )
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    if st.button("🧹 Start New Topic", type="primary"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 4. CHAT LOGIC
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")
st.caption(f"Topic: **{topic}** | Style: **Socratic (Guided Learning)**")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! I'm ready to help you *understand* physics, not just memorize it. What problem are we looking at?"
    })

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- SUGGESTED QUESTIONS ---
if len(st.session_state.messages) < 2:
    st.markdown("### Try asking:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Help me solve a projectile problem"):
            st.session_state.messages.append({"role": "user", "content": "I'm stuck on a projectile motion question. A ball is thrown at 30 degrees."})
            st.rerun()
    with col2:
        if st.button("🤔 I don't get Lenz's Law"):
            st.session_state.messages.append({"role": "user", "content": "I don't understand Lenz's Law. Why is there a minus sign?"})
            st.rerun()

# --- CHAT INPUT ---
if prompt := st.chat_input("Type your question here..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("Please provide an API Key in the sidebar.")
        st.stop()

    try:
        genai.configure(api_key=api_key)
        
        # Using Flash for speed, but instructions enforce slow pacing
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=SEAB_H2_SOCRATIC_INSTRUCTIONS
        )
        
        history_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            history_api.append({"role": role, "parts": [m["content"]]})

        chat = model.start_chat(history=history_api[:-1])
        
        # Context Injection
        context_prompt = f"[Context: Student is studying {topic}. Do NOT give the answer. Guide them step-by-step.]\n\n{prompt}"
        
        response = chat.send_message(context_prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
