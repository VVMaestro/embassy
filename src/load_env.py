import os

from dotenv import load_dotenv


def load():
    src_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(src_dir)

    for dotenv_path in (
        os.path.join(project_root, ".env"),
        os.path.join(src_dir, ".env"),
    ):
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            break
