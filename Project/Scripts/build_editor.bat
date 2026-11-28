@echo off
rem Compiles the C++ module of the project (free look, Source\Scenes) for the editor. Close the editor first.
set HTTP_PROXY=
set HTTPS_PROXY=
call "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" ScenesEditor Win64 Development -Project="C:\UnrealScenes\Project\Scenes.uproject" -WaitMutex -NoHotReload
