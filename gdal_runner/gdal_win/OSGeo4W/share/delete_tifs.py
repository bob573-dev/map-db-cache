from pathlib import Path

def delete_files_by_extension(directory: Path, extension: str):
    extension = extension.lower().lstrip(".")

    for file in directory.iterdir():
        if file.is_file() and file.suffix.lower() == f".{extension}":
            file.unlink()

# приклад використання
delete_files_by_extension(Path("proj"), "tif")

