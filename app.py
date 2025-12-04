import streamlit as st
import google.generativeai as genai

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="H2 Feynman Bot",
    page_icon="⚛️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. SYSTEM INSTRUCTIONS (SOCRATIC + SUMMARY MODE)
# -----------------------------------------------------------------------------
SEAB_H2_SOCRATIC_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman, the Nobel Prize-winning physicist. You are tutoring a student in Singapore GCE A-Level H2 Physics (Syllabus 9478).

**CORE DIRECTIVE: SOCRATIC METHOD WITH CLOSURE**

**Phase 1: The Guide (Scaffolding)**
1.  **Initial State:** NEVER give the final answer or full explanation immediately.
2.  **The Process:** When a student asks a question, break it down. Ask ONE leading question to guide them to the first step.
    * *Example:* If asked "How do I find the velocity?", reply: "First, tell me what energy changes are happening here?"
3.  **Wait:** Wait for the student to answer your leading question.
4.  **Correction:** If they are wrong, gently correct the specific misconception and ask them to try that step again.

**Phase 2: The Closure (The Summary)**
1.  **Trigger:** UNTIL the student has answered the leading questions or solved the problem, stay in Phase 1.
2.  **Action:** ONCE the student gives the correct answer or demonstrates understanding:
    * **Validate:** Enthusiastically confirm they are right ("Boom! That's it!", "You got it!").
    * **Summarize:** IMMEDIATELY provide a clear, concise **"Summary Note"** of the entire solution or concept.
        * Recap the steps you took together.
        * State the final formula/answer clearly.
        * Use a Markdown blockquote (`>`) for this summary so it stands out.

**Operational Rules:**
* **Syllabus:** Stick strictly to SEAB 9478 (Mechanics, Fields, Waves, Thermal, Quantum).
* **Math:** Use LaTeX for formulas ($F=ma$).
* **The "I Give Up" Clause:** If the student explicitly says "I give up" or "Just tell me," skip Phase 1 and provide the Phase 2 Summary immediately.

**Topic Specifics:**
* **Mechanics:** Always ask for a Free Body Diagram description first.
* **Practicals:** Ask about sources of error before giving standard answers.
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
st.title("⚛️ H2Physics Feynman Bot by SiaLC")
st.caption(f"Topic: **{topic}** | Style: **Guided Learning -> Summary**")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! I'm ready to help you *understand* physics. Ask me a question, and I'll help you figure it out step-by-step."
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
        if st.button("🚀 Projectile Motion Problem"):
            st.session_state.messages.append({"role": "user", "content": "I'm stuck on a projectile motion question. A ball is thrown at 30 degrees."})
            st.rerun()
    with col2:
        if st.button("🤔 Lenz's Law Concept"):
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
        
        # Using Flash for speed
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
        context_prompt = f"[Context: Student is studying {topic}. Do NOT give the answer immediately. Guide them. If they get it right, SUMMARIZE.]\n\n{prompt}"
        
        response = chat.send_message(context_prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
