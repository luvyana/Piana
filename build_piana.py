import shutil
import os
import pathlib
from pathlib import Path
from shutil import rmtree
import sys


addon_name = "Piana"
addon_version = sys.argv[1]
addon_filename = addon_name + "-" + addon_version


def remove(path: str):
    """
    Remove a file
    """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        rmtree(path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(path))


def main():

    cwd = Path(os.getcwd())
    build_folder = Path(os.path.join(os.path.dirname(__file__), addon_name))
    src_folder = Path(os.path.join(os.path.dirname(__file__), "src"))

    # TODO : Make this work in Github Actions
    # Build cue4extractor
    # subprocess.call([
    #     "dotnet",
    #     "publish",
    #     "./src/tools/cue4extractor",
    #     "-c", "Release",
    #     "--no-self-contained",
    #     "-r", "win-x64",
    #     "-f", "net6.0",
    #     "-o", "./src/tools/",
    #     "-p:PublishSingleFile=true",
    #     "-p:PublishSingleFile=true",
    #     "-p:DebugType=None",
    #     "-p:GenerateDocumentationFile=false",
    #     "-p:DebugSymbols=false",
    #     "-p:AssemblyVersion=4.0.2.0",
    #     "-p:FileVersion=4.0.2.0"
    # ])

    [p.unlink() for p in pathlib.Path(".").rglob("*.py[co]")]
    [p.rmdir() for p in pathlib.Path(".").rglob("__pycache__")]

    if not build_folder.exists():
        build_folder.mkdir(parents=True)

    shutil.copytree(src_folder, build_folder, dirs_exist_ok=True)

    # Remove unwanted files
    remove(os.path.join(build_folder, "tools", "cue4extractor"))
    remove(os.path.join(build_folder, ".vscode"))
    remove(os.path.join(build_folder, "assets", "VALORANT_Agent_LV.blend"))
    remove(os.path.join(build_folder, "assets", "VALORANT_Agent.blend"))
    remove(os.path.join(build_folder, "assets", "VALORANT_Weapon.blend"))

    shutil.make_archive(
        base_name=addon_filename,
        format="zip",
        root_dir=cwd.__str__(),
        base_dir=addon_name,
    )


if __name__ == "__main__":
    main()
