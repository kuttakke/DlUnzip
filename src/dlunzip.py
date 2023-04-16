import contextlib
import random
import shutil
import subprocess
from pathlib import Path

from loguru import logger
from plyer import notification

from exception import NotArchiveError, PasswordError
from password.handler import Pw, PWhandler
from util.rjcode import get_rj_title

logger.add(
    Path(__file__).parent / "logs" / "dlunzip.log", rotation="1 day", encoding="utf-8"
)


def get_file_list_from_archive(path: Path, password: str = "") -> list[str]:
    cmd = ["7z", "l", f"-p{password}", str(path)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.readlines()  # type: ignore
    if (
        not out[-2].decode("gbk", errors="ignore").startswith("------")
        and not out[-4].decode("gbk", errors="ignore").startswith("------")
        and not out[-9].decode("gbk", errors="ignore").startswith("------")
    ):
        all_text = "".join([line.decode("gbk", errors="ignore") for line in out])
        if "Wrong password" in all_text:
            raise PasswordError
        # if "Cannot open the file as archive" in all_text:
        else:
            raise NotArchiveError
    file_name_list = []
    if out[-4].decode("gbk", errors="ignore").startswith("------"):
        index = -4
    elif out[-2].decode("gbk", errors="ignore").startswith("------"):
        index = -2
    else:
        index = -9
    for line in out[:index][::-1]:
        if line.decode("gbk", errors="ignore").startswith("------"):
            break
        file_name_list.append("".join(line.decode("gbk", errors="ignore").split()[5:]))
    return file_name_list


def try_with_password(path: Path, password: list[str]) -> tuple[list[str], Pw]:
    for pw in password:
        with contextlib.suppress(PasswordError):
            file_list = get_file_list_from_archive(path, pw)
            return file_list, Pw(value=pw)
    while True:
        notification.notify(
            title="请输入密码",
            message=f"请为 {path} 文件输入密码",
            app_name="DlUnzip",
            timeout=5,
        )  # type: ignore
        pw_input = input(f"请为{path.name}输入密码：\n")
        try:
            file_list = get_file_list_from_archive(path, pw_input)
            return file_list, Pw(value=pw_input)
        except PasswordError:
            logger.error("密码错误，请重新输入")


def test_unzip_file(path: Path, password: str = "") -> bool:
    cmd = ["7z", "t", f"-p{password}", str(path)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.read().decode("gbk", errors="ignore")  # type: ignore
    return "Everything is Ok" in out


def try_test_with_password(path: Path, password: list[str]) -> Pw:
    # print(password)
    for pw in password:
        if test_unzip_file(path, pw):
            return Pw(value=pw)
    while True:
        notification.notify(
            title="请输入密码",
            message=f"请为 {path} 文件输入密码",
            app_name="DlUnzip",
            timeout=5,
        )  # type: ignore
        pw_input = input(f"请为{path.name}输入密码：\n")
        if test_unzip_file(path, pw_input):
            return Pw(value=pw_input)


# def get_decode_format(file_name_list: list[bytes]) -> str:
#     for file_name in file_name_list:
#         with contextlib.suppress(UnicodeDecodeError):
#             file_name.decode("shift-jis")
#             return "shift-jis"
#     return "GBK"


def check_and_rename_file(path: Path):
    for file in path.iterdir():
        name = file.name
        with contextlib.suppress(UnicodeDecodeError):
            true_name = name.encode("gbk").decode("shift-jis")
            file = file.rename(file.parent / true_name)
        if file.is_dir():
            check_and_rename_file(file)


def extract_7z(path: Path, password=None, is_child=False):
    new_path = path.parent / path.stem
    new_path.mkdir(exist_ok=True)
    archive_path = str(path)
    destination_path = str(new_path)
    cmd = ["7z", "x", archive_path, f"-o{destination_path}"]
    if password:
        cmd.append(f"-p{password}")
    logger.info(
        f"解压 {Path(archive_path).name} to {Path(destination_path).name} 密码： {password}"
        if password
        else f"不使用密码解压 {archive_path} to {destination_path}"
    )
    code = subprocess.run(cmd, input=b"\n")
    if code.returncode == 0:
        check_and_rename_file(new_path)
        return _sucess(archive_path, destination_path, path, new_path, is_child)
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
            unzip(file, is_child=True)
            is_first = False
    # TODO 检查分卷是否全部解压，有则删除并移动文件


def move_file(file: Path):
    file_list = list(file.iterdir())
    if len(file_list) == 1 and file_list[0].is_dir():
        for file_ in file_list[0].iterdir():
            if (file / file_.name).exists():
                file_.rename(file / f"{file_.name}{random.randint(0, 1000)}")
            else:
                file_.rename(file / file_.name)
        file_list[0].rmdir()
        move_file(file)


def _sucess(archive_path, destination_path, path, new_path, is_child):
    logger.success(f"解压 {Path(archive_path).name} to {Path(destination_path).name} 成功")
    # 删除
    path.unlink()
    title = get_rj_title(new_path.stem)
    if title:
        new_path = new_path.rename(new_path.parent / title)

    logger.success(f"删除 {path.name} 成功")
    notification.notify(
        title="解压成功",
        message=f"解压 {Path(archive_path).name} to {Path(destination_path).name} 成功",
        app_name="DlUnzip",
        timeout=5,
    )  # type: ignore
    if is_child_unzipable(new_path):
        logger.info("检测到子文件夹，开始解压")
        unzip_child(new_path)
    if not is_child:
        logger.info("开始移动文件")
        move_file(new_path)
    return True


def unzip(path: Path, is_child=False):
    if "." not in path.name:
        logger.success(f"Rename {path.name} to {path.with_suffix('.zip').name}")
        path = path.rename(path.with_suffix(".zip"))
    pws = PWhandler.get_all_pws(path.name)
    # get file code
    current_pw = ""
    try:
        _ = get_file_list_from_archive(path)
    except NotArchiveError:
        logger.error(f"{path} 不是压缩文件")
        return
    except PasswordError:
        _, pw = try_with_password(path, [pw.value for pw in pws])
        current_pw = _save_pw(pw)
    # test file
    if not current_pw:
        if test_unzip_file(path):
            logger.info(f"不需要密码解压 {path.name}")
        else:
            pw = try_test_with_password(path, [pw.value for pw in pws])
            current_pw = _save_pw(pw)

    # unzip
    extract_7z(path, current_pw or None, is_child)


# TODO Rename this here and in `unzip`
def _save_pw(pw: Pw):
    if not pw.value.startswith("RJ"):
        PWhandler.add_pw(pw.value)
        logger.info(f"添加并保存密码： {pw.value}")
    return pw.value


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
