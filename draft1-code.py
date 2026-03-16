import streamlit as st
import pandas as pd

st.title("Arwa's Intelligent Scheduler")

# 1. Get User Inputs
sleep = st.slider("How many hours did you sleep?", 0, 12, 7)
stress = st.slider("Stress Level (1-10)", 1, 10, 5)

# 2. When button is clicked
if st.button("Generate My Schedule"):
    # result = model.predict([[sleep, stress]]) # This is the ML part
    st.success(f"Prediction: You are ready for High Focus work!")