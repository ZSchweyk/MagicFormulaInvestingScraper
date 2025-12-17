# About
This program logs in to [magicformulainvesting.com](https://www.magicformulainvesting.com), and runs/saves the results from the heavily backtested and market beating algorithm covered in The Little Book That Still Beats The Market by Joel Greenblatt.  

It is easily customizable for different user credentials and input preferences, and allows a programmatic approach to running and saving the algorithm and its results for analysis or personal use. This was the main motivation behind why I created this script. Obviously, it is not intended to be used for commercial purposes which is against the Terms of Service.  

If you find any value in it and are interested in more extensive investing or trading related programs I've written, specifically with options, feel free to contact me at zeyn@schweyk.com.
# Setup
Create, activate, and initialize a virtual environment with all necessary dependencies:
```
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```

# Run Instructions
Run the following to set your credentials to [magicformulainvesting.com](https://www.magicformulainvesting.com)  
```
set MFI_EMAIL=your@email.com
set MFI_PASSWORD="your-password"
```
If you'd like to set these more permanently, look into the `SETX` command on Windows, or simply consider making Python variables that contain your credentials (make sure git does not track these).  

Then, run the program with
```
python main.py --min-mcap 50 --num-stocks 50 --headless
```
`--num-stocks` - default is 50  
`--min-mcap` - in millions... default is 1000  
Remove `--headless` if you want to see the web browser (Firefox) open up  

# Results
The script will generate two files in the `results/` directory, one `.csv` and one `.json` named with the same timestamp of the run. The `.json` file will contain inputs for the run for future reference.  

Examples are shown in the `results/` folder :)