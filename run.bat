@echo off
cd /d "%~dp0"
echo Installing requirements...
python -m pip install -r requirements.txt --quiet
python -m streamlit run app.py
pause
