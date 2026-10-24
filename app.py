import streamlit as st
import requests

# Apna Render backend ka live URL yahan daal
API_URL = "https://micro-saas-api-u0ny.onrender.com"

st.set_page_config(page_title="AI Payload Refiner API", page_icon="⚡", layout="centered")

st.title("⚡ AI JSON & Text Payload Refiner API")
st.markdown("Convert raw messy text into clean, structured JSON instantly using Llama 3. **₹1.00 per API call.**")

tab1, tab2 = st.tabs(["🔑 Get API Key", "🚀 Test Refiner API"])

with tab1:
    st.subheader("Generate your Live API Key")
    email = st.text_input("Enter your Email address:")
    if st.button("Create API Key & Get ₹10 Free Trial"):
        if email:
            res = requests.post(f"{API_URL}/v1/auth/create-key?email={email}")
            if res.status_code == 200:
                data = res.json()
                st.success("API Key generated successfully!")
                st.code(data["api_key"], language="text")
                st.info(f"Welcome balance loaded: ₹{data['welcome_balance_inr']}")
            else:
                st.error("Something went wrong. Try again.")
        else:
            st.warning("Please enter an email.")

with tab2:
    st.subheader("Test API Endpoint")
    api_key = st.text_input("Enter your API Key (sk_live_...):", type="password")
    raw_text = st.text_area("Enter raw text to refine (e.g., 'Rahul is 25 years old living in Delhi'):")
    
    if st.button("Refine Payload"):
        if api_key and raw_text:
            headers = {"x-api-key": api_key, "Content-Type": "application/json"}
            payload = {"raw_text": raw_text}
            
            res = requests.post(f"{API_URL}/v1/refine", headers=headers, json=payload)
            
            if res.status_code == 200:
                result = res.json()
                st.success(f"Success! Deducted: ₹{result['deducted_inr']}")
                st.markdown(f"**Remaining Balance:** ₹{result['remaining_balance_inr']}")
                st.code(result["data"], language="json")
            elif res.status_code == 402:
                st.error("Insufficient Balance! Please top up your wallet.")
            else:
                st.error(f"Error: {res.json().get('detail', 'Invalid request')}")
        else:
            st.warning("Please provide both API Key and raw text.")
