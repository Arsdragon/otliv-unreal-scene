@echo off
rem Packs scene 1 as a Windows program that plays by itself, without Unreal:  C:\UnrealScenes\Build\Windows\Scenes.exe
rem Close the Unreal editor first (memory). On this laptop it takes long: every shader of the scene is compiled for the game.
rem Log: C:\UnrealScenes\Build\build_log.txt (the last line is the exit code, 0 = packed).
rem The level is saved for the game by rt_bake.prepare_game() - see Scripts\scene1\rt_bake.py.
set UE=C:\Program Files\Epic Games\UE_5.8
rem The PC has HTTP_PROXY set for the VPN client; the packer talks to its local Zen server at [::1] and must not go through it.
rem Only this process is affected. Pass "skipcook" as the first argument to repack what is already cooked.
set HTTP_PROXY=
set HTTPS_PROXY=
set COOK=-cook
if /i "%1"=="skipcook" set COOK=-skipcook
if not exist C:\UnrealScenes\Build mkdir C:\UnrealScenes\Build
call "%UE%\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun -nop4 -utf8output -unattended -nocompileeditor -skipbuildeditor -nocompile -nocompileuat ^
 -project="C:\UnrealScenes\Project\Scenes.uproject" -unrealexe="%UE%\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
 -platform=Win64 -clientconfig=Shipping -installed -build %COOK% -map=/Game/Scene1/L_Otliv -stage -pak -iostore -compressed -prereqs ^
 -archive -archivedirectory="C:\UnrealScenes\Build" -nodebuginfo > C:\UnrealScenes\Build\build_log.txt 2>&1
echo exit code %ERRORLEVEL% >> C:\UnrealScenes\Build\build_log.txt
