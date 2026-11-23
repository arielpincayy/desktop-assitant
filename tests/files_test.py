"""Ejecutar: .venv/bin/python tests/files_test.py"""

import os
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import tools

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    (base / "sub").mkdir()
    (base / "nota.txt").write_text("hola mundo\nhola mundo\n")

    listing = tools.list_dir(str(base))
    assert {entry["name"] for entry in listing} == {"sub", "nota.txt"}, listing
    assert next(e for e in listing if e["name"] == "sub")["type"] == "dir"
    assert "error" in tools.list_dir(str(base / "no-existe"))

    read = tools.read_file(str(base / "nota.txt"))
    assert read["content"] == "hola mundo\nhola mundo\n" and not read["truncated"], read
    assert "app_name" in tools.read_file("CONFIG.py")["content"].lower()

    assert tools.edit_file(str(base / "nota.txt"), "mundo", "all")["replacements"] == 1
    assert (base / "nota.txt").read_text() == "hola all\nhola mundo\n"
    assert (
        tools.edit_file(str(base / "nota.txt"), "mundo", "all", replace_all=True)[
            "replacements"
        ]
        == 1
    )
    assert (base / "nota.txt").read_text() == "hola all\nhola all\n"
    assert tools.edit_file(str(base / "nota.txt"), "no está", "x").get("error")
    assert tools.edit_file(str(base / "nota.txt"), "", "x").get("error")
    assert tools.edit_file(str(base / "no-existe.txt"), "a", "b").get("error")

    assert tools.copy_path(str(base / "nota.txt"), str(base / "copia.txt"))["success"]
    assert (base / "copia.txt").read_text() == "hola all\nhola all\n"
    assert tools.copy_path(str(base / "nota.txt"), str(base / "copia.txt")).get("error")
    assert tools.copy_path(str(base / "sub"), str(base / "sub2"))["success"]
    assert (base / "sub2").is_dir()
    assert tools.copy_path(str(base / "nota.txt"), str(base / "sub"))["success"]
    assert (base / "sub/nota.txt").is_file()

    assert tools.move_path(str(base / "copia.txt"), str(base / "movida.txt"))["success"]
    assert not (base / "copia.txt").exists() and (base / "movida.txt").is_file()
    assert tools.move_path(str(base / "movida.txt"), str(base / "movida.txt")).get("error")
    assert tools.move_path(str(base / "sub2"), str(base / "sub"))["success"]
    assert (base / "sub/sub2").is_dir()

    assert tools.delete_path(str(base / "movida.txt")).get("error")
    assert tools.delete_path(str(base / "movida.txt"), confirm=True)["success"]
    assert not (base / "movida.txt").exists()
    assert tools.delete_path(str(base / "sub/sub2"), confirm=True)["success"]
    assert not (base / "sub/sub2").exists()
    assert tools.delete_path(str(tools.ROOT), confirm=True).get("error")

    assert tools.compress_path(str(base / "nota.txt"), str(base / "nota.zip"))["success"]
    with zipfile.ZipFile(base / "nota.zip") as archive:
        assert "nota.txt" in archive.namelist()
    assert tools.compress_path(str(base / "sub"), str(base / "sub.tar.gz"))["success"]
    with tarfile.open(base / "sub.tar.gz") as archive:
        assert any(item.name.startswith("sub") for item in archive.getmembers())
    assert tools.compress_path(str(base / "nota.txt"), str(base / "nota.zip")).get("error")
    assert tools.compress_path(str(base / "nota.txt"), str(base / "nota.rar")).get("error")

    if os.getuid() != 0:
        locked = base / "bloqueado.txt"
        locked.write_text("hola")
        locked.chmod(0o444)
        try:
            assert "sudo" in tools.edit_file(str(locked), "hola", "adios")["error"]
            assert locked.read_text() == "hola"
        finally:
            locked.chmod(0o644)

print("ok")
