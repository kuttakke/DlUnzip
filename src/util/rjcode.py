import re

import httpx
from lxml import html

from .retry import retry


def get_rjcode(value: str) -> str | None:
    regex = r"RJ(\d{8}|\d{6})"
    if res := re.findall(regex, value, re.IGNORECASE):
        return res[0]


@retry()
def get_rj_title(value: str) -> str | None:
    rjcode = get_rjcode(value)
    if not rjcode:
        return
    rjcode = f"RJ{rjcode}"
    url = (
        "https://hvdb.me/Dashboard/Details/RJ"
        f"{rjcode[3:] if rjcode[2] == '0' else rjcode[2:]}"
    )
    with httpx.Client() as client:
        text = _get_title(client, url)
    return f"{rjcode} {text}" if text else None


def _get_title(client, url):
    res = client.get(url)
    if res.status_code != 200:
        return None
    text = res.text
    tree = html.fromstring(text)
    title = tree.xpath("//input[@id='Name']/@value")
    # 替换掉windows文件名中不允许的字符
    title = re.sub(r'[\\/:*?"<>|]', "", title[0])
    return title.strip()


if __name__ == "__main__":
    # print(get_rjcode("RJ12345678"))
    # print(get_rjcode("RJ123456"))
    print(get_rj_title("RJ01030662"))
