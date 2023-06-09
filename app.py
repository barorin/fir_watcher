import re

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from sqlalchemy import create_engine
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder


def main():
    # ソースデータ取り込み
    df = get_df()

    # サイドバー
    st.sidebar.title("Firm Inspectoin Reports Watcher :dog:")

    # logoutメソッドでaurhenciationの値をNoneにする
    st.sidebar.markdown(f"## Login User : {name}")
    authenticator.logout("Logout", "sidebar")

    # CSVダウンロード
    st.sidebar.markdown("## Download")
    csv = make_csv(df)
    st.sidebar.download_button(
        label="Download CSV file",
        data=csv,
        file_name="firm_inspection_reports.csv",
        mime="text/csv",
        help="You can download the original data in CSV.",
    )

    # セッティング
    st.sidebar.markdown("## Settings")

    # 選択肢作成
    vars_firm_name, default_firm_name, vars_countries, vars_industries = make_vars(df)

    # 検索フォーム
    input_word = st.sidebar.text_input(
        label="Search text",
        help='Search from "Type of audit and related area affected"'
        + ' and "Description of the deficiencies identified".',
        value="",
        placeholder="Enter keywords",
    )

    # レポート範囲選択
    min_value, max_value = make_min_max_date(df)
    start_date, end_date = st.sidebar.slider(
        "Report date",
        min_value=min_value,
        max_value=max_value,
        value=(min_value, max_value),
        format="YY-MM-DD",
    )

    # ファーム選択
    all_firm = st.sidebar.checkbox("Select All (Firm name)")

    if all_firm:
        firm_name_multi_selected = st.sidebar.multiselect(
            "Firm name", vars_firm_name, default=vars_firm_name
        )
    else:
        firm_name_multi_selected = st.sidebar.multiselect(
            "Firm name", vars_firm_name, default=default_firm_name
        )

    # 国名選択
    countries_multi_selected = st.sidebar.multiselect(
        "Country", vars_countries, default=vars_countries
    )

    # 産業選択
    industries_multi_selected = st.sidebar.multiselect(
        "Industry", vars_industries, default=vars_industries
    )

    # レイアウト
    st.header("Part I.A: Audits with Unsupported Opinions")
    st.caption("Source: Public Company Accounting Oversight Board, www.pcaobus.org")

    # グラフ用df
    df = filter_df(
        df,
        firm_name_multi_selected,
        countries_multi_selected,
        industries_multi_selected,
        start_date,
        end_date,
        input_word,
    )

    # 棒グラフ
    # bar = make_bar(df, "report_date", "Issuer", "report_date", "issuer")

    # 円グラフ
    pie_firm = make_pie(df, "firm_name", "Firm name")
    pie_country = make_pie(df, "country", "Country")
    pie_industry = make_pie(df, "industry", "Industry")

    # 棒グラフと円グラフの配置
    # st.plotly_chart(bar, use_container_width=True)
    col1, col2, col3 = st.columns(3)
    col1.plotly_chart(pie_firm, use_container_width=True)
    col2.plotly_chart(pie_country, use_container_width=True)
    col3.plotly_chart(pie_industry, use_container_width=True)

    # テーブル
    df_table = make_table(df)
    grid_options = set_aggrid_configure(df_table)
    AgGrid(
        df_table, gridOptions=grid_options, fit_columns_on_grid_load=True, height=750
    )


def load_config():
    """ログイン情報読み込み"""
    with open("./config.yaml") as file:
        config = yaml.load(file, Loader=yaml.SafeLoader)

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        config["preauthorized"],
    )

    return authenticator


@st.cache_resource
def get_db_engin():
    """DB接続"""
    SQLALCHEMY_DATABASE_URL = "sqlite:///./backend/fir.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    return engine


@st.cache_data
def get_df():
    """最初のdf取り込み"""
    engine = get_db_engin()
    links = pd.read_sql(sql="SELECT * FROM links ORDER BY report_date DESC", con=engine)
    reports = pd.read_sql(sql="SELECT * FROM reports", con=engine)
    df = pd.merge(reports, links, on="file_name", how="left")
    df["report_date"] = pd.to_datetime(df["report_date"])
    df["search_text"] = (
        df["type_of_audit_and_related_area_affected"]
        + df["description_of_the_deficiencies_identified"]
    )
    # 並べ替え
    df = df.sort_values(
        ["report_date", "firm_name", "issuer"], ascending=[False, True, True]
    )

    # expandedがある場合は、そっちを残して古い方を消す
    expanded = df[df.pdf_url.str.contains("-expanded.pdf")]
    for expanded_url in set(expanded["pdf_url"]):
        base_num = re.search(r"\d{3}-\d{4}-\d{3}", expanded_url).group()
        # -> 104-2021-175

        # base_numを含む、かつ、'-expanded'を含まない方を消す
        drop_index = df.index[
            df["pdf_url"].str.contains(base_num)
            & ~df.pdf_url.str.contains("-expanded.pdf")
        ]
        df.drop(drop_index, inplace=True)

    # xxx-xxxx-xxxaの末尾のaがある場合は、そっちを残して古い方を消す
    a = df[df.pdf_url.str.match(r".*\d{3}-\d{4}-\d{3}a.*")]
    for a_url in set(a["pdf_url"]):
        base_num = re.search(r"\d{3}-\d{4}-\d{3}", a_url).group()
        # -> 104-2021-175

        # base_numを含む、かつ、'a'を含まない方を消す
        drop_index = df.index[
            df["pdf_url"].str.contains(base_num)
            & ~df.pdf_url.str.match(r".*\d{3}-\d{4}-\d{3}a.*")
        ]
        df.drop(drop_index, inplace=True)

    return df


