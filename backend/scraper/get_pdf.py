import os

import pandas as pd
from sqlalchemy import create_engine

from utils import get_pdf

# DB接続
SQLALCHEMY_DATABASE_URL = "sqlite:///../fir.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# PDFを格納するフォルダを作成
os.makedirs("./pdf", exist_ok=True)

# 2020-12-17以降のPDFをダウンロード
links = pd.read_sql(
    sql="SELECT pdf_url FROM links WHERE report_date >= '2020-12-17", con=engine
)
get_pdf("./pdf", links["pdf_url"])
print("Done get_pdf")
