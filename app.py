"""AqarExit Resale Analytics: launch with python -m streamlit run app.py."""
from pathlib import Path

import pymysql
import streamlit as st

import app_service
from ui_pages import overview, explorer, projects, developers, reports, registration

st.set_page_config(page_title='AqarExit Resale Analytics',page_icon=':material/apartment:',
                   layout='wide',initial_sidebar_state='auto')
st.html('<style>'+Path(__file__).with_name('assets').joinpath('studio.css').read_text(encoding='utf-8')+'</style>')

st.logo(str(Path(__file__).with_name('assets')/'wordmark.svg'),size='large')

pages = [
    st.Page(overview,title='Overview',icon=':material/dashboard:',default=True,url_path='overview'),
    st.Page(explorer,title='Property explorer',icon=':material/search:',url_path='properties'),
    st.Page(projects,title='Projects & reviews',icon=':material/apartment:',url_path='projects'),
    st.Page(developers,title='Developer rankings',icon=':material/leaderboard:',url_path='developers'),
    st.Page(reports,title='Market reports',icon=':material/analytics:',url_path='reports'),
    st.Page(registration,title='Register profile',icon=':material/person_add:',url_path='register'),
]
page=st.navigation(pages)

with st.sidebar:
    st.html('<div class="studio-side-note"><strong>Egypt resale market</strong><br>Prices in Egyptian pounds</div>')
    if st.button('Refresh data',icon=':material/refresh:',width='stretch'):
        st.cache_data.clear()
        st.rerun()
    st.caption('Market data is cached for up to 5 minutes. Use Refresh data for the latest figures.')

st.html('<div class="studio-breadcrumb">AqarExit Resale Analytics</div>')
try:
    page.run()
except (pymysql.Error,OSError,RuntimeError,ValueError) as exc:
    st.error('We couldn’t load the market data. Please try again in a moment.')
    st.caption('If this continues, check the database service, local connection settings and certificate.')
    if st.button('Try again',type='primary'):
        st.cache_data.clear()
        st.rerun()
