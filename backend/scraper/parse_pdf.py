import pandas as pd
from sqlalchemy import create_engine

from utils import parse_pdf, read_pdf

# DB接続
SQLALCHEMY_DATABASE_URL = "sqlite:///../fir.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 重複チェック用
reports = pd.read_sql(sql="SELECT file_name_issuer FROM reports", con=engine)
# 抽出元df（2020-12-17以降分）
df = pd.read_sql(
    sql="SELECT * FROM links WHERE report_date >= '2020-12-17' \
        ORDER BY report_date DESC",
    con=engine,
)

for row in df.itertuples():
    # PDFファイル
    file_path = "./pdf/" + row.file_name

    # PDF読み取り
    text = read_pdf(file_path)

    # パース
    details = parse_pdf(row, text)

    # 重複チェックしてDBにInsert
    if details is not None:
        for i in range(len(details)):
            record = details.iloc[[i]]
            file_name_issuer = "".join(record["file_name_issuer"])

            if file_name_issuer not in reports["file_name_issuer"].values:
                # DBにfile_name_issuerの要素がなければInsert
                record.to_sql("reports", con=engine, if_exists="append", index=False)
            else:
                # 内側のループから抜ける
                print(f'"{file_name_issuer}" was a duplicate.')
                break
        else:
            # 内側のループが正常に終了したら次の外側ループへ
            continue
        # 外側のループから抜ける
        break

print("Done parse_pdf")
