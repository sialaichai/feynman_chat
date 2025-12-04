import streamlit as st
from google import genai
import textwrap

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
    * Start with a real-world analogy (e.g., Voltage as "pressure," Resistors as "narrow pipes").
    * ONLY introduce technical jargon *after* the concept is understood.

2.  **The "Test Me" (Feynman Technique) Protocol:**
    * If the student asks to be tested, DO NOT give a multiple-choice quiz.
    * Ask them to explain a concept back to you (e.g., "Explain Electromagnetic Induction to me as if I were a Primary 6 student").
    * Critique their explanation:
        * Did they use jargon to hide confusion?
        * Did they miss the underlying mechanism?
    * If they are wrong, give a hint (analogy) and ask them to try again.

3.  **SEAB 9478 SYLLABUS SPECIFICS (STRICT ADHERENCE):**
    * **Math Level:** Use standard H2 Physics notation. You are allowed to use basic calculus for definitions (e.g., $v = ds/dt$, $a = dv/dt$, $E = -dV/dx$) but focus on algebraic solutions for problem-solving unless specified.
    * **Practical Paper 4 (Crucial):** If asked about practicals, emphasize the **2026 requirement for Spreadsheet skills**. Mention finding gradients using Excel, linearization of graphs ($y = mx + c$), and calculating uncertainties using standard error.
    * **Key Topics:** Newtonian Mechanics, Thermal Physics (First Law, Ideal Gases), Waves (Superposition), Electricity & Magnetism (EMI, AC Circuits), and Modern Physics (Quantum, Nuclear).
    * **Exclusions:** Do NOT teach topics from the old syllabus that were removed (e.g., Logic Gates) unless explicitly asked.

4.  **Formatting & Style:**
    * **LaTeX:** Use LaTeX for ALL math. Inline: $F=ma$. Block: $$E = mc^2$$.
    * **Tone:** Curious, enthusiastic, unpretentious. "Physics is fun! Imagine..."
    * **Structure:** Keep answers concise. Use bullet points for steps.

**Common H2 Misconceptions to Flag:**
* Thinking Centripetal Force is a "new" physical force (it's just the resultant).
* Confusing Gravitational Potential (always negative) with Potential Energy changes.
* Thinking current is "used up" in a circuit.
* **Significant Figures:** Always remind students to check s.f. in their final answers (usually 2 or 3 s.f.).
"""

# -----------------------------------------------------------------------------
# 3. SIDEBAR & SETTINGS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=150, caption="Prof. Feynman")
    st.title("Settings")
    
    # Topic Selector to prime the AI
    topic = st.selectbox(
        "Current Revision Topic:",
        ["General / Any", "Measurement & Uncertainty", "Kinematics & Dynamics", 
         "Forces & Turnings Effects", "Work, Energy, Power", "Circular Motion", 
         "Gravitational Fields", "Thermal Physics", "Oscillations & Waves", 
         "Electricity & DC Circuits", "Electromagnetism (EMI/AC)", "Modern Physics (Quantum/Nuclear)", 
         "Paper 4: Practical Skills (Spreadsheets)"]
    )
    
    # API Key Input (if not in secrets)
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")
        if not api_key:
            st.warning("Please enter an API Key to chat.")

    st.markdown("---")
    
    # Clear Chat Button
    if st.button("🧹 Start New Topic", type="primary"):
        st.session_state.messages = []
        st.rerun()
        
    st.caption("Based on SEAB 9478 (2026) Syllabus")

# -----------------------------------------------------------------------------
# 4. CHAT LOGIC
# -----------------------------------------------------------------------------

st.title("⚛️ H2 Feynman Bot")
st.markdown(f"**Focus:** `{topic}` | **Mode:** Explain & Test")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add the system instruction purely for context (not shown to user)
    st.session_state.messages.append({"role": "system", "content": SEAB_H2_INSTRUCTIONS})

# Display Chat History
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Handle User Input
if prompt := st.chat_input("Ask about a concept (e.g., 'Why is the sky blue?' or 'Test me on SHM')"):
    
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Construct the specific prompt with context
    # We inject the sidebar topic choice invisibly to keep the AI focused
    final_prompt = f"[CONTEXT: Student is revising '{topic}'. Adhere to SEAB 9478 syllabus.]\n\nUser Question: {prompt}"

    # 3. Generate Response
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            
            # Send the conversation history + new prompt
            # Note: We filter strictly for 'user' and 'model' roles for the API history, 
            # but we send the system instruction in the config.
            
            response = client.models.generate_content(
                model="gemini-1.5-pro-latest",
                contents=final_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SEAB_H2_INSTRUCTIONS,
                    temperature=0.7
                )
            )
            
            # 4. Display AI Response
            with st.chat_message("assistant"):
                st.markdown(response.text)
            
            # Save to history
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("Please provide an API Key in the sidebar.")
