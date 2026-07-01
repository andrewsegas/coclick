HOW TO BUNDLE TESSERACT INTO COCLICK
====================================

To ship CoClick so friends do NOT need to install Tesseract, drop a Tesseract
build into THIS folder before running build.ps1.

Steps (one-time, on your build machine):

1. Install Tesseract-OCR from the UB-Mannheim build:
     https://github.com/UB-Mannheim/tesseract/wiki
   Default install path is usually:
     C:\Program Files\Tesseract-OCR

2. Copy the CONTENTS of that install folder into this folder
   (vendor\tesseract\) so that you end up with:

     vendor\tesseract\tesseract.exe
     vendor\tesseract\*.dll                 (leptonica / tesseract DLLs)
     vendor\tesseract\tessdata\eng.traineddata

   You only need eng.traineddata (the bot reads digits), so you can delete the
   other .traineddata files under tessdata\ to keep the download small.

3. Run  .\build.ps1  from the project root.

At runtime, bot_engine.py points pytesseract at vendor\tesseract\tesseract.exe
(bundled under "tesseract\" inside the exe). If this folder is empty, the build
still succeeds but the exe falls back to a system-installed Tesseract.

NOTE: Tesseract is licensed under Apache-2.0. Keep its LICENSE file alongside
the binary when you redistribute.
