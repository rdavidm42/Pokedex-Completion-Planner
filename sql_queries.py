"""
sql_queries.py
--------------
Database access layer for the Pokédex Streamlit app.

Handles all SQLite queries via Streamlit's connection API, including
filtered Pokémon lookups by game availability and keyword search.
The database connection is managed through st.connection, which reads
credentials from .streamlit/secrets.toml.
"""

import pandas as pd
import re
import json
import streamlit as st

def searching(location, search_term):
    """
    Check whether a location string matches all words in a search term.

    Splits compound location strings (e.g. "Route 1, Pallet Town") on
    ', ' or '& ' before uppercase letters, then checks whether any
    individual location contains all words in the search term as whole
    words (with optional trailing 's' for plurals).

    Parameters
    ----------
    location : str
        Raw location string from the database, potentially containing
        multiple comma- or ampersand-separated locations.
    search_term : str
        Space-separated keywords to search for.

    Returns
    -------
    bool
        True if any sub-location matches all search words.
    """
    words = search_term.lower().split()
    locations = re.split(r', (?=[A-Z])|& (?=[A-Z])', str(location))
    return any(
        all(bool(re.search(rf"\b{re.escape(word)}s?\b", loc.lower())) for word in words)
        for loc in locations
    )


def query_database(generation, included_games, exclusions=[], search_term="", inclusive=True):
    """
    Query the Pokédex database and return a pivoted DataFrame of Pokémon
    and their encounter locations, filtered by game availability.

    The query supports two filtering modes:
    - Inclusive ('at least one of'): returns Pokémon available in any of
      the included games, excluding those also found in excluded games.
    - Exclusive ('all of'): returns only Pokémon available in ALL included
      games (i.e. the intersection), excluding those in excluded games.

    If no games are specified, returns all Pokémon for the generation.

    Parameters
    ----------
    generation : int
        Generation number (1-9) used to scope the query when no games
        are specified, and to order columns via game_order.json.
    included_games : list of str
        Games to include in the search. Empty list returns all Pokémon
        for the generation.
    exclusions : list of str, optional
        Games whose Pokémon should be excluded from results. Default [].
    search_term : str, optional
        Keyword string to filter by location name. Default "".
    inclusive : bool, optional
        If True, use inclusive (union) filtering. If False, use exclusive
        (intersection) filtering. Default True.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by Pokédex number ('No.'), with a 'Pokemon'
        column and one column per game showing encounter locations.
        Games are ordered according to game_order.json.
    """
    conn = st.connection("pokedex", type="sql")

    selected_games = list(included_games) if not isinstance(included_games, list) else included_games
    excluded_games = list(exclusions) if not isinstance(exclusions, list) else exclusions

    # Build named placeholders for parameterised queries
    placeholders1 = ",".join([f":g{i}" for i in range(len(selected_games))])
    placeholders2 = ",".join([f":g{i + len(selected_games)}" for i in range(len(excluded_games))])
    params = {f"g{i}": game for i, game in enumerate(selected_games + excluded_games)}

    # Base query joining encounter locations with Pokémon names
    initial_query = """SELECT p.number, p.pokemon, e.game, e.location
                       FROM encounters e JOIN pokemon_names p ON p.number = e.number
                    """

    if inclusive and len(selected_games) > 0:
        # Return Pokémon catchable (method=1) in at least one included game,
        # excluding those catchable in any excluded game
        secondary_query = f"""
            WHERE e.game IN ({placeholders1})
            AND e.number IN
                (SELECT number FROM encounters WHERE game IN ({placeholders1}) AND method = 1)
            AND e.number NOT IN
                (SELECT number FROM encounters WHERE game IN ({placeholders2}) AND method = 1)
        """
    elif not inclusive and len(selected_games) > 0:
        # Return only Pokémon catchable in ALL included games (intersection),
        # excluding those catchable in any excluded game
        secondary_query = f"""
            WHERE e.game IN ({placeholders1}) AND e.method = 1
            AND e.number NOT IN
                (SELECT number FROM encounters WHERE game IN ({placeholders2}) AND method = 1)
        """
    else:
        # No games specified: return all Pokémon for the generation,
        # still respecting any exclusions
        secondary_query = f"""
            WHERE e.game IN
                (SELECT game FROM games_gens WHERE generation = {generation})
            AND e.number NOT IN
                (SELECT number FROM encounters WHERE game IN ({placeholders2}) AND method = 1)
        """

    sql = initial_query + secondary_query
    test = conn.query(sql, params=params, ttl=0)

    # Pivot so each row is a Pokémon and each column is a game,
    # with location strings as values
    df = (
        test.pivot(index=['number', 'pokemon'], columns='game', values='location')
        .rename_axis(None, axis=1)
        .rename_axis(index={"number": 'No.', "pokemon": 'Pokemon'})
    )

    # Reorder columns to show logical game ordered saved in game_order.json
    with open("game_order.json", "r") as f:
        game_order = json.load(f)
    present_games = [g for g in game_order[str(generation)] if g in df.columns]
    df = df[present_games]

    # Intersection mode: drop Pokémon missing from any included game
    if not inclusive:
        df = df.dropna()

    # Apply keyword filter to location strings if a search term was provided
    if len(search_term) > 0:
        mask = test['location'].apply(lambda x: searching(x, search_term))
        indices = test[mask]['number']
        df = df.loc[indices]

    return df.reset_index("Pokemon").drop_duplicates()


def get_games(gen):
    """
    Return the ordered list of games for a given generation.

    Reads directly from game_order.json rather than the database,
    since game ordering is a static configuration concern.

    Parameters
    ----------
    gen : int
        Generation number (1–9).

    Returns
    -------
    list of str
        Game names in canonical release order for the generation.
    """
    with open("game_order.json", "r") as f:
        game_order = json.load(f)
    return game_order[str(gen)]
