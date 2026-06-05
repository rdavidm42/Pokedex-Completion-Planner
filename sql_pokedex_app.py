"""
sql_pokedex_app.py
------------------
Streamlit app for tracking Pokémon catches across all nine generations.

Users can filter Pokémon by game availability, assign a planned catch
game to each entry (individually or in bulk), and download/upload save
files to continue their progress across sessions.

Data is sourced from a SQLite database via sql_queries.py. User state
(planned game assignments) is held in st.session_state and is not
written back to the database to ensure compatibility with the Streamlit Community Cloud.

Dependencies
------------
- streamlit
- pandas
- re
- json
- sqlalchemy (used internally by st.connection)
- sql_queries.py (local module)
- game_order.json (static game ordering config)
- .streamlit/secrets.toml (database connection config)
"""

import pandas as pd
import streamlit as st
import uuid
from pathlib import Path
from sql_queries import query_database, get_games

st.set_page_config(layout="wide")


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def update_value(entry, erase_all):
    """
    Bulk-assign a planned game to Pokémon in the current filtered view.

    Flushes any pending manual edits first via save_caught(), then
    applies the assignment either to unassigned rows only or to all
    rows in the current search results, depending on the erase_all flag.

    Parameters
    ----------
    entry : str
        Game name to assign (e.g. "Red"), or "None" to clear.
    erase_all : str
        "Unassigned Games" to skip already-assigned rows;
        any other value overwrites all rows in the current view.
    """
    save_caught()
    if erase_all == 'Unassigned Games':
        # Only target rows within the current filter that have no assignment yet
        mask = (
            (st.session_state.df['Caught?'] == "None") &
            (st.session_state.df.index.isin(st.session_state.search_index))
        )
    else:
        # Overwrite all rows in the current filtered view
        mask = st.session_state.df.index.isin(st.session_state.search_index)

    st.session_state.df.loc[mask, 'Caught?'] = entry
    st.session_state.caught = st.session_state.df['Caught?']
    st.session_state.dek = str(uuid.uuid4())  # force data editor reset


