# Windows EXE build

This folder contains helper scripts for building and smoke-testing a Windows executable.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1
```

The default output is:

```text
dist\aircraft-design\aircraft-design.exe
```

For a single-file experimental build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1 -OneFile
```

## Smoke checks

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_windows_exe.ps1
```

To also launch the GUI as part of the check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_windows_exe.ps1 -LaunchGui
```
