"""
Account Intelligence Agent - Streamlit Frontend

Web interface that connects to the Agent API backend.
"""

import os

import requests
import streamlit as st

# API configuration - use env var or default
API_URL = os.getenv("API_URL", "http://localhost:8001")

# Page config
st.set_page_config(
    page_title="Account Intelligence Agent",
    page_icon="🤖",
    layout="centered",
)

# Custom CSS - Clean white theme
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    .stApp {
        background: #ffffff;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 720px;
    }
    
    h1 {
        color: #111827 !important;
        font-weight: 600;
        font-size: 2rem !important;
        letter-spacing: -0.02em;
    }
    
    h2, h3 {
        color: #374151 !important;
        font-weight: 600;
    }
    
    p, label, .stMarkdown {
        color: #4b5563;
    }
    
    /* Input styling */
    .stSelectbox > div > div,
    .stTextArea textarea {
        background: #f9fafb !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        color: #111827 !important;
    }
    
    .stSelectbox > div > div:focus-within,
    .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* Button styling */
    .stButton > button[kind="primary"] {
        background: #3b82f6 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.15s ease !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: #2563eb !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important;
    }
    
    /* Response box */
    .response-box {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
        white-space: pre-wrap;
        color: #374151;
        line-height: 1.7;
        font-size: 0.95rem;
    }
    
    /* Divider */
    hr {
        border-color: #f3f4f6 !important;
        margin: 1.5rem 0 !important;
    }
    
    /* Toggle */
    .stCheckbox label span {
        color: #6b7280 !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #3b82f6 !important;
    }
    
    /* Error/Warning messages */
    .stAlert {
        border-radius: 8px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def fetch_accounts():
    """Fetch accounts from the API."""
    try:
        response = requests.get(f"{API_URL}/api/accounts", timeout=10)
        response.raise_for_status()
        return response.json()["accounts"]
    except Exception as e:
        st.error(f"Failed to fetch accounts: {e}")
        return []


def query_agent(account_id: int, user_query: str) -> str:
    """Query the agent via API (non-streaming)."""
    response = requests.post(
        f"{API_URL}/api/query",
        json={"account_id": account_id, "user_query": user_query},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"]


def query_agent_stream(account_id: int, user_query: str):
    """Query the agent via API with streaming."""
    response = requests.post(
        f"{API_URL}/api/query/stream",
        json={"account_id": account_id, "user_query": user_query},
        stream=True,
        timeout=60,
    )
    response.raise_for_status()

    for line in response.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data == "[DONE]":
                    break
                if data.startswith("[ERROR]"):
                    raise Exception(data[8:])
                yield data


def main():
    # Header
    st.title("🤖 Account Intelligence Agent")
    st.markdown(
        "Ask questions about any account based on their transcripts and emails."
    )

    st.divider()

    # Fetch accounts
    accounts = fetch_accounts()

    if not accounts:
        st.warning("No accounts available. Make sure the API is running on port 8001.")
        return

    # Account selection
    account_options = {acc["name"]: acc["id"] for acc in accounts}
    selected_account = st.selectbox(
        "Select Account",
        options=list(account_options.keys()),
        index=None,
        placeholder="Choose an account...",
    )

    # Query input
    user_query = st.text_area(
        "Your Question",
        placeholder="e.g., What are the main pain points discussed? Summarize recent communications...",
        height=100,
    )

    # Streaming toggle
    use_streaming = st.toggle("Stream response", value=False)

    # Submit button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        submit = st.button("🚀 Ask Agent", type="primary", use_container_width=True)

    # Handle submission
    if submit:
        if not selected_account:
            st.error("Please select an account.")
            return

        if not user_query.strip():
            st.error("Please enter a question.")
            return

        account_id = account_options[selected_account]

        st.divider()
        st.subheader("💬 Agent Response")

        if use_streaming:
            # Streaming response
            response_placeholder = st.empty()
            full_response = ""

            try:
                for chunk in query_agent_stream(account_id, user_query):
                    full_response += chunk
                    response_placeholder.markdown(
                        f'<div class="response-box">{full_response}</div>',
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            # Non-streaming response
            with st.spinner("Thinking..."):
                try:
                    response = query_agent(account_id, user_query)
                    st.markdown(
                        f'<div class="response-box">{response}</div>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
