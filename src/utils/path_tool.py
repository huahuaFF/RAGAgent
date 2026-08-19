from pathlib import Path


def get_project_root() -> str:
    return str(Path(__file__).resolve().parents[2])


def get_abs_path(relative_path: str) -> str:
    path = Path(relative_path)
    if path.is_absolute():
        return str(path)
    return str(Path(get_project_root()) / path)


if __name__ == "__main__":
    print(get_abs_path("config/config.txt"))
