from contextlib import contextmanager
from pathlib import Path

from display import Display, LayoutName
from model import File, Status
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Column, Table
from rich.text import Text


class ControlUnzip:
    def __init__(self, path: Path | str) -> None:
        self.path = path if isinstance(path, Path) else Path(path)
        self.files = self._get_files()
        self._now_process: Progress
        self._now_task: TaskID
        self._now_file: File
        self._now_total: int

    def _format_file_size(self, size: int) -> str:
        if size > 1000 * 1024 * 1024:
            return f"{(size / 1024 / 1024 / 1024):.0f} GB"
        return f"{(size / 1024 / 1024):.0f} MB"

    def _get_files(self) -> list[File]:
        return [
            File(
                name=file.name,
                path=file,
                size=self._format_file_size(file.stat().st_size),
                size_bytes=file.stat().st_size,
            )
            for file in self.path.iterdir()
            if file.is_file()
        ]

    def to_panel(self) -> Panel:
        tb = Table(
            "序号",
            "文件名",
            "大小",
            "状态",
            title="文件列表",
            show_header=True,
            header_style="bold",
            highlight=True,
            expand=True,
        )
        done_count = 0
        ids = 0
        for ids, file in enumerate(self.files, 1):
            tb.add_row(str(ids), file.name, file.size, file.status.value)
            if file.status == Status.DONE:
                done_count += 1
        title = f"剩余{ids - done_count}，共{ids}" if ids else "没有文件需要解压"
        return Panel(
            # Align.center(tb, vertical="middle"),
            tb,
            title=f"[magenta][b]{title}[/b]",
            border_style="magenta",
        )

    def _make_base_process(self):
        text_column = TextColumn("{task.description}")
        bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
        self._now_process = Progress(
            SpinnerColumn(),
            text_column,
            "•",
            FileSizeColumn(),
            bar_column,
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            expand=True,
        )

    @contextmanager
    def with_unzip_process(self, file: File):
        self._make_base_process()
        self._now_task = self._now_process.add_task("0%", total=file.size_bytes)
        self._now_file = file
        self._now_file.status = Status.DING
        self._now_total = file.size_bytes
        Display.display(LayoutName.FILES, self.to_panel())
        progress_table = Table.grid(expand=True)
        progress_table.add_row(
            Panel(
                self._now_process,
                border_style="green",
            )
        )
        Display.display(LayoutName.PROCESS, Panel(progress_table))
        yield
        self._now_file.status = Status.DONE
        Display.display(LayoutName.FILES, self.to_panel())
        self._now_process.stop()

    def update_process(
        self,
        completed: int,
        total: int = 0,
        filename: str = "",
    ):
        """更新进度条, filename 为压缩包中的文件名"""
        if filename:
            filename = Path(filename.replace("/", "\\")).name
            Display.display(
                LayoutName.NOW_FILE,
                Panel(
                    Text(filename, justify="center", overflow="ellipsis"),
                    border_style="magenta",
                ),
            )
        if total and total != self._now_total:
            self._now_total = total
            self._now_process.update(
                self._now_task,
                total=self._now_total,
                completed=completed / 100 * self._now_total,
                description=f"{completed}% ",
            )
        self._now_process.update(
            self._now_task,
            completed=completed / 100 * self._now_total,
            description=f"{completed}% ",
        )
