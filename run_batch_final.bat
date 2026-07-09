@echo off
cd /d <project-root>/video-summarizer
echo ============================================ > batch_final.log
echo Started at %date% %time% >> batch_final.log
echo ============================================ >> batch_final.log
python -u batch_master.py >> batch_final.log 2>&1
echo ============================================ >> batch_final.log
echo Finished at %date% %time% >> batch_final.log
echo ============================================ >> batch_final.log