def save_caught():
    """
    Adds data editor changes into the master session state DataFrame.

    st.session_state.caught holds only the rows that were edited in the
    current render cycle. This function merges those partial edits back
    into the full DataFrame (st.session_state.df), then refreshes
    st.session_state.caught to reflect the complete current state.

    """
    st.session_state.df.loc[st.session_state.caught.index, 'Caught?'] = st.session_state.caught
    st.session_state.caught = st.session_state.df['Caught?']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_export_df():
    """
    Build a summary DataFrame suitable for download or display.

    Looks up the encounter location for each Pokémon's assigned game,
    producing a DataFrame with columns: Pokemon, Game, Location.

    Returns
    -------
    pd.DataFrame
        Indexed by Pokédex number ('No.'), with 'Pokemon', 'Game', and
        'Location' columns. Rows with no assigned game show "None" for
        both Game and Location.
    """
    export = st.session_state.df[['Pokemon', 'Caught?']].copy()
    export.index.name = 'No.'

    # Vectorised location lookup: for each assigned game, read the
    # corresponding location cell from the master DataFrame
    mask = export['Caught?'] != "None"
    locations = pd.Series("None", index=export.index)
    for idx, game in export.loc[mask, 'Caught?'].items():
        locations.loc[idx] = st.session_state.df.loc[idx, game]

    export["Location"] = locations
    export.rename(columns={"Caught?": "Game"}, inplace=True)
    return export


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """
    Entry point for the Streamlit app.

    Initialises session state, renders the sidebar controls (generation
    selector, game filters, search, download/upload), and displays the
    main tabbed interface (Full Pokédex editor + Planned Catches summary).
    """

    # --- Session state initialisation ---

    if 'df' not in st.session_state:
        # Master DataFrame holding all Pokémon for the current generation,
        # plus the user's planned game assignments in 'Caught?'
        st.session_state.df = query_database(1, [])
        st.session_state.df.insert(1, 'Caught?', "None")

    if 'caught' not in st.session_state:
        # Partial Series of edited rows from the data editor; merged into
        # df by save_caught() before any bulk operation
        st.session_state.caught = st.session_state.df['Caught?']

    if 'file' not in st.session_state:
        # Guard flag to ensure an uploaded file is only processed once
        st.session_state.file = True

    if 'dek' not in st.session_state:
        # Unique key for the data editor; refreshed to force a re-render
        # after bulk updates or generation changes
        st.session_state.dek = str(uuid.uuid4())

    if 'gen' not in st.session_state:
        st.session_state.gen = 1

    if 'mode' not in st.session_state:
        # Tracks the last rendered generation to detect changes
        st.session_state.mode = 1

    if 'search_index' not in st.session_state:
        # Index of the currently visible (filtered) Pokémon; used by
        # update_value() to scope bulk assignments to the current view
        st.session_state.search_index = st.session_state.df.index

    st.title('Gotta Catch \'Em All!')

    generations = [
        'Generation I', 'Generation II', 'Generation III',
        'Generation IV', 'Generation V', 'Generation VI',
        'Generation VII', 'Generation VIII', 'Generation IX'
    ]
    generation_dictionary = {gen: i + 1 for i, gen in enumerate(generations)}

    # --- Sidebar: generation selector ---
    games_list = get_games(st.session_state.gen)
    with st.sidebar:
        st.session_state.gen = generation_dictionary[
            st.selectbox('Select Generation:', generations)
        ]
        if st.session_state.gen != st.session_state.mode:
            # Generation changed: reload master DataFrame and reset state
            games_list = get_games(st.session_state.gen)
            st.session_state.df = query_database(st.session_state.gen, [])
            st.session_state.df.insert(1, 'Caught?', "None")
            st.session_state.caught = st.session_state.df['Caught?']
            st.session_state.mode = st.session_state.gen

    # --- Sidebar: search / filter form ---
    with st.sidebar.form('search_form'):
        button = st.radio(
            'Get Pokemon that are in',
            ['all of', 'at least one of'],
            horizontal=True
        )
        game = st.multiselect("", games_list, label_visibility='collapsed')
        game_not = st.multiselect("But not in:", games_list)
        search_bar = st.text_input('Keywords')
        st.form_submit_button("Search", on_click=save_caught)

    # --- Build filtered DataFrame ---
    # Query parameters determine which SQL filter mode to use
    if game and button == 'all of':
        search_df = query_database(
            st.session_state.gen, game, game_not,
            search_term=search_bar, inclusive=False
        )
    elif game and button == 'at least one of':
        search_df = query_database(
            st.session_state.gen, game, game_not,
            search_term=search_bar, inclusive=True
        )
    else:
        search_df = query_database(
            st.session_state.gen, [],
            search_term=search_bar, inclusive=True
        )

    # Inject current planned game assignments from master df into the filtered view
    search_df.insert(1, 'Caught?', st.session_state.df.loc[search_df.index, 'Caught?'])

    # Persist the filtered index so update_value() can scope bulk assignments
    st.session_state.search_index = search_df.index

    # --- Main tabs ---
    tab1, tab2 = st.tabs(["Full Pokedex", "Planned Catches"], on_change=save_caught)

    with tab1:
        st.write(f'Total Pokemon found: {len(search_df)}')

        # Render editable table with a selectbox for planned game assignment
        editor = st.data_editor(
            search_df,
            key=st.session_state.dek,
            column_config={
                "Caught?": st.column_config.SelectboxColumn(
                    "Planned Game",
                    help="Select which game you plan to catch the Pokemon in",
                    options=["None"] + games_list,
                    required=True
                )
            },
            disabled=('No.', 'Pokemon', *games_list)
        )

        # --- Bulk assignment controls ---
        apply_game = st.selectbox(
            "Planned Game",
            ["None"] + games_list,
            index=None,
            placeholder="Planned game to assign to all empty cells",
            accept_new_options=False
        )
        assign_option = st.radio(
            'Apply to',
            ['Unassigned Games', 'All Games'],
            horizontal=True
        )
        st.button(
            'Apply game to "Planned Game" Column',
            on_click=update_value,
            args=(str(apply_game), assign_option),
            disabled=apply_game is None  # prevent accidental no-op submissions
        )

        # Capture only the rows edited this render cycle; save_caught() will
        # merge these into the master df before the next bulk operation
        st.session_state.caught = pd.Series(
            [x['Caught?'] for x in st.session_state[st.session_state.dek]["edited_rows"].values()],
            index=editor.index[list(st.session_state[st.session_state.dek]["edited_rows"].keys())]
        )

    # --- Sidebar: download / upload ---
    with st.sidebar:
        export_df = build_export_df()
        st.sidebar.download_button(
            label="Download Save File",
            data=export_df.to_csv(),
            file_name='Generation ' + str(st.session_state.gen) + " pokedex.csv",
            mime="text/csv",
            on_click=save_caught
        )
        uploaded_file = st.file_uploader("Load a Previous Tracker")

    with tab2:
        # Display a read-only summary of planned catches grouped by game
        st.dataframe(data=build_export_df())

    # --- File upload handling ---
    # Processed only once per upload thanks to the st.session_state.file guard
    if uploaded_file is not None and st.session_state.file:
        if Path(uploaded_file.name).suffix != '.csv':
            st.write(f'File type is {Path(uploaded_file.name).suffix}, needs to be .csv!')
        else:
            # Rename 'Game' back to 'Caught?' to match internal column name
            uploaded_df = pd.read_csv(uploaded_file, index_col='No.').rename(
                columns={'Game': 'Caught?'}
            )
            if 'Caught?' not in uploaded_df.columns:
                st.write('File does not contain a "Caught?" column.')
            elif not uploaded_df.index.isin(st.session_state.df.index).all():
                st.write('Pokémon numbers do not match the current generation.')
            else:
                # Reset and merge uploaded assignments into master df
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
