@echo off
REM Lanceur automatique du pipeline RTE Energy & Meteo
cd /d "%~dp0"
uv run rte-energy
