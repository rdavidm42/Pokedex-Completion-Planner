import pandas as pd
import streamlit as st
import uuid
from pathlib import Path
from sql_queries import query_database, get_games

st.set_page_config(layout="wide")
    
def update_value(entry,erase_all):
    save_caught()
    if erase_all == 'Unassigned Games':
        mask = (st.session_state.df['Caught?'] == "None") & (st.session_state.df.index.isin(st.session_state.search_index))
    else:
        mask = st.session_state.df.index.isin(st.session_state.search_index)
    st.session_state.df.loc[mask, 'Caught?'] = entry
    st.session_state.caught = st.session_state.df['Caught?']
    st.session_state.dek = str(uuid.uuid4())

def save_caught(): 
    st.session_state.df.loc[st.session_state.caught.index, 'Caught?'] = st.session_state.caught
    st.session_state.caught = st.session_state.df['Caught?']
    
def main():
    
    # Initialize session_state variables
    
    if 'df' not in st.session_state:
        st.session_state.df = query_database(1,[])
        st.session_state.df.insert(1,'Caught?',"None")
    if 'caught' not in st.session_state:
        st.session_state.caught = st.session_state.df['Caught?']
    if 'file' not in st.session_state:
        st.session_state.file = True
    if 'dek' not in st.session_state:
        st.session_state.dek = str(uuid.uuid4())
    if 'gen' not in st.session_state:
        st.session_state.gen = 1
    if 'mode' not in st.session_state:
        st.session_state.mode = 1
    if 'search_index' not in st.session_state:
        st.session_state.search_index = st.session_state.df.index
    # if 'csv' not in st.session_state:
    #     st.session_state.csv = st.session_state.df.to_csv()
    st.title('Gotta Catch \'Em All!')
    generations = ['Generation I',
               'Generation II',
               'Generation III',
               'Generation IV',
               'Generation V',
               'Generation VI',
               'Generation VII',
               'Generation VIII',
               'Generation IX']
    generation_dictionary = {generations[i]:i+1 for i in range(len(generations))}
    #Define buttons and options
    games_list = get_games(st.session_state.gen)
    with st.sidebar:
        st.session_state.gen = generation_dictionary[st.selectbox('Select Generation:',generations)]
        if st.session_state.gen != st.session_state.mode:
            games_list = get_games(st.session_state.gen)
            st.session_state.df = query_database(st.session_state.gen,[])
            st.session_state.df.insert(1,'Caught?',"None")
            st.session_state.caught = st.session_state.df['Caught?']
            st.session_state.mode = st.session_state.gen           
    
    with st.sidebar.form('search_form'):
        button = st.radio('Get Pokemon that are in',['all of','at least one of'],horizontal=True)
        game = st.multiselect("",games_list,label_visibility='collapsed')    
        game_not = st.multiselect("But not in:",games_list,)
        
        search_bar = st.text_input('Keywords')
        st.form_submit_button("Search",on_click = save_caught)

    #Load Dataframe based on options
    if game and button == 'all of':
        search_df = query_database(st.session_state.gen,
                                   game,game_not,
                                   search_term=search_bar,
                                   inclusive = False)
        
    elif game and button == 'at least one of':
        search_df = query_database(st.session_state.gen,
                                   game,game_not,
                                   search_term=search_bar,
                                   inclusive = True)
        
    else:
        search_df = query_database(st.session_state.gen,[],
                                   search_term=search_bar,
                                   inclusive = True)
    
    search_df.insert(1, 'Caught?', st.session_state.df.loc[search_df.index, 'Caught?'])
    st.session_state.search_index = search_df.index 
    #Report back the dataframe

    # editor = st.data_editor(
    #     search_df,
    #     key = st.session_state.dek,
    #     column_config = {
    #             "Caught?":st.column_config.CheckboxColumn(
    #             None,
    #             help="Select which Pokemon you've already caught",
    #             default=False,
    #         )
    #     },
    #     disabled = ('No.','Pokemon',*games_list)       
    # )
    tab1, tab2 = st.tabs(["Full Pokedex","Planned Catches"],on_change = save_caught)
    with tab1:
        st.write(f'Total Pokemon found: {len(search_df)}')
        editor = st.data_editor(
            search_df,
            key = st.session_state.dek,
            column_config = {
                    "Caught?":st.column_config.SelectboxColumn(
                    "Planned Game",
                    help="Select which game you plan to catch the Pokemon in",
                    options = ["None"]+games_list,
                    required = True
                )
            },
            disabled = ('No.','Pokemon',*games_list)       
        )
            # clear_button = st.button('Clear \"Caught?\" Column',on_click=update_value)
        apply_game = st.selectbox("Planned Game",["None"] + games_list,index=None,
                                placeholder="Planned game to assign to all empty cells",
                                accept_new_options=False)
        assign_option = st.radio('Apply to',['Unassigned Games','All Games'],horizontal=True)
        apply_button = st.button(
            'Apply game to "Planned Game" Column',
            on_click=update_value,
            args=(str(apply_game),assign_option),
            disabled=apply_game is None
        )
    
        #Record the changes to the dataframe
        st.session_state.caught = pd.Series(
            [x['Caught?'] for x in list(st.session_state[st.session_state.dek]["edited_rows"].values())],
            index=editor.index[list(st.session_state[st.session_state.dek]["edited_rows"].keys())])

    with st.sidebar:
        caught_export = st.session_state.df[['Pokemon','Caught?']].copy()
        locations = [
            st.session_state.df.iloc[i][caught_export['Caught?'].iloc[i]]
            if caught_export['Caught?'].iloc[i] != "None"
            else "None"
            for i in range(len(st.session_state.df))
        ]
        caught_export.index.name = 'No.'
        caught_export["Location"] = locations
        caught_export.rename(columns = {"Caught?":"Game"},inplace=True)
        download_button = st.sidebar.download_button(
        label="Download Save File",
        data=caught_export.to_csv(),
        file_name= 'Generation ' + str(st.session_state.gen) + " pokedex.csv",
        mime="text/csv",
        on_click = save_caught
        )
        uploaded_file = st.file_uploader("Load a Previous Tracker")

    with tab2:
        caught_export = st.session_state.df[['Pokemon','Caught?']].copy()
        locations = [
            st.session_state.df.iloc[i][caught_export['Caught?'].iloc[i]]
            if caught_export['Caught?'].iloc[i] != "None"
            else "None"
            for i in range(len(st.session_state.df))
        ]
        caught_export.index.name = 'No.'
        caught_export["Location"] = locations
        caught_export.rename(columns = {"Caught?":"Game"},inplace=True)
        st.dataframe(data=caught_export)

    #Get uploaded file, if available 
    if uploaded_file is not None and st.session_state.file:
        if Path(uploaded_file.name).suffix != '.csv':
            st.write(f'File type is {Path(uploaded_file.name).suffix}, needs to be .csv!')
        else:
            uploaded_df = pd.read_csv(uploaded_file, index_col='No.').rename(columns = {'Game':"Caught?"})
            if 'Caught?' not in uploaded_df.columns:
                st.write('File does not contain a "Caught?" column.')
            elif not uploaded_df.index.isin(st.session_state.df.index).all():
                st.write('Pokémon numbers do not match the current generation.')
            else:
                st.session_state.df['Caught?'] = "None"
                st.session_state.df.loc[uploaded_df.index, 'Caught?'] = uploaded_df['Caught?']
                st.session_state.caught = st.session_state.df['Caught?']
                st.session_state.dek = str(uuid.uuid4())
                st.session_state.file = False
                st.rerun()
    elif uploaded_file is None:
        st.session_state.file = True

if __name__ == "__main__":
    main()