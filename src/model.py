from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from rich.spinner import Spinner


class Status(Enum):
    UNDO = "[red]X[/red]"
    DONE = "[green]√[/green]"
    DING = Spinner("dots")


class File(BaseModel):
    name: str
    path: Path
    # G for size > 1000M
    size: str
    size_bytes: int
    status: Status = Status.UNDO