@st.cache_data
def make_csv(df):
    """ダウンロード用CSVの作成"""
    df_download = df[
        [
            "report_date",
            "firm_name",
            "country",
            "industry",
            "issuer",
            "type_of_audit_and_related_area_affected",
            "description_of_the_deficiencies_identified",
            "pdf_url",
        ]
    ]
    csv = df_download.to_csv(index=False)

    return csv


@st.cache_data
def make_vars(df):
    """選択肢作成"""
    # ファーム選択用
    vars_firm_name = list(set([var for var in df["firm_name"]]))
    vars_firm_name = sorted(vars_firm_name)

    default_firm_name = list(
        set(
            [
                var
                for var in df["firm_name"]
                if re.search(
                    r"^(?=.*deloitte).*$|^(?=.*kpmg).*$|^(?=.*ernst).*$"
                    + r"|^(?=.*pricewaterhousecoopers).*$",
                    var,
                    flags=re.IGNORECASE,
                )
            ]
        )
    )
    default_firm_name = sorted(default_firm_name)

    # 国名選択用
    vars_countries = list(set([var for var in df["country"]]))
    vars_countries = sorted(vars_countries)

    # 産業選択
    vars_industries = list(set([var for var in df["industry"]]))
    vars_industries = sorted(vars_industries)

    return vars_firm_name, default_firm_name, vars_countries, vars_industries


@st.cache_data
def make_min_max_date(df):
    """report_dateの最小値と最大値"""
    min_value = df["report_date"].min().to_pydatetime()
    max_value = df["report_date"].max().to_pydatetime()

    return min_value, max_value


@st.cache_data
def filter_df(
    df,
    firm_name_multi_selected,
    countries_multi_selected,
    industries_multi_selected,
    start_date,
    end_date,
    input_word,
):
    """dfにフィルターかける"""
    df = df[
        (df["firm_name"].isin(firm_name_multi_selected))
        & (df["country"].isin(countries_multi_selected))
        & (df["industry"].isin(industries_multi_selected))
        & (df["report_date"] >= start_date)
        & (df["report_date"] <= end_date)
        & (df["search_text"].str.contains(input_word))
    ]

    return df


@st.cache_data
def make_pie(df, column, title):
    """円グラフ作成"""
    df = df[column].value_counts(sort=True)
    df = df.rename_axis(column).reset_index(name="counts")
    pie = px.pie(df, title=title, values="counts", names=column)
    pie.update_traces(
        textposition="inside", direction="clockwise", textinfo="percent+label"
    )
    # 割合が小さいときは文字消す
    # pie.update_layout(uniformtext_minsize=12, uniformtext_mode="hide")
    pie.update(layout_showlegend=False)  # 凡例を消す

    return pie


# @st.cache_data
# def make_bar(df, column, title, x, y):
#     """棒グラフ作成"""
#     df_bar = df.groupby(column, as_index=False).count()
#     bar = px.bar(df_bar, title=title, x=x, y=y)

#     return bar


@st.cache_data
def make_table(df):
    """テーブル作成"""
    df_table = df[
        [
            "report_date",
            "firm_name",
            "country",
            "industry",
            "issuer",
            "type_of_audit_and_related_area_affected",
            "description_of_the_deficiencies_identified",
        ]
    ]

    return df_table


@st.cache_data
def set_aggrid_configure(df):
    """aggridのオプション設定"""
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(wrapText=True, autoHeight=True)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    gb.configure_column(
        "report_date", type=["customDateTimeFormat"], custom_format_string="yyyy-MM-dd"
    )
    gb.configure_column("type_of_audit_and_related_area_affected", width=350)
    gb.configure_column("description_of_the_deficiencies_identified", width=700)
    grid_options = gb.build()

    return grid_options


if __name__ == "__main__":
    # サイト設定
    st.set_page_config(
        page_title="Firm Inspection Reports Watcher",
        page_icon=":dog:",
        initial_sidebar_state="collapsed",
        layout="wide",  # スクリーン全体を使ってグラフが表示されるようにする
    )

    # ログイン情報読み込み
    authenticator = load_config()

    # ログインメソッドで入力フォームを配置
    name, authentication_status, _ = authenticator.login("Login", "main")

    # authenticaton_statusの状態で処理を場合分け
    if authentication_status:
        main()
    elif authentication_status is False:
        st.error("Username / Password is incorrect")
