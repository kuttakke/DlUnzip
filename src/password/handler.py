from pathlib import Path

from pydantic import BaseModel

from util.rjcode import get_rjcode


class Pw(BaseModel):
    value: str


class AllPws(BaseModel):
    passwords: list[Pw]


class PWhandler:
    password_file = Path(__file__).parent / "passwords.json"
    all_pws = AllPws(passwords=[])

    @classmethod
    def load_all_pws(cls):
        if cls.password_file.exists():
            cls.all_pws = AllPws.parse_file(cls.password_file)
        else:
            cls.password_file.touch()
            cls.password_file.write_text(cls.all_pws.json())

    @classmethod
    def save_to_file(cls):
        cls.password_file.write_text(cls.all_pws.json())

    @classmethod
    def add_pw(cls, pw: str):
        # check existing passwords
        for p in cls.all_pws.passwords:
            if p.value == pw:
                return False
        # add new password
        cls.all_pws.passwords.append(Pw(value=pw))
        cls.save_to_file()

    @classmethod
    def get_all_pws(cls, filename: str | None = None):
        all_pws = cls.all_pws.passwords.copy()
        if filename:
            if rjcode := get_rjcode(filename):
                all_pws.extend([Pw(value=f"RJ{rjcode}"), Pw(value=f"rj{rjcode}")])
        return all_pws
