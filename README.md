# Firm Inspection Reports Watcher

![fir_image](https://user-images.githubusercontent.com/38820722/191781580-df7775af-d25a-478d-b378-8f3d724196fc.png)

## Overview

This app extracts Issuers from PCAOB's Firm Inspection Reports(>=2020-12-17) and visualizes them in Steamlit.

## Requirement

- Ubuntu 20.04
- Python 3.8.10
- Google Chrome 105.0.5195.102

## Usage

```bash
# Install libraries
cd fir_catcher
pip install -r requirements.txt

# Create DB
cd backend
python models.py

# Crawling and Scraping
cd scraper
python get_page_detail.py
python get_pdf.py
python parse_pdf.py

# Rename and Edit login config
cd ../../
mv config.example.yaml config.yaml
vim config.yaml

# Run streamlit
streamlit run app.py
```

## Reference

- [Streamlit](https://streamlit.io/)
- [Streamlit-Authenticator](https://github.com/mkhorasani/Streamlit-Authenticator)

## Author

[Blog - Python と！](https://python-to.hateblo.jp/)

## Licence

[MIT](https://github.com/barorin/fir_watcher/blob/master/LICENSE)
