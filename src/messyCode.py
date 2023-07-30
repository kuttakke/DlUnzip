""" 批量重命名文件夹下的文件名为指定编码 """
import argparse
from pathlib import Path


def cover(
    root_path: Path,
    ec: str,
    dc: str,
    checked: bool = False,
    _file_name_list: list[str] | None = None,
    _is_root: bool = True,
):
    if not _file_name_list:
        _file_name_list = []
    for file in root_path.iterdir():
        file_name = file.name
        try:
            real_name = file_name.encode(ec).decode(dc)
        except (UnicodeDecodeError, UnicodeEncodeError):
            # print(f"文件名{file_name}不是{ec}编码")
            continue
        else:
            if real_name == file_name:
                # print(f"文件{file_name}已是{ec}编码")
                pass
            elif checked:
                file = file.rename(file.parent / real_name)
                print(f"文件{file_name}已重命名为{real_name}")
            else:
                _file_name_list.append(real_name)
        if file.is_dir():
            cover(file, ec, dc, checked, _file_name_list, _is_root=False)
    if _is_root and not checked:
        if _file_name_list:
            print("即将重命名为以下文件：\n")
        else:
            print("没有需要重命名的文件")
            exit()
        for file_name in _file_name_list:
            print(file_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="文件夹路径", type=str)
    parser.add_argument("-e", "--encode", help="原编码", type=str, default="GBK")
    parser.add_argument("-d", "--decode", help="目标编码", type=str, default="shift-jis")

    args = parser.parse_args()
    path: str = args.path
    path = path.removesuffix('"')
    ec = args.encode
    dc = args.decode
    if not (p := Path(path)):
        print("路径不存在")
        exit()
    cover(p, ec, dc)
    check = input("是否重命名文件？(y/n default: y)\n")
    if check == "n":
        exit()
    cover(p, ec, dc, checked=True)
