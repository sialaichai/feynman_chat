import streamlit as st
import google.generativeai as genai

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="H2 Feynman Bot", page_icon="⚛️")

# -----------------------------------------------------------------------------
# 2. SYSTEM INSTRUCTIONS (SEAB H2 2026)
# -----------------------------------------------------------------------------
SEAB_H2_INSTRUCTIONS = """
You are Richard Feynman. Teach Singapore H2 Physics (Syllabus 9478).
1. Explain simply using analogies first.
2. Only use technical jargon after the concept is clear.
3. If asked to 'Test', ask the student to explain back to you.
4. Use LaTeX for math ($F=ma$).
5. Stick to the syllabus (Newtonian Mechanics, Thermal, Waves, Electricity, Modern Physics).
"""

# -----------------------------------------------------------------------------
# 3. SIDEBAR & SETUP
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("Settings")
    topic = st.selectbox("Topic", ["General", "Mechanics", "Waves", "Electricity", "Modern Physics", "Practicals"])
    
    # API Key Handling
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------------------------------------------------
# 4. CHAT LOGIC
# -----------------------------------------------------------------------------
st.title("⚛️ H2 Feynman Bot")

# Initialize Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle Input
if prompt := st.chat_input("Ask a physics question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("Please provide an API Key in the sidebar.")
        st.stop()

    # --- GENERATION LOGIC ---
    try:
        genai.configure(api_key=api_key)
        
        # We use the generic 'gemini-1.5-flash' which works on the new library.
        # If this fails, the 'except' block below will diagnose why.
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=SEAB_H2_INSTRUCTIONS
        )
        
        # Prepare history for the API
        history_api = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages if m["role"] != "system"]

        chat = model.start_chat(history=history_api[:-1])
        
        # Send message
        final_prompt = f"[Context: Student revising {topic} for Singapore H2 Physics.] {prompt}"
        response = chat.send_message(final_prompt)
        
        # Show Output
        with st.chat_message("assistant"):
            st.markdown(response.text)
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
