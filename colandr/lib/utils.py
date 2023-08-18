import pathlib


def to_path(path: str | pathlib.Path) -> pathlib.Path:
    if isinstance(path, pathlib.Path):
        return path
    elif isinstance(path, str):
        return pathlib.Path(path)
    else:
        raise TypeError()
