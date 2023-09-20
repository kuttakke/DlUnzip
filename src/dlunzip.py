import random
import re
import shutil
from pathlib import Path
from time import sleep
from send2trash import send2trash
import wexpect
from control import ControlUnzip
from display import Display, LayoutName
from exception import NotArchiveError, PasswordError
from loguru._logger import Logger
from password.handler import Pw, PWhandler
from plyer import notification
from rich_log import set_rich_logger
from util.rjcode import get_rj_title
from wexpect.legacy_wexpect import spawn_windows


class DlUnzip:
    def __init__(self, path: Path | str) -> None:
        self.path = path if isinstance(path, Path) else Path(path)
        self.logger: Logger
        self.control: ControlUnzip
        self._is_show_password_info_once = False

    def set_logger(self):
        logger = set_rich_logger(
            Display.default_logger_table,
            Display.layout_logger,
            "INFO",
            Display.redraw_logger_table,
        )
        logger.add(
            Path(__file__).parent / "logs" / "dlunzip.log",
            rotation="1 day",
            encoding="utf-8",
            level="DEBUG",
        )
        self.logger = logger  # type: ignore

    def update_files_layout(self):
        Display.display(LayoutName.FILES, self.control.to_panel())

    def process_str_handler(self, info: str):
        if "Physical Size" in info:
            if match := re.search(r"Physical Size = (\d+)", info):
                self.control.update_process(0, int(match[1]))

    def is_child_unzipable(self, path: Path):
        return all(file.is_file() for file in path.iterdir()) and all(
            file.suffix not in [".mp3", ".wav"] for file in path.iterdir()
        )

    def process_handler(self, process: spawn_windows, password: str):
        use_password = False
        is_show_process_info = False
        is_show_once = False
        try:
            while True:
                index = process.expect(
                    [
                        "Enter password",
                        "ERROR: Wrong password",
                        "Cannot open encrypted archive. Wrong password?",
                        "ERROR: Data Error in encrypted file. Wrong password?",
                        "ERROR: CRC Failed in encrypted file. Wrong password?",
                        "Cannot open the file as archive",
                        "([^\r\n]+)\r\n",
                        "(\d+%[^\r\n]+)",
                        "(\d+)%",
                        "Everything is Ok",
                        wexpect.EOF,
                    ]
                )
                if process.match == wexpect.EOF:
                    self.logger.warning("EOF")
                    return
                if index == 0:
                    use_password = True
                    process.sendline(password)
                elif index in [1, 2, 3, 4]:
                    if not self._is_show_password_info_once:
                        self._is_show_password_info_once = True
                        self.logger.info("加密压缩包，尝试使用密码库解压")
                    process.kill()
                    try:
                        process.terminate(force=True)
                    except Exception:
                        break
                    raise PasswordError
                elif index == 5:
                    raise NotArchiveError
                elif index == 6:
                    self.process_str_handler(process.match.group(0).strip())  # type: ignore
                elif index in [7, 8]:
                    is_show_process_info, is_show_once = self.handle_index_67(
                        index,
                        process,
                        is_show_process_info,
                        is_show_once,
                        password,
                        use_password,
                    )
                elif index == 9:
                    return
                # 一般来说，这里不会出现EOF
                elif index == 10:
                    self.logger.warning("EOF")
                    return
        finally:
            if process.isalive():
                process.close()

    def handle_index_67(
        self,
        index: int,
        process: spawn_windows,
        is_show_process_info: bool,
        is_show_once: bool,
        password: str,
        use_password: bool,
    ):
        if not is_show_process_info and is_show_once:
            if use_password:
                self.logger.info(f"开始解压 - 使用密码{password}")
            else:
                self.logger.info("开始解压 - 无密码")
            is_show_process_info = True
        info = process.match.group(0).strip()  # type: ignore
        compile_per = int(info.split("%")[0])
        filename = "".join(info.split("-")[1:]).strip() if index == 6 else ""
        self.control.update_process(compile_per, filename=filename)
        is_show_once = True
        return is_show_process_info, is_show_once

    def unzip_child(self, path: Path):
        is_first = True
        for file in path.iterdir():
            if file.is_file():
                # 检查分卷
                if not is_first and "part" in file.stem:
                    self.logger.warning(f"Skip {file.stem} 疑似是分卷文件，不压缩")
                    continue
                self.unzip(file, is_child=True)
                is_first = False
        # TODO 检查分卷是否全部解压，有则删除并移动文件

    def move_file(self, file: Path):
        file_list = list(file.iterdir())
        if len(file_list) == 1 and file_list[0].is_dir():
            for file_ in file_list[0].iterdir():
                if (file / file_.name).exists():
                    file_.rename(file / f"{file_.name}{random.randint(0, 1000)}")
                else:
                    file_.rename(file / file_.name)
            file_list[0].rmdir()
            self.move_file(file)

    def extract(self, path: Path, password: str, is_child: bool = False) -> bool:
        new_path = path.parent / path.stem
        new_path.mkdir(exist_ok=True)
        archive_path = str(path)
        destination_path = str(new_path)
        cmd = " ".join(["7z", "x", f"'{archive_path}'", f"-o'{destination_path}'"])
        process = wexpect.spawn(cmd)
        try:
            self.process_handler(process, password)
        except PasswordError as e:
            if new_path.exists():
                shutil.rmtree(path=new_path)
            raise PasswordError from e
        self.logger.success(f"解压完成 - {new_path.stem}")
        # path.unlink()
        send2trash(path)
        title = None if is_child else get_rj_title(new_path.stem)
        if title:
            if (new_path.parent / title).exists():
                title = f"{title}{random.randint(0, 1000)}"
            new_path = new_path.rename(new_path.parent / title)
            self.logger.success(f"重命名 - {new_path.stem}")
        notification.notify(
            title="解压成功",
            message=f"解压 {Path(archive_path).name} to {Path(destination_path).name} 成功",
            app_name="DlUnzip",
            timeout=5,
        )  # type: ignore
        # 不判断是否为子文件夹，直接移动
        self.move_file(new_path)
        self.logger.success("移动文件完成")
        if self.is_child_unzipable(new_path):
            self.logger.info(f"检测到{new_path.stem}为分卷文件，开始解压")
            self.unzip_child(new_path)
        if not is_child:
            self.move_file(new_path)
            self.logger.success("移动文件完成")

        return True

    def _save_pw(self, pw: Pw):
        if not pw.value.startswith("RJ"):
            PWhandler.add_pw(pw.value)
            self.logger.info(f"添加并保存密码： {pw.value}")

    def unzip(self, path: Path, is_child: bool = False):
        if "." not in path.name:
            self.logger.success(
                f"Rename {path.name} to {path.with_suffix('.zip').name}"
            )
            path = path.rename(path.with_suffix(".zip"))
        pws = PWhandler.get_all_pws(path.name)
        self._is_show_password_info_once = False
        for pw in pws:
            try:
                self.extract(path, pw.value, is_child)
                return
            except PasswordError:
                if pw == pws[-1]:
                    self.logger.error(f"{path.stem} 密码库无匹配密码")
                    break
                continue
            except NotArchiveError:
                self.logger.error(f"{path.stem} 不是压缩文件")
                return
        notification.notify(
            title="请输入密码",
            message=f"请为 {path} 文件输入密码",
            app_name="DlUnzip",
            timeout=5,
        )  # type: ignore
        while True:
            pw_input = Display.ask_for_password(path.stem)
            try:
                if self.extract(path, pw_input, is_child):
                    self._save_pw(Pw(value=pw_input))
                    break
            except PasswordError:
                continue

    def run(self):
        PWhandler.load_all_pws()
        Display.layout_init()
        with Display.live():
            self.set_logger()
            self.control = ControlUnzip(self.path)
            self.update_files_layout()
            sleep(1)
            last_file_name = ""
            for file in self.control.files:
                if file.path.stem == last_file_name and file.path.suffix != ".zip":
                    self.logger.warning(f"Skip {file.path.stem} - 疑似分卷文件，跳过")
                    continue
                with self.control.with_unzip_process(file):
                    self.unzip(file.path)
                self.update_files_layout()
                last_file_name = file.path.stem
            self.logger.success("解压完成")
            sleep(1)


if __name__ == "__main__":
    import argparse
    import os

    import sentry_sdk

    parse = argparse.ArgumentParser()
    path = parse.add_argument("-p", "--path", help="需要解压的文件夹", type=str)
    args = parse.parse_args()
    if args.path:
        if _dsn := os.getenv("SENTRY_DSN"):
            sentry_sdk.init(
                dsn=_dsn,
                traces_sample_rate=1.0,
            )
        DlUnzip(args.path).run()
    else:
        print("请输入需要解压的文件夹")
