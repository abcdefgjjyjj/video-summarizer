@echo off
cd /d <project-root>/video-summarizer
echo Starting focused_seq.py at %date% %time% > batch_log.txt
python -u focused_seq.py >> batch_log.txt 2>&1
echo Done at %date% %time% >> batch_log.txt
echo Exit: %ERRORLEVEL% >> batch_log.txt
