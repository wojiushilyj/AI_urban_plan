@echo off
chcp 65001 >nul
echo ========================================================
echo  国土AI · 医药制药多场景智慧选址系统 (Streamlit)
echo  技术栈: LangGraph + PostGIS + Streamlit + Folium
echo ========================================================
"C:\Users\Reload\.workbuddy\binaries\python\envs\default\Scripts\streamlit.exe" run streamlit_app.py
pause
