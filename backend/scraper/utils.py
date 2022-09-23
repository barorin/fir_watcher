import datetime
import os
import re
import time
import urllib.request

import chromedriver_binary  # NOQA
import fitz
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from tenacity import retry, stop_after_attempt, wait_fixed

# retry設定
wait = wait_fixed(30)  # リトライ間隔
stop = stop_after_attempt(5)  # リトライ回数


@retry(wait=wait, stop=stop)
def get_soup(url):
    """soup取得

    Args:
        url(str): クロール先のURL
    Returns:
        soup(BeautifulSoup): HTML
    """
    # driverのオプション設定
    options = webdriver.ChromeOptions()
    options.add_argument("no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-desktop-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--lang=ja")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--proxy-server="direct://"')
    options.add_argument("--proxy-bypass-list=*")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome("chromedriver", options=options)
    driver.implicitly_wait(10)

    driver.get(url)
    time.sleep(10)
    html = driver.page_source.encode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    driver.close()

    return soup


@retry(wait=wait, stop=stop)
def get_last_page(url):
    """最終ページを取得

    Args:
        url(str): クロール先のURL
    Returns:
        last_page(int): リストの最終ページ
    """
    soup = get_soup(url)
    last_page = re.search(
        r"(\d)+", soup.find(class_="hawk-pagination__total-text").get_text()
    ).group()

    return int(last_page)


def get_report(df, soup):
    """一覧ページから情報を抽出

    Args:
        df(DataFrame): 一覧ページから取得した情報を格納するdf
        soup(BeautifulSoup): soup
    Returns:
        df(DataFrame): Argsのdf（一覧ページから取得した情報格納後）
    """
    for tag in soup.find_all(class_="media-body sf-media-body"):
        firm_name = tag.find("a").get_text()
        country_and_report_date = tag.find_all(class_="lead-text-st")
        country = country_and_report_date[0].get_text()
        report_date = country_and_report_date[1].get_text()
        report_date = report_date.replace(".", "")  # Apr.とかの.を削除
        report_date = datetime.datetime.strptime(report_date, "%b %d, %Y")
        report_date = datetime.date(
            report_date.year, report_date.month, report_date.day
        )
        pdf_url = tag.find("a").get("href")

        tmp = pd.DataFrame(
            {
                "firm_name": [firm_name],
                "country": [country],
                "report_date": [report_date],
                "pdf_url": [pdf_url],
            }
        )

        df = pd.concat([df, tmp], ignore_index=True)

    df["file_name"] = df["pdf_url"].apply(
        lambda x: re.search(r"\/[^\/]*pdf", x).group().replace("/", "")
    )

    return df


@retry(wait=wait, stop=stop)
def get_pdf(folder_path, urls):
    """pdfをダウンロード
    Args:
        folder_path(str): pdfの格納先
        urls(list[str]): ダウンロードURLのリスト
    Returns:
        None
    """
    # ファイル名.pdfの抽出
    pattern = re.compile(r"\/[^\/]*pdf")

    for i, url in enumerate(urls):
        res = re.search(pattern, url)
        file_name = res.group()
        file_path = folder_path + file_name

        if not os.path.isfile(file_path):
            print(i + 1, "try:", file_name.replace("/", ""))
            urllib.request.urlretrieve(url, file_path)
            time.sleep(3)


def read_pdf(file_path):
    """pdfの読み取り
    Args:
        file_path(str): pdfのファイルパス
    Returns:
        text(str): pdfのテキストデータ
    """
    print("parsing...", file_path)
    doc = fitz.open(file_path)
    rect = fitz.Rect(0, 0, 612, 745)  # 読み取り範囲の設定

    texts = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        texts.append(page.get_text("text", clip=rect).replace("\n", ""))

    text = "".join(texts)

    return text


def parse_pdf(row, text):
    """pdfのパース
    Args:
        row(Pandas): linksテーブルの行データ
        text(str): pdfのテキストデータ
    Returns:
        details(DataFrame): パース後のdf（reportsテーブルの様式）
    """
    issuers_and_industries = re.findall(r"(Issuer [A-W].*?)Type", text)

    if issuers_and_industries:
        if issuers_and_industries[0]:
            if re.search(r"Issuer A[^)].*", issuers_and_industries[0]) is None:
                issuer_a = "Issuer A"
            else:
                issuer_a = re.search(
                    r"Issuer A[^)].*", issuers_and_industries[0]
                ).group()
            issuers_and_industries[0] = issuer_a

        issuers = [
            re.search(r"(Issuer [A-W])", iss).group(1) for iss in issuers_and_industries
        ]

        industries = [
            re.search(r"– (.*)", iss).group(1) if re.search(r"– (.*)", iss) else "None"
            for iss in issuers_and_industries
        ]
        industries = [
            "Health Care" if iss == "Healthcare" else iss for iss in industries
        ]  # ゆらぎ修正

        type_of_audit_and_related_area_affected = re.findall(
            r"(In our review.*?)Description", text
        )

        description_of_the_deficiencies_identified = re.findall(
            r"Description of the (?:deficiencies|deficiency) identified(.*?)"
            + r"(?:Issuer|Audits with|PART I\.B|Part I\.B)",
            text,
        )

        # df作成
        details = pd.DataFrame(issuers, columns=["issuer"])
        details["industry"] = industries
        details[
            "type_of_audit_and_related_area_affected"
        ] = type_of_audit_and_related_area_affected
        details[
            "description_of_the_deficiencies_identified"
        ] = description_of_the_deficiencies_identified
        details["file_name"] = row.file_name

        # 前後から空白を削除
        details["issuer"] = details["issuer"].str.strip()
        details["industry"] = details["industry"].str.strip()
        details["type_of_audit_and_related_area_affected"] = details[
            "type_of_audit_and_related_area_affected"
        ].str.strip()
        details["description_of_the_deficiencies_identified"] = details[
            "description_of_the_deficiencies_identified"
        ].str.strip()

        # 主キー作成
        details["file_name_issuer"] = details["file_name"] + "_" + details["issuer"]

        return details
