# Pokemon Catching Guide

A tracker/catching guide to assist in completing the Pokedex in each generation of mainline Pokemon games written in Python as a Streamlit app. This app is hosted on the Streamlit Community Cloud, and can be found at this link:

https://pokedex-completion-planner.streamlit.app/

Since every generation of Pokemon games require trading between multiple games to complete the Pokedex, I created this tracker as a way to help plan and carry out the completion of the Pokedex in each generation.
In each dataframe, the Pokemon's name, number, and the location within each game it can be caught in is included. I've also included a "Planned Game" column, where you can write down in which game you plan to catch the Pokemon.
This column is saved, and the location of the Pokemon in the selected game is displayed in the "Planned Catches" tab. This provides a convenient place for you to see where you want to catch each Pokemon within a generation of games.

An important note: The planned game column is reset every time the generation is changed. If you want to save this data and switch the viewer to a different generation, please save the pokedex and reload it when you want to return to that particular generation.

## Search Options
Below is an outline of the search options available.

### Generation
Switch back and forth between the different generations. This reloads the entire dataset, and will give a fresh "Planned Game" column every time a new generation is selected.

### Get Pokemon in (Blank) Game(s) but not (Blank) Game(s)
This option lets you pick which Pokemon appear based on which games they appear in. In the first dropdown menu, if "All of" is selected, only Pokemon that appear in all of the games listed will be returned in the search. If "At least one of" is selected, Pokemon that appear in any one of the games chosen will appear.

For example, Lunatone will appear if Ruby and Sapphire are selected and the "At least one of," option is chosen, since it appears in Sapphire, but it will not appear if "All of" is selected, since it does not appear in Ruby.

In the second dropdown menu, any Pokemon that appear in the games you choose will *not* appear.

For example, if Ruby is selected in the first dropdown menu and Emerald is selected in the second, then Roselia will appear, since it appears in Ruby but not Emerald.
### Keywords
This ensures only Pokemon whose location includes the included keywords appear. For example, if "Route 1" is in the textbox, only Pokemon found in Route 1 will appear in the search.
Note that this only searches within the locations of each game, and not in the Pokemon name itself. If you want to search for a particular Pokemon, I recommend using the dataframe's search feature, described below.
### Searching Within Dataframe
If you want to search within a returned dataframe (e.g. for a specific Pokemon), you can use the built in searchbar feature. Click on the magnifying glass in the upper righthand corner of the dataframe, and type the terms you wish to search for. 
This will find matching words in any cells of the dataframe.
## Saving and Reloading
To save the "Planned Games" dataframe, click on the "Download Save File." This will save a copy of the "Planned Catches" tab as a .csv file which can then be opened in a spreadsheet application of your choice, such as Excel or Google Sheets.
To save the full dataframe on the "Full Pokedex" tab, click on the download button in the upper right hand corner of the dataframe. 

To reload a previous dataset, use the "Upload" file button to select a previously downloaded file. This should be a "Planned Catches" .csv that you have downloaded from a previous instance. 
Note that the generation selected needs to match the file prior to upload, otherwise the file will not load.
