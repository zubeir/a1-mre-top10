@echo off
echo ========================================
echo A1-MRE Dashboard - Local Run Script
echo ========================================
echo.

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully
echo.

echo [2/4] Initializing database and fetching market data...
python update_data.py
if %errorlevel% neq 0 (
    echo Error updating data
    pause
    exit /b 1
)
echo Data updated successfully
echo.

echo [3/4] Starting Streamlit application...
echo The dashboard will open in your browser at http://localhost:8501
echo Press Ctrl+C to stop the server
echo.
streamlit run app.py
