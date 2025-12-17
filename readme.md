# Setup
Run the following to set your credentials to [magicformulainvesting.com](https://www.magicformulainvesting.com)  
```
set MFI_EMAIL=your@email.com
set MFI_PASSWORD="your-password"
```
Source/activate your virtual environment. Be sure to install dependencies.  

# Run Instructions
```
python main.py --min-mcap 50 --num-stocks 50 --headless
```
`--num-stocks` - default is 50  
`--min-mcap` - in millions... default is 1000  
Remove `--headless` if you want to see the web browser (Firefox) open up  

# Details
The script will generate two files in the `results/` directory, one `.csv` and one `.json` named with the same timestamp of the run. The `.json` file will contain inputs for the run for future reference.