import argparse
from pathlib import Path

from util.rjcode import get_rj_title, get_rjcode


def rename_directory(path: str | Path):
    path = Path(path)
    if not path.exists():
        print("路径不存在")
        exit()
    for file in path.iterdir():
        if file.is_dir():
            rj_code = f"RJ{get_rjcode(file.name)}"
            if file.name.lower().strip() == rj_code.lower().strip():
                if title := get_rj_title(file.name):
                    file.rename(file.parent / title)
                    print(f"{file.name}已重命名为{title}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="文件夹路径", type=str)
    args = parser.parse_args()
    path: str = args.path
    path = path.removesuffix('"')
    rename_directory(path)
