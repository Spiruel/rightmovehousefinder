import streamlit as st
from multiapp import MultiApp
from apps import (
    wms
)
import streamlit as st
import streamlit_analytics

st.set_page_config(layout="wide")


apps = MultiApp()

# Add all your application here

apps.add_app("Home", wms.app)

# The main app
apps.run()
