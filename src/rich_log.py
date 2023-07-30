import logging
import os
from typing import Callable

from loguru import logger
from loguru._logger import Logger
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

_color_map = {
    "TRACE": "dim blue",
    "DEBUG": "cyan",
    "INFO": "bold",
    "SUCCESS": "bold green",
    "WARNING": "yellow",
    "ERROR": "bold red",
    "CRITICAL": "bold white on red",
}


def _rich_logger_format(record: dict):
    """Log message formatter"""
    lvl_color = _color_map.get(record["level"].name, "cyan")
    return (
        "[not bold green]{time:YYYY/MM/DD HH:mm:ss}[/not bold green] | "
        + f"[{lvl_color}]{{level.name}}[/{lvl_color}]"
        + f"  - [{lvl_color}]{{message}}[/{lvl_color}]"
    )


class LoggerTableHandler(logging.Handler):
    def __init__(
        self,
        log_table: Table,
        layout: Layout,
        log_level: str,
        redraw_func: Callable[[list[str]], Table],
    ):
        super().__init__()
        self.log_table = log_table
        self.log_list = []
        self.layout = layout
        # self.log_format = _rich_logger_format
        self.redraw_func = redraw_func
        self.setLevel(log_level)
        # Could set colors for levels here.

    def emit(self, record):
        msg = self.format(record)
        tsize = os.get_terminal_size().lines // 2
        if len(self.log_list) > tsize:
            self.log_list.append(msg)
            self.log_list.pop(0)
            self.log_table = self.redraw_func(self.log_list)
            self.layout.update(Panel(self.log_table, border_style="red"))
        else:
            self.log_table.add_row(msg)
            self.log_list.append(msg)


def set_rich_logger(
    tabel: Table,
    layout: Layout,
    log_level: str,
    redraw_func: Callable[[list[str]], Table],
) -> Logger:
    """设置一个可以在特定位置显示的logger

    Args:
        tabel (Table): 初始 log table
        layout (Layout): log table 所在的 layout
        log_level (str): log level
        redraw_func (Callable[[list[str]], Table]): 重绘 log table 的方法
    """
    logger.remove()
    logger.add(
        LoggerTableHandler(tabel, layout, log_level, redraw_func),  # type: ignore
        level=log_level,
        enqueue=True,
        format=_rich_logger_format,  # type: ignore
    )
    return logger  # type: ignore


if __name__ == "__main__":
    import random
    from time import sleep

    from rich.console import Console
    from rich.live import Live
    from rich.traceback import install

    def _make_defalut_logger_table() -> Table:
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

    def redraw_logger_table(log_list: list[str]) -> Table:
        """重绘logger table"""
        table = _make_defalut_logger_table()
        for log in log_list:
            table.add_row(log)
        return table

    console = Console()
    install(console=console, show_locals=True)
    table = _make_defalut_logger_table()
    layout = Layout()
    lf = Layout(Panel(table))
    lr = Layout(Panel("right"))
    layout.split_row(lf, lr)
    with Live(layout, console=console, refresh_per_second=10, screen=True):
        logger = set_rich_logger(table, lf, "INFO", redraw_logger_table)
        for _ in range(100):
            sleep(1)
            log = random.choice(["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"])
            getattr(logger, log.lower())(f"this is a {log} log")
