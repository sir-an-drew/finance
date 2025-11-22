cd ~/valuation_tool
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install yfinance yahooquery streamlit pandas numpy --force-reinstall
streamlit run app_6.py
