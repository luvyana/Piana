import subprocess

args = [
    "dotnet",
    "publish",
    "./src/tools/cue4extractor",
    "-c", "Release",
    "--no-self-contained",
    "-r", "win-x64",
    "-f", "net6.0",
    "-o", "./src/tools/",
    "-p:PublishSingleFile=true",
    "-p:PublishSingleFile=true",
    "-p:DebugType=None",
    "-p:GenerateDocumentationFile=false",
    "-p:DebugSymbols=false",
    "-p:AssemblyVersion=4.0.2.0",
    "-p:FileVersion=4.0.2.0"
]

subprocess.call(args)
