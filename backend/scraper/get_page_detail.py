import pandas as pd
from sqlalchemy import create_engine
from utils import get_last_page, get_report, get_soup

# DB接続
SQLALCHEMY_DATABASE_URL = "sqlite:///../fir.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 重複チェック用
links = pd.read_sql(
    sql="SELECT pdf_url FROM links ORDER BY report_date DESC", con=engine
)

# 最終のページを取得
last_page = get_last_page(
    "https://pcaobus.org/oversight/inspections/firm-inspection-reports?mpp=96"
)

# リスト取得
for page in range(1, last_page + 1):
    # クロール
    url = (
        "https://pcaobus.org/oversight/inspections/firm-inspection-reports"
        + f"?pg={page}&mpp=96"
    )

    df = pd.DataFrame(columns=["firm_name", "country", "report_date", "pdf_url"])
    try_num = 0
    while len(df) == 0:
        try_num += 1
        # 10回までトライする
        if try_num == 10:
            raise Exception("Error - get_soup")
        else:
            print("page:", page, "/", last_page, "try:", try_num)
            print(url)
            soup = get_soup(url)
            # ページをスクレイピングしてdfにまとめる
            df = get_report(df, soup)

    # 重複チェックしてDBにInsert
    for i in range(len(df)):
        record = df.iloc[[i]]
        pdf_url = "".join(record["pdf_url"])

        if pdf_url not in links["pdf_url"].values:
            # DBにpdf_urlの要素がなければInsert
            record.to_sql("links", con=engine, if_exists="append", index=False)
        else:
            # 内側のループから抜ける
            print(f'"{pdf_url}" was a duplicate.')
            # TODO: 過去にデータが追加されている場合、ここでbreakするとそこまで到達できない
            # break
    else:
        # 内側のループが正常に終了したら次の外側ループへ
        continue
    # 外側のループから抜ける
    break
