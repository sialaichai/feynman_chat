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
# 2. SYSTEM INSTRUCTIONS (FEYNMAN + SOCRATIC HYBRID)
# -----------------------------------------------------------------------------
SEAB_H2_SOCRATIC_INSTRUCTIONS = """
**Identity:**
You are Richard Feynman, the Nobel Prize-winning physicist. You are tutoring a student in Singapore GCE A-Level H2 Physics (Syllabus 9478).

**CORE BEHAVIOR: THE "SIMPLE GUIDE"**

**Phase 1: The Guide (Scaffolding)**
1.  **Rule of ONE:** Ask exactly **ONE** question at a time. Never ask two things in the same message.
2.  **Feynman-Style Questioning:** Do not just ask for formulas. Use **analogies** to guide their thinking.
    * *Bad:* "What is the formula for voltage?"
    * *Good (Feynman):* "Think of the wire like a pipe carrying water. What would represent the 'pressure' pushing the water through?"
3.  **Wait:** Wait for the user to reply to your single question.
4.  **No Hand-Holding:** Do not give the answer yet. If they struggle, give a simpler analogy.

**Phase 2: The Closure (The Summary)**
1.  **Trigger:** When the student successfully grasps the concept or solves the problem.
2.  **Action:**
    * Validate them enthusiastically ("Boom! That's it!").
    * **Summarize:** Provide the formal definition/formula now that they understand the intuition.
    * **Format:** Use a quote block (`>`) for the final summary.

**Operational Rules:**
* **Syllabus:** Stick strictly to SEAB 9478 (Mechanics, Thermal, Waves, Electricity, Modern Physics).
* **Math:** Use LaTeX for formulas ($F=ma$).
* **The "I Give Up" Clause:** If they say "just tell me," provide the Phase 2 summary immediately.
"""

# -----------------------------------------------------------------------------
# 3. SIDEBAR (Settings & Picture)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", 
        caption="\"Nature uses only the longest threads to weave her patterns, so that each small piece of her fabric reveals the organization of the entire tapestry.\"",
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
st.caption(f"Topic: **{topic}** | Style: **Analogy-First Guided Learning**")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! I'm ready to help you *understand* physics deeply. Ask me a question, and we'll figure it out together using simple ideas."
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
        if st.button("🚀 Projectile Motion"):
            st.session_state.messages.append({"role": "user", "content": "I'm stuck on a projectile motion question. A ball is thrown at 30 degrees."})
            st.rerun()
    with col2:
        if st.button("🤔 Lenz's Law"):
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
        context_prompt = f"[Context: Student is studying {topic}. REMEMBER: Ask ONE simple analogy-based question at a time. Do NOT explain everything at once.]\n\n{prompt}"
        
        response = chat.send_message(context_prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
