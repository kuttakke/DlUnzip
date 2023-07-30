from contextlib import contextmanager
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from rich.traceback import install


# 要更新的layout位置
class LayoutName(Enum):
    FILES = "left"
    LOGGER = "right_top"
    PROCESS = "right_bottom"
    NOW_FILE = "now_file"


class make_header:
    """Display header with clock."""

    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            "[b]DlUnzip[/b]",
            datetime.now().ctime().replace(":", "[blink]:[/]"),
        )
        return Panel(grid, style="red on black")


class Display:
    console = Console(height=25)

    install(console=console, show_locals=True)

    layout = Layout(name="root")
    layout_hander = Layout(name="hander", size=3)
    default_logger_table = Table(
        expand=True,
        show_header=False,
        header_style="bold",
        title="[blue][b]Log Messages[/b]",
        highlight=True,
    )
    default_logger_table.add_column("Log Output")
    layout_logger = Layout(Panel(default_logger_table), name="logger", ratio=2)
    layout_files = Layout(name="files")
    layout_now_file = Layout(
        Panel(
            Text(" - ", justify="center", overflow="ellipsis"), border_style="magenta"
        ),
        name="now_file",
    )
    layout_process = Layout(name="process")

    layout.split(layout_hander, Layout(name="main"))
    layout["main"].split_row(layout_files, Layout(name="right"))
    # layout["right"].split_column(layout_logger, layout_process)
    layout["right"].split_column(layout_logger, Layout(name="right_bottom"))
    layout["right_bottom"].split_column(layout_now_file, layout_process)

    _layout_map = {
        LayoutName.FILES: layout_files,
        LayoutName.LOGGER: layout_logger,
        LayoutName.PROCESS: layout_process,
        LayoutName.NOW_FILE: layout_now_file,
    }

    _now_live: Live

    @classmethod
    def layout_init(cls):
        cls.layout_hander.update(make_header())
        # cls.layout_logger.update(Panel(cls.default_logger_table, border_style="red"))
        cls.layout_process.update(Panel("process", border_style="magenta"))

    # live context
    @classmethod
    @contextmanager
    def live(cls):
        """动态显示"""

        with Live(
            cls.layout, console=cls.console, refresh_per_second=10, screen=True
        ) as live:
            cls._now_live = live
            yield live

    @classmethod
    def _make_defalut_logger_table(cls) -> Table:
        """制作默认的logger table"""
        table = Table(
            expand=True,
            show_header=False,
            header_style="bold",
            title="[blue][b]Log Messages[/b]",
            highlight=True,
        )
        table.add_column("Log Output")
        return table

    @classmethod
    def redraw_logger_table(cls, log_list: list[str]) -> Table:
        """重绘logger table"""
        table = cls._make_defalut_logger_table()
        for log in log_list:
            table.add_row(log)
        return table

    @classmethod
    def display(cls, name: LayoutName, panel: Panel):
        """更新layout"""
        cls._layout_map[name].update(panel)

    @classmethod
    def ask_for_password(cls, filename: str) -> str:
        cls._now_live.stop()
        password = Prompt.ask(f"请为{filename}输入密码\n")
        cls._now_live.start()
        return password

    @classmethod
    def is_skip(cls, filename: str) -> bool:
        cls._now_live.stop()
        skip = Confirm.ask(f"是否跳过{filename}？否则停止程序")
        cls._now_live.start()
        return skip
