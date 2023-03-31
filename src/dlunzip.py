import shutil
import subprocess
from pathlib import Path

from loguru import logger
from plyer import notification

from password.handler import Pw, PWhandler
from util.rjcode import get_rj_title

logger.add(
    Path(__file__).parent / "logs" / "dlunzip.log", rotation="1 day", encoding="utf-8"
)


def extract_7z(path: Path, password=None):
    new_path = path.parent / path.stem
    new_path.mkdir(exist_ok=True)
    archive_path = str(path)
    destination_path = str(new_path)
    cmd = ["7z", "x", archive_path, f"-o{destination_path}"]
    if password:
        cmd.append(f"-p{password}")
    logger.info(
        f"解压 {archive_path} to {destination_path} 密码： {password}"
        if password
        else f"不使用密码解压 {archive_path} to {destination_path}"
    )
    code = subprocess.run(cmd, input=b"\n")
    if code.returncode == 0:
        return _sucess(archive_path, destination_path, path, new_path)
    logger.error(f"解壓 {archive_path} to {destination_path} failed")
    # clean new path
    if new_path.exists():
        shutil.rmtree(path=new_path)
    return False


def is_child_unzipable(path: Path):
    return all(file.is_file() for file in path.iterdir()) and all(
        file.suffix not in [".mp3", ".wav"] for file in path.iterdir()
    )


def unzip_child(path: Path):
    is_first = True
    for file in path.iterdir():
        if file.is_file():
            # 检查分卷
            if not is_first and "part" in file.stem:
                logger.warning(f"Skip {file} 疑似是分卷文件，不压缩")
                continue
            unzip(file)
            is_first = False
    # TODO 检查分卷是否全部解压，有则删除并移动文件


def _sucess(archive_path, destination_path, path, new_path):
    logger.success(f"解压 {archive_path} to {destination_path} 成功")
    # 删除
    path.unlink()
    title = get_rj_title(new_path.stem)
    if title:
        new_path = new_path.rename(new_path.parent / title)

    logger.success(f"删除 {path} 成功")
    notification.notify(
        title="解压成功",
        message=f"解压 {archive_path} to {destination_path} 成功",
        app_name="DlUnzip",
        timeout=5,
    )  # type: ignore
    if is_child_unzipable(new_path):
        logger.info("检测到子文件夹，开始解压")
        unzip_child(new_path)
    return True


def unzip(path: Path):
    if "." not in path.name:
        logger.success(f"Rename {path} to {path.with_suffix('.zip')}")
        path = path.rename(path.with_suffix(".zip"))
    pws = PWhandler.get_all_pws(path.name)
    # try unzip with none password
    if extract_7z(path):
        return
    for pw in pws:
        if extract_7z(path, pw.value):
            return
    while True:
        notification.notify(
            title="请输入密码",
            message=f"请为 {path} 文件输入密码",
            app_name="DlUnzip",
            timeout=5,
        )  # type: ignore
        pw = Pw(value=str(input(f"请为 {path} 文件输入密码: \n")))
        if pw == "skip":
            logger.info(f"跳过解压 {path}")
            break
        if extract_7z(path, pw.value):
            PWhandler.add_pw(pw.value)
            logger.info(f"添加并保存密码： {pw.value}")
            break


def run(path_str: str):
    PWhandler.load_all_pws()
    path = Path(path_str)
    last_file_name = ""
    for file in path.iterdir():
        if file.is_file():
            # 检查文件名是否有变化
            if file.stem == last_file_name and file.suffix != ".zip":
                logger.warning(f"Skip {file} 疑似是分卷文件，不压缩")
                continue
            unzip(file)
            last_file_name = file.stem


if __name__ == "__main__":
    run(r"path")
