
Follow these step-by-step instructions to get the automation script running on your machine.

1. Prerequisites

Python 3.x: You must have Python installed on your computer. If you don't have it, download it from python.org.

Google Chrome: The script is configured to use the Chrome browser, so you need to have it installed.

PIP: Python's package installer, which usually comes with Python. You'll need it to install the libraries.

2. Setup and Installation

Step 2a: Download the Code
Download the script and save it to a folder on your computer.

Step 2b: Install Required Libraries
This script depends on selenium for browser automation and webdriver-manager to automatically handle the browser driver.

Open your terminal (Command Prompt on Windows, or Terminal on macOS/Linux) and run the following command to install these libraries:[1][2]

**
pip install selenium webdriver-manager
**

This command will download and install the necessary packages for the script to work.[3][4][5]

Step 2c: Create the questions.txt File
In the same folder where you saved the Python script, create a new text file named questions.txt.

Inside this file, add the questions you want the bot to ask. Place each question on a new line.

Example questions.txt:

What are the primary benefits of using a large language model?
Explain the difference between supervised and unsupervised learning.
Summarize the plot of the movie "Inception".

Note: If you forget this step, the script will automatically create a questions.txt file for you with two sample questions.

3. Running the Script

Step 3a: Execute the Script
Navigate to the script's directory in your terminal and run the script using Python:


python your_script_name.py

(Replace your_script_name.py with the actual name of the Python file.)

Step 3b: Log In Manually (First-Time Setup)
When you run the script for the first time, a new Chrome browser window will open and navigate to the AI website.

The script will pause, and you will see a prompt in the terminal asking if you are logged in.


👤 Are you logged in? (yes/no):

At this point, you need to manually log in or sign up on the website within the opened Chrome window. This is a one-time action. The script saves your session in a chrome_profile folder, so you won't need to log in again on subsequent runs.

Step 3c: Confirm and Start Automation
After you have successfully logged in, go back to the terminal, type yes, and press Enter.

The automation will now begin. The bot will start asking the questions from your questions.txt file one by one. You can sit back and watch it work.

4. Stopping and Resuming

You can stop the script at any time by pressing Ctrl+C in the terminal. The script is designed to save its progress. The next time you run the script, it will automatically resume from the last question it was about to ask.

