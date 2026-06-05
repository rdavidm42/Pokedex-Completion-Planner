import pandas as pd
import re
import json
import streamlit as st
# from sqlalchemy import text,create_engine

def get_connection():
    return st.connection("pokedex",type="sql")

def searching(location,search_term):
    words = search_term.lower().split()
    locations = re.split(r', (?=[A-Z])|& (?=[A-Z])',str(location))
    
    return any([all([bool(re.search(rf"\b{re.escape(word)}s?\b",loc.lower())) for word in words]) for loc in locations])

def query_database(generation,included_games,exclusions=[],search_term="",inclusive = True):
    conn = get_connection()
    if type(included_games) ==list:
        selected_games = included_games
    else:
        selected_games = list(included_games)
    if type(exclusions) == list:
        excluded_games = exclusions
    else:
        excluded_games = list(exclusions)
    
    placeholders1 = ",".join([f":g{i}" for i in range(len(selected_games))])
    placeholders2 = ",".join([f":g{i+len(selected_games)}" for i in range(len(excluded_games))])
    
    params = {
        f"g{i}": game
        for i, game in enumerate(selected_games + excluded_games)
    }

    initial_query = f"""SELECT p.number, p.pokemon, e.game, e.location
                    FROM encounters e JOIN pokemon_names p ON p.number = e.number
                    """

    if inclusive and len(selected_games)>0:
        secondary_query = f"""
                        WHERE e.game IN ({placeholders1})
                        
                        AND e.number IN 
                        (SELECT number FROM encounters WHERE game IN ({placeholders1}) AND method = 1)
                        
                        AND e.number NOT IN 
                        (SELECT number FROM encounters WHERE game IN ({placeholders2}) AND method = 1)
                        """
    elif not inclusive and len(selected_games)>0:
        secondary_query = f"""
                        WHERE e.game IN ({placeholders1}) AND e.method = 1
                    
                        AND e.number NOT IN 
                        (SELECT number FROM encounters WHERE game IN ({placeholders2}) AND method = 1)
                        """
    else:
        secondary_query = f"""
                        WHERE e.game IN 
                        (SELECT game FROM games_gens WHERE generation = {generation})
                        
                        AND e.number NOT IN 
                        (SELECT number FROM encounters WHERE game IN ({placeholders2}) AND method = 1)
                        """
        
    sql = initial_query+secondary_query
    test = conn.query(sql, engine,params=params,ttl=0)     
    df = test.pivot(index=['number','pokemon']
                   ,columns='game',
                   values='location').rename_axis(None, axis=1).rename_axis(index={"number":'No.',"pokemon":'Pokemon'})
    
    with open("game_order.json", "r") as jsonfile: 
        game_order = json.load(jsonfile)
    present_games = [x for x in game_order[str(generation)] if x in df.columns]
    df = df[present_games]
    
    if not inclusive:
        df = df.dropna()
    if len(search_term)>0:
        mask = test['location'].apply(lambda x: searching(x,search_term))
        indices = test[mask]['number']
        df = df.loc[indices]
    return df.reset_index("Pokemon").drop_duplicates()
    
def get_games(gen):
    conn = get_connection()
    sql = f""" SELECT game FROM games_gens WHERE generation = :gen_number """
    test = conn.query(sql, engine,params={'gen_number':gen},ttl=0)
    return list(test['game'])
