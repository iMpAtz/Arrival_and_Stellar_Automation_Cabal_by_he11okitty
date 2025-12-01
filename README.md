# stellarlink_auto_imprint-OCR

## USE THIS AT YOUR OWN RISK!

In case you want to compile it yourself into an .exe file:
 1. Install Python on your system: https://www.geeksforgeeks.org/how-to-install-python-on-windows/
 2. Convert a Python Script to an executable file
     - open powershell where cloned repository is and run `pyinstaller main.spec`


## How to use
 1. If you're using some unusual font in the game, change it to Tahoma (Esc -> options -> preferences -> font)
 2. Download .exe file
 3. Open the application as administrator (important, otherwise it cannot access the cabal window)
 4. Define reading area
    - press 'Define area' button
    - information prompt with additional instructions will appear, press 'Ok' to proceed
    - press and hold LMB (left mouse button) drag it acress to opposite corner
    - information prompt will appear with info if you have done it correctly or not
    - if it wasn't defined correctly, please repeat
    - if it was defined correctly, after pressing 'Ok' in the last information prompt - red border will appear around the selected area - it is there to tell you if the area is in the right place or not
 5. Define phrase1 and phrase2
    1. phrase1 stands for stellar, for example: Penetration
       - it is required
       - make sure that the name you have typed in correct
       - you can input only letters and white chars (spacebar)
    2. phrase2 stands for stellar force, for example: +15
       - is not required
       - you can input only digits
       - on the right side of the input is checkbox that enables or disables phrase2 input
         - if it is enabled, application will run untill both phrase1 and phrase2 is found
         - if its disabled, application will check only for phrase1 (example in the youtube video linked bellow)
       - if the value found by the application is greater than the phrase2 value - it will stop aka you got what you've been looking for
 6. Press 'Start' button
 7. Move your cursor to where 'Imprint' button is within the game (stellar link screen)
 8. Now application will continously read what you have got and keeps pressing 'LMB' untill it find what you have been looking for or untill u stop it manualy by pressing 'Stop' button.

# Important notes
- application will create folder that will store all the logs in your home directory C:\Users\YOUR_COMPUTER_NAME\stellarlink_logs, it is for both user and developer use to track exceptions and what values have been found by OCR
- always use it on main screen - if you have 2 screens plugged and you move the app to the second screen then the software will print wrong area coordinates - it has to be done on main screen
- why is the .exe file so big - because it includes all the additional required files like whole OCR (https://github.com/tesseract-ocr/tesseract)
- how is it working?
  - application takes screenshot of the area that you have defined
  - OCR then gets all the strings that are one the photo and returns to app
  - then application processes this data - if it's legit and contains the phrases
  - next step is either success or repeat the process
- **I would highly recommend to watch the showcase video and pay attention to the area definition and state of stellar window**
 
If you have any questions or need assistance contact me on Discord (aquazz) or hit me up ingame (Revolwer).

youtube example usage video: https://youtu.be/0KVkZXdlfyY

Incase you're not a part of PlayCabal community, here is my referral link: https://playcabal.to/referral/3055
