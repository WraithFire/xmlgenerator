import os
import random
import requests
import threading
import importlib.util
import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
import tkinter as tk
from tkinter import messagebox, ttk

from essential_data import (
    DEBUG,
    requiredDirectory,
    requiredFile,
    backupFile,
    generation_to_games,
    region_to_gen,
    pokemon_ids,
    staticUrl,
    graphqlUrl,
    headers,
    graphqlQuery,
    pokemon_data_content,
    small_icon_data,
    large_icon_data
)

queries = []

def initialize_app():
    global queries

    if os.path.exists("queries_data.py"):
        query_spec = importlib.util.spec_from_file_location("queries_data", "queries_data.py")
        queries_data = importlib.util.module_from_spec(query_spec)
        query_spec.loader.exec_module(queries_data)
        queries = queries_data.queries_array

    if not os.path.exists(requiredFile):
        with open(requiredFile, 'w') as file:
            file.write(pokemon_data_content)
    
    if not os.path.exists(requiredDirectory):
        os.makedirs(requiredDirectory)

def fairy_type_patch_warning():
    if not fairy_patch_var.get():
        confirmation = messagebox.askyesno("Attention", "Unchecking this means Fairy type defaults to Normal type. Continue?")
        if not confirmation:
            fairy_patch_var.set(True)

def reset_data_file():
    confirmed = messagebox.askyesno("Attention", f"Are you sure you want to reset the {requiredFile} file?")
    if confirmed:
        if os.path.exists(requiredFile):
            with open(requiredFile, "r") as file:
                content = file.read()
            with open(backupFile, 'w') as file:
                file.write(content)       
        with open(requiredFile, 'w') as file:
            file.write(pokemon_data_content)

def title_case(move_name):
    return " ".join(word.capitalize() for word in move_name.split("-"))

def find_key_by_value(dictionary, target_value):
    for key, value in dictionary.items():
        if value == target_value:
            return key
    return None

def get_random_ability():

    valid_abilities_for_randomization = {ability: ability_id for ability, ability_id in pokemon_abilities_id.items() if ability_id not in pokemon_signature_abilities.values()}

    return random.choice(list(valid_abilities_for_randomization.values()))

def get_random_move(avoid_ids, moves_dict):
    move_list = []

    avoid_ids_for_randomization = avoid_ids.union(pokemon_signature_moves.values())

    for move_type in moves_dict.values():
        for move_category in move_type.values():
            for move in move_category:
                if move["ID"] not in avoid_ids_for_randomization:
                    move_list.append(move)

    selected_move = random.choice(move_list)

    return selected_move["ID"]

def get_move_name_by_id(move_id, moves_dict):
    for move_type in moves_dict.values():
        for move_category in move_type.values():
            for move in move_category:
                if move["ID"] == move_id:
                    return move["Move"]
    return None

def get_move_id_by_name(move_name, moves_dict):
    for move_type in moves_dict.values():
        for move_category in move_type.values():
            for move in move_category:
                if move["Move"] == move_name:
                    return move["ID"]
    return None

def toggle_category(category):
    if category == "Physical":
        category = "Special"
    elif category == "Special":
        category = "Physical"
    return category

def get_moves_by_category(category, avoid_ids, moves_dict):
    moves = []
    for move_type in moves_dict.values():
        if category in move_type:
            for move in move_type[category]:
                if move["ID"] not in avoid_ids:
                    moves.append(move)
    return moves

def get_closest_move(power, move_type, category, avoid_ids, moves_dict):
    closest_move = None
    min_power_difference = float('inf')

    similar_moves = moves_dict.get(move_type).get(category)
    filtered_moves = [move for move in similar_moves if move["ID"] not in avoid_ids]

    if power is None:
        if filtered_moves:
            closest_move = random.choice(filtered_moves)
        else:
            category_moves = get_moves_by_category(category, avoid_ids, moves_dict)
            closest_move = random.choice(category_moves)
    else:
        if filtered_moves:
            for move in filtered_moves:
                if abs(move["Power"] - power/4.5) < min_power_difference:
                    closest_move = move
                    min_power_difference = abs(move["Power"] - power/4.5)
        else:
            category = toggle_category(category)
            similar_moves = moves_dict.get(move_type).get(category)
            filtered_moves = [move for move in similar_moves if move["ID"] not in avoid_ids]
            if filtered_moves:
                for move in filtered_moves:
                    if abs(move["Power"] - power/4.5) < min_power_difference:
                        closest_move = move
                        min_power_difference = abs(move["Power"] - power/4.5)
            else:
                category = toggle_category(category)
                category_moves = get_moves_by_category(category, avoid_ids, moves_dict)
                for move in category_moves:
                    if abs(move["Power"] - power/4.5) < min_power_difference:
                        closest_move = move
                        min_power_difference = abs(move["Power"] - power/4.5)

    if closest_move is None:
        return get_random_move(avoid_ids, moves_dict)
    else:
        return closest_move['ID']

def add_query():
    if pokemon_var.get() == "None":
        messagebox.showerror("Error", "Please select a Pokemon.")
        return
    elif not base_index_var.get():
        messagebox.showerror("Error", "Base Pokemon Index cannot be blank!")
        return
    elif not pre_evo_index_var.get():
        messagebox.showerror("Error", "Pre Evolution Index cannot be blank!")
        return
    elif expand_pokelist_var.get() and not poke_id_var.get():
        messagebox.showerror("Error", "Entity ID cannot be blank!")
        return

    query_pokemon_name = pokemon_var.get()
    pokemon_index = pokemon_ids[query_pokemon_name]
    pokemonId, movesetRegion, gender  = pokemon_index.split("-")

    if gender == "Normal" and expand_pokelist_var.get() and not pre_evo_index_var_second.get():
        messagebox.showerror("Error", "Pre Evolution Index of Female cannot be blank!")
        return        

    query = {}

    if len(query_pokemon_name) > 10:
        if '-' in query_pokemon_name:
            name_parts = query_pokemon_name.split('-')
            first_part = name_parts[0][:10]
            query_pokemon_name =  first_part
        else:
            query_pokemon_name = query_pokemon_name[:10]

    query["pokemonId"] = int(pokemonId)

    query_pre_evo_index = int(pre_evo_index_var.get())
    query["preEvoIndex"] = query_pre_evo_index

    query_pre_evo_index_second = int(pre_evo_index_var_second.get()) if pre_evo_index_var_second.get()  else None
    query["preEvoIndex2"] = query_pre_evo_index_second    

    query["pokeGender"] = gender

    query_poke_id = int(poke_id_var.get()) if poke_id_var.get()  else None
    query["pokeID"] = query_poke_id

    query_base_index = int(base_index_var.get())
    query["baseIndex"] = query_base_index

    query["graphQL"] = graphql_var.get()

    query_new_moves = move_assign_var.get()
    query["newMoves"] = query_new_moves

    query_stats = stats_assign_var.get()
    query["stats"] = query_stats

    if region_to_gen[moveset_region_var.get()]:
        query_moveset_region = moveset_region_var.get()
        query["movesetGen"] = region_to_gen[query_moveset_region]
    else:
        query_moveset_region = "Default"
        query["movesetGen"] = int(movesetRegion)

    queries.append(query)

    if expand_pokelist_var.get():
        query_text = f"Name: {query_pokemon_name}, EntityID: {query_poke_id}, BaseId: {query_base_index}, PreId: ({query_pre_evo_index}, {query_pre_evo_index_second}), MoveGen: {query_moveset_region}"
    else:
        query_text = f"Name: {query_pokemon_name}, BaseId: {query_base_index}, PreId: {query_pre_evo_index}, MoveGen: {query_moveset_region}"

    query_log.config(state=tk.NORMAL)
    query_log.insert(tk.END, query_text + "\n")
    query_log.see(tk.END)
    query_log.config(state=tk.DISABLED)

    if not DEBUG:
        pokemon_var.set("None")
        poke_id_var.set("")
        pre_evo_index_var.set("")
        pre_evo_index_var_second.set("")
        base_index_var.set("")
    else:
        print(query)

def undo_query():
    if queries:
        queries.pop()
        query_log.config(state=tk.NORMAL)
        query_log.delete("end-2l", "end-1l")
        query_log.see(tk.END)
        query_log.config(state=tk.DISABLED)
    else:
        messagebox.showerror("Error", "No Query to Undo.")

def clear_log():
    console_log.config(state=tk.NORMAL)
    console_log.delete("1.0", tk.END)
    console_log.config(state=tk.DISABLED)

def pokemon_select(event):
    index = pokemon_listbox.curselection()
    if index:
        selected_item = pokemon_listbox.get(index)
        if selected_item:
            pokemon_var.set(selected_item)
            pokemon_index = pokemon_ids[selected_item]
            gender  = pokemon_index.split("-")[2]
            if gender == "Normal" and expand_pokelist_var.get():
                pre_evo_index_entry_second.config(state=tk.NORMAL)
            else:
                pre_evo_index_entry_second.config(state=tk.DISABLED)

def update_suggestions(event):
    filter_text = event.widget.get().lower()
    suggestions = [
        pokemon for pokemon in pokemon_ids.keys() if filter_text in pokemon.lower()
    ]
    update_listbox(suggestions)

def update_listbox(suggestions):
    pokemon_listbox.delete(0, tk.END)
    for suggestion in suggestions:
        pokemon_listbox.insert(tk.END, suggestion)

def validate_numeric_input(input):
    if input.isdigit() or input == "":
        return True
    else:
        return False

def toggle_poke_id_entry():
    if expand_pokelist_var.get():
        confirmation = messagebox.askyesno("Attention", "Checking this creates separate XML for male and female Pokemon. Continue?")
        if confirmation:
            poke_id_entry.configure(state=tk.NORMAL)
            if not pokemon_var.get() == "None":
                pokemon_index = pokemon_ids[pokemon_var.get()]
                gender  = pokemon_index.split("-")[2]
                if gender == "Normal":
                    pre_evo_index_entry_second.config(state=tk.NORMAL)
        else:
            poke_id_var.set("")
            poke_id_entry.configure(state=tk.DISABLED)
            expand_pokelist_var.set(False)
    else:
        confirmation = messagebox.askyesno("Attention", "If unchecked, the expanded pokelist fields will be ignored in Queries. Continue?")
        if confirmation:
            poke_id_var.set("")
            poke_id_entry.configure(state=tk.DISABLED)
            pre_evo_index_var_second.set("")
            pre_evo_index_entry_second.configure(state=tk.DISABLED)            
        else:
            poke_id_entry.configure(state=tk.NORMAL)
            expand_pokelist_var.set(True)

def toggle_moveset_dropdown(state):
    if state:
        moveset_region_combobox.configure(state=tk.NORMAL)
    else:
        moveset_region_combobox.configure(state=tk.DISABLED)
        moveset_region_var.set("Default")

def assign_base_stats(base_stats, random_seed = None):

    if random_seed:
        random.seed(random_seed)

    hp = random.randint(*base_stats["HP"])
    other_stats = [random.randint(*base_stats["Other"]) for _ in range(4)]

    total = hp + sum(other_stats)

    while total < base_stats["Total"][0] or total > base_stats["Total"][1]:
        hp = random.randint(*base_stats["HP"])
        other_stats = [random.randint(*base_stats["Other"]) for _ in range(4)]
        total = hp + sum(other_stats)

    other_stats.append(hp)

    stats_list = sorted(other_stats)

    if random_seed:
        random.seed()

    return stats_list

def generate_xml():
    if queries:
        add_query_button.config(state=tk.DISABLED)
        undo_query_button.config(state=tk.DISABLED)
        clear_log_button.config(state=tk.DISABLED)
        reset_data_button.config(state=tk.DISABLED)
        fairy_patch_checkbox.config(state=tk.DISABLED)
        expanded_poke_checkbox.config(state=tk.DISABLED)
        generate_xml_button.config(state=tk.DISABLED)
        console_log.config(state=tk.NORMAL)
        console_log.insert(tk.END, "Generating XML....\n")
        console_log.see(tk.END)
        console_log.config(state=tk.DISABLED)
        def generate_xml_thread():
            query_executed = 0
            exception_occurred = False
            global queries
            queries_copy = queries.copy()

            for query in queries:
                pokemonId = query.get("pokemonId")
                preEvoIndex = query.get("preEvoIndex")
                preEvoIndexSecond = query.get("preEvoIndex2")
                baseIndex = query.get("baseIndex")
                movesetGen = query.get("movesetGen")
                pokeGender = query.get("pokeGender")
                newMoves = query.get("newMoves")
                graphQL = query.get("graphQL")
                pokeID = query.get("pokeID")
                stats = query.get("stats")

                try:
                    if graphQL:
                        graphqlVariables = {}
                        graphqlVariables["pokemonId"] = pokemonId
                        graphqlVariables["movesetGame"] = generation_to_games[movesetGen]
                        data = {"query": graphqlQuery, "variables": graphqlVariables}
                        response = requests.post(graphqlUrl, headers=headers, json=data)
                        json_response = response.json().get("data")
                    else:
                        requestUrl = staticUrl.replace("[id]", str(pokemonId)).replace(
                            "[gen]", str(movesetGen)
                        )
                        response = requests.get(requestUrl)
                        json_response = response.json()

                    pokemon_node = json_response["pokemon"][0]

                    # Create the root element
                    root = ET.Element("Pokemon", gameVersion="EoS")

                    # Create Strings element
                    strings_element = ET.SubElement(root, "Strings")
                    english_element = ET.SubElement(strings_element, "English")
                    pokemon_name = pokemon_node["name"]

                    name_element = ET.SubElement(english_element, "Name")

                    if len(pokemon_name) > 10:
                        if '-' in pokemon_name:
                            name_parts = pokemon_name.split('-')
                            first_part = name_parts[0][:10]
                            pokemon_name =  first_part
                        else:
                            pokemon_name = pokemon_name[:10]

                    name_element.text = pokemon_name.title()

                    category_element = ET.SubElement(english_element, "Category")
                    category_element.text = pokemon_node["specy"]["category"][0][
                        "genus"
                    ].replace(" Pokémon", "")

                    primary_type = (
                        pokemon_node["types"][0]["type"]["name"].title()
                        if len(pokemon_node["types"]) > 0
                        else None
                    )
                    secondary_type = (
                        pokemon_node["types"][1]["type"]["name"].title()
                        if len(pokemon_node["types"]) > 1
                        else None
                    )

                    if not fairy_patch_var.get():
                        exclude_type = "Fairy"
                        if primary_type == "Fairy":
                            primary_type = "Normal"

                        if secondary_type == "Fairy":
                            secondary_type = "Normal"
                    else:
                        exclude_type = "None"

                    types_list = [value for key, value in pokemon_types_id.items() if key != exclude_type]

                    placeholder_type = random.choice(types_list)
                    primary_type_id =  pokemon_types_id.get(primary_type, placeholder_type)
                    secondary_type_id = pokemon_types_id.get(secondary_type, 0)

                    placeholder_ability = get_random_ability()

                    primary_ability = (
                        title_case(pokemon_node["abilities"][0]["ability"]["name"])
                        if len(pokemon_node["abilities"]) > 0
                        else None
                    )
                    primary_ability_id = pokemon_abilities_id.get(primary_ability, placeholder_ability)
                    secondary_ability = (
                        title_case(pokemon_node["abilities"][1]["ability"]["name"])
                        if len(pokemon_node["abilities"]) > 1
                        else None
                    )
                    secondary_ability_id = pokemon_abilities_id.get(secondary_ability, 0)

                    evolution_chain_id = pokemon_node["specy"]["evolution_chain"]["id"]

                    def assign_iq(evolution_chain_id):
                        random.seed(evolution_chain_id)
                        assigned_iq = random.choice(pokemon_iq_array)
                        random.seed()
                        return assigned_iq
                    
                    pokemon_iq = assign_iq(evolution_chain_id)

                    def assign_chest_rates(evolution_chain_id):
                        random.seed(evolution_chain_id)
                        no_drop_rate = random.choice(no_drop_rate_array)
                        normal_drop_rate = random.choice(normal_drop_rate_array)
                        type_one_drop_rate = random.choice(type_one_drop_rate_array)
                        type_two_drop_rate = random.choice(type_two_drop_rate_array)
                        random.seed()
                        return [no_drop_rate, normal_drop_rate, type_one_drop_rate, type_two_drop_rate]

                    chest_drop_rates = assign_chest_rates(evolution_chain_id)

                    personality = random.choice(personality_array)
                    asleep_value = random.choice(asleepchance_array)

                    if expand_pokelist_var.get():
                        gendered_entity_number = 1
                    else:
                        gendered_entity_number = 2

                    pokemon_stats_dict = {
                        "Attack" : pokemon_node["stats"][1]["base_stat"],
                        "Defense" : pokemon_node["stats"][2]["base_stat"],
                        "SpAttack" : pokemon_node["stats"][3]["base_stat"],
                        "SpDefense" : pokemon_node["stats"][4]["base_stat"],
                    }

                    pokemon_stats_dict = dict(sorted(pokemon_stats_dict.items(), key=lambda item: item[1]))

                    pokemon_stats_dict["HP"] = pokemon_node["stats"][0]["base_stat"]

                    pokemon_speed = pokemon_node["stats"][5]["base_stat"]

                    stat_total = pokemon_stats_dict["HP"] + pokemon_stats_dict["Attack"] + pokemon_stats_dict["SpAttack"] + pokemon_stats_dict["Defense"] + pokemon_stats_dict["SpDefense"] + pokemon_speed

                    pokemon_stats_dict_keys = list(pokemon_stats_dict.keys())

                    if stats == "Normal":
                        base_stats_list = assign_base_stats(normal_base_stats)
                    elif stats == "Starter":
                        base_stats_list = assign_base_stats(starter_base_stats, evolution_chain_id)
                    elif stats == "Legendary":
                        base_stats_list = assign_base_stats(legendary_base_stats)

                    for i in range(len(pokemon_stats_dict_keys)):
                        pokemon_stats_dict[pokemon_stats_dict_keys[i]] = base_stats_list[i]

                    for loop_index in range(gendered_entity_number):
                        # Creating the GenderedEntity element                        
                        gendered_entity_element = ET.SubElement(root, "GenderedEntity")

                        if expand_pokelist_var.get() and pokeID:
                            poke_id_element = ET.SubElement(gendered_entity_element, "PokeID")
                            poke_id_element.text = str(pokeID)

                        # pokedex
                        pokedex_number_element = ET.SubElement(
                            gendered_entity_element, "PokedexNumber"
                        )
                        pokedex_number_element.text = str(pokemon_node["dex_id"])

                        movement_speed = ET.SubElement(gendered_entity_element, "MovementSpeed")
                        movement_speed.text = str(1)

                        # Gender 
                        if pokeGender == "Normal":
                            gender_element = ET.SubElement(gendered_entity_element, "Gender")
                            if DEBUG:
                                gender_element.text = "Male" if loop_index == 0 else "Female"
                            else:    
                                gender_element.text = str(loop_index + 1)
                        elif pokeGender == "Male":
                            gender_element = ET.SubElement(gendered_entity_element, "Gender")
                            if DEBUG:
                                gender_element.text = "Male" if loop_index == 0 else "Invalid"
                            else:
                                gender_element.text = str(1) if loop_index == 0 else str(0)
                        elif pokeGender == "Female":
                            gender_element = ET.SubElement(gendered_entity_element, "Gender")
                            if DEBUG:
                                gender_element.text = "Female" if loop_index == 0 else "Invalid"
                            else:
                                gender_element.text = str(2) if loop_index == 0 else str(0)
                        elif pokeGender == "Genderless":
                            gender_element = ET.SubElement(gendered_entity_element, "Gender")
                            if DEBUG:
                                gender_element.text = "Genderless" if loop_index == 0 else "Invalid"
                            else:
                                gender_element.text = str(3) if loop_index == 0 else str(0)

                        body_size = ET.SubElement(gendered_entity_element, "BodySize")

                        for (start, end), assigned_body_size in body_size_ranges.items():
                            if pokemon_node["height"] >= start and pokemon_node["height"] <= end:
                                body_size.text = str(assigned_body_size)

                        # types
                        primary_type_element = ET.SubElement(
                            gendered_entity_element, "PrimaryType"
                        )
                        if DEBUG:
                            primary_type_element.text = find_key_by_value(pokemon_types_id, primary_type_id)
                        else:
                            primary_type_element.text = str(primary_type_id)
                        secondary_type_element = ET.SubElement(
                            gendered_entity_element, "SecondaryType"
                        )
                        if DEBUG:
                            secondary_type_element.text = find_key_by_value(pokemon_types_id, secondary_type_id) if secondary_type_id != 0 else "None"
                        else:
                            secondary_type_element.text = str(secondary_type_id)

                        # movement type
                        movement_type_element = ET.SubElement(
                            gendered_entity_element, "MovementType"
                        )

                        if primary_type in ["Water", "Fire", "Flying", "Ghost"]:
                            if DEBUG:
                                movement_type_element.text = primary_type
                            else:
                                movement_type_element.text = str(
                                    movement_types.get(primary_type, 0)
                                )
                        elif secondary_type in ["Water", "Fire", "Flying", "Ghost"]:
                            if DEBUG:
                                movement_type_element.text = secondary_type
                            else:
                                movement_type_element.text = str(
                                    movement_types.get(secondary_type, 0)
                                )
                        elif primary_ability in ["Levitate"]:
                            if DEBUG:
                                movement_type_element.text = primary_ability
                            else:
                                movement_type_element.text = str(
                                    movement_types.get(primary_ability, 0)
                                )
                        elif secondary_ability in ["Levitate"]:
                            if DEBUG:
                                movement_type_element.text = secondary_ability
                            else:
                                movement_type_element.text = str(
                                    movement_types.get(secondary_ability, 0)
                                )
                        else:
                            if DEBUG:
                                movement_type_element.text = "Standard"
                            else:
                                movement_type_element.text = "0"

                        iq_group = ET.SubElement(gendered_entity_element, "IQGroup")
                        iq_group.text = str(pokemon_iq)

                        # ability
                        primary_ability_element = ET.SubElement(
                            gendered_entity_element, "PrimaryAbility"
                        )
                        if DEBUG:
                            primary_ability_element.text = find_key_by_value(pokemon_abilities_id, primary_ability_id)
                        else:
                            primary_ability_element.text = str(primary_ability_id)
                        secondary_ability_element = ET.SubElement(
                            gendered_entity_element, "SecondaryAbility"
                        )
                        if DEBUG:
                            secondary_ability_element.text = find_key_by_value(pokemon_abilities_id, secondary_ability_id) if secondary_ability_id != 0 else "None"
                        else:
                            secondary_ability_element.text = str(secondary_ability_id)

                        exp_yield = ET.SubElement(gendered_entity_element, "ExpYield")

                        if pokemon_node["exp_yield"]:
                            exp_yield.text = str(int(pokemon_node["exp_yield"])//2)
                        else:
                            exp_yield.text = str(50)

                        for internal_loop_index in range(2):
                            recruit_rate = ET.SubElement(
                                gendered_entity_element, f"RecruitRate{internal_loop_index+1}"
                            )
                            for (start, end), assigned_rate in recruitrate_ranges.items():
                                if stat_total >= start and stat_total <= end:
                                    recruit_rate.text = str(assigned_rate)

                        weight = ET.SubElement(gendered_entity_element, "Weight")

                        for (start, end), assigned_weight in weight_ranges.items():
                            if pokemon_node["weight"] >= start and pokemon_node["weight"] <= end:
                                weight.text = str(assigned_weight)

                        size = ET.SubElement(gendered_entity_element, "Size")

                        for (start, end), assigned_size in size_ranges.items():
                            if pokemon_node["height"] >= start and pokemon_node["height"] <= end:
                                size.text = str(assigned_size)

                        if not expand_pokelist_var.get():
                            Unk17 = ET.SubElement(gendered_entity_element, "Unk17")
                            Unk17.text = str(10)

                            Unk18 = ET.SubElement(gendered_entity_element, "Unk18")
                            Unk18.text = str(10)

                        shadow_size = ET.SubElement(gendered_entity_element, "ShadowSize")

                        for (start, end), assigned_shadow in shadow_ranges.items():
                            if pokemon_node["height"] >= start and pokemon_node["height"] <= end:
                                shadow_size.text = str(assigned_shadow)

                        asleep_chance = ET.SubElement(gendered_entity_element, "AsleepChance")
                        asleep_chance.text = str(asleep_value)

                        hp_regen = ET.SubElement(gendered_entity_element, "HpRegen")
                        hp_regen.text = str(100)

                        spawn_threshold = ET.SubElement(gendered_entity_element, "Unk21h")
                        spawn_threshold.text = str(0)

                        if baseIndex:
                            base_pokemon_index = ET.SubElement(gendered_entity_element, "BasePokemonIndex")
                            base_pokemon_index.text = str(baseIndex)

                        #chest drops
                        no_drop_rate = ET.SubElement(gendered_entity_element, "Unk27")
                        no_drop_rate.text = str(chest_drop_rates[0])

                        normal_drop_rate = ET.SubElement(gendered_entity_element, "Unk28")
                        normal_drop_rate.text = str(chest_drop_rates[1])

                        type_one_drop_rate = ET.SubElement(gendered_entity_element, "Unk29")
                        type_one_drop_rate.text = str(chest_drop_rates[2])

                        type_two_drop_rate = ET.SubElement(gendered_entity_element, "Unk30")
                        type_two_drop_rate.text = str(chest_drop_rates[3])

                        #personality
                        pokemon_personality = ET.SubElement(gendered_entity_element, "Personality")
                        pokemon_personality.text = str(personality)

                        # Evolution Data
                        evolution_data = pokemon_node["specy"]["evolution_chain"]["species"]
                        evolutionreq_element = ET.SubElement(
                            gendered_entity_element, "EvolutionReq"
                        )

                        prev_evo_index_element = ET.SubElement(
                            evolutionreq_element, "PreEvoIndex"
                        )

                        if loop_index == 1 and preEvoIndex != 0:
                            prev_evo_index_element.text = str(preEvoIndex + 600)
                        else:
                            prev_evo_index_element.text = str(preEvoIndex)

                        evolution_method_element = ET.SubElement(evolutionreq_element, "Method")
                        evolution_method_element.text = "0"
                        evolution_parameter_element = ET.SubElement(
                            evolutionreq_element, "Param1"
                        )
                        evolution_parameter_element.text = "0"
                        evolution_aditional_element = ET.SubElement(
                            evolutionreq_element, "Param2"
                        )
                        evolution_aditional_element.text = "0"

                        for species in evolution_data:
                            if (
                                species["name"] in pokemon_name
                                and len(species["evolution_condition"]) > 0
                            ):
                                condition = species["evolution_condition"][0]
                                if condition["level"] is not None:
                                    evolution_method_element.text = "1"
                                    evolution_parameter_element.text = str(condition["level"])
                                elif condition["iq"] is not None and condition["time"] == "":
                                    evolution_method_element.text = "2"
                                    evolution_parameter_element.text = "200"
                                elif condition["iq"] is not None:
                                    evolution_method_element.text = "2"
                                    evolution_parameter_element.text = "100"                                
                                elif (
                                    condition["item"] is not None
                                    or condition["held_item"] is not None
                                ):
                                    evolution_method_element.text = "3"
                                    evolution_parameter_element.text = "161"
                                elif condition["trigger"] == 2:
                                    evolution_method_element.text = "5"
                                    evolution_aditional_element.text = "1"
                                elif condition["trigger"] > 0:
                                    evolution_method_element.text = "1"
                                    evolution_parameter_element.text = str(30)

                                if condition["time"] == "day":
                                    evolution_aditional_element.text = "5"
                                elif condition["time"] == "night":
                                    evolution_aditional_element.text = "6"

                                break

                        # Base Stats
                        base_stats_element = ET.SubElement(
                            gendered_entity_element, "BaseStats"
                        )

                        hp_element = ET.SubElement(base_stats_element, "HP")
                        hp_element.text = str(pokemon_stats_dict["HP"])

                        attack_element = ET.SubElement(base_stats_element, "Attack")
                        attack_element.text = str(pokemon_stats_dict["Attack"])

                        sp_attack_element = ET.SubElement(base_stats_element, "SpAttack")
                        sp_attack_element.text = str(pokemon_stats_dict["SpAttack"])

                        defense_element = ET.SubElement(base_stats_element, "Defense")
                        defense_element.text = str(pokemon_stats_dict["Defense"])

                        sp_defense_element = ET.SubElement(base_stats_element, "SpDefense")
                        sp_defense_element.text = str(pokemon_stats_dict["SpDefense"])
                               
                        # Create Bitfield element
                        bitfield_element = ET.SubElement(gendered_entity_element, "Bitfield")
                        unknown_bit_0_element = ET.SubElement(bitfield_element, "Unk0")
                        unknown_bit_0_element.text = "0"
                        unknown_bit_1_element = ET.SubElement(bitfield_element, "Unk1")
                        unknown_bit_1_element.text = "0"
                        unknown_bit_2_element = ET.SubElement(bitfield_element, "Unk2")
                        unknown_bit_2_element.text = "0"
                        unknown_bit_3_element = ET.SubElement(bitfield_element, "Unk3")
                        unknown_bit_3_element.text = "0"
                        can_move_element = ET.SubElement(bitfield_element, "CanMove")
                        can_move_element.text = "1"
                        can_throw_items_element = ET.SubElement(bitfield_element, "Unk5")
                        can_throw_items_element.text = "1"
                        can_evolve_element = ET.SubElement(bitfield_element, "CanEvolve")
                        item_for_spawning_element = ET.SubElement(
                            bitfield_element, "ItemRequiredForSpawning"
                        )
                        item_for_spawning_element.text = "0"

                        for species in evolution_data:
                            if species["pre_evolution"] == pokemon_node["dex_id"]:
                                can_evolve_element.text = "1"
                                break
                        else:
                            can_evolve_element.text = "0"

                    # Create Moveset element
                    moveset_element = ET.SubElement(root, "Moveset")

                    all_moves_dict = pokemon_moves_dict

                    length_all_moves_dict = 0

                    for move_type in all_moves_dict.values():
                        for category in move_type.values():
                            length_all_moves_dict += len(category)

                    # Create LevelUpMoves element
                    levelup_moves_element = ET.SubElement(moveset_element, "LevelUpMoves")
                    assigned_level_up_move_ids = set()

                    level_moves_dict = {i: 0 for i in range(1, 101)}

                    for move in pokemon_node["levelUpMoves"]:
                        if len(assigned_level_up_move_ids) < length_all_moves_dict:
                            move_name = title_case(move["move"]["name"])
                            move_id = get_move_id_by_name(move_name, all_moves_dict)
                            move_power = move["move"]["power"]
                            move_type = move["move"]["type"]["name"].title()

                            if not fairy_patch_var.get() and move_type == "Fairy":
                                move_type = "Normal"

                            move_category = move["move"]["category"]["name"].title()
                            move_level = min(max(move["level"], 1), 100)
                            next_level = min((move_level + 1), 100)

                            if move_id is not None:
                                learn_element = ET.SubElement(levelup_moves_element, "Learn")
                                level_element = ET.SubElement(learn_element, "Level")

                                if level_moves_dict[move_level] > 3:
                                    while next_level < 100 and level_moves_dict[next_level] > 3:
                                        next_level += 1
                                    level_element.text = str(next_level)
                                    level_moves_dict[next_level] += 1
                                else:
                                    level_element.text = str(move_level)
                                    level_moves_dict[move_level] += 1

                                move_id_element = ET.SubElement(learn_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, all_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_level_up_move_ids.add(move_id)                            
                            elif move_id is None and newMoves == "Random":
                                learn_element = ET.SubElement(levelup_moves_element, "Learn")
                                level_element = ET.SubElement(learn_element, "Level")

                                if level_moves_dict[move_level] > 3:
                                    while next_level < 100 and level_moves_dict[next_level] > 3:
                                        next_level += 1
                                    level_element.text = str(next_level)
                                    level_moves_dict[next_level] += 1
                                else:
                                    level_element.text = str(move_level)
                                    level_moves_dict[move_level] += 1

                                move_id = get_random_move(assigned_level_up_move_ids, all_moves_dict)
                                move_id_element = ET.SubElement(learn_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, all_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_level_up_move_ids.add(move_id)
                            elif move_id is None and newMoves == "Similar":
                                learn_element = ET.SubElement(levelup_moves_element, "Learn")
                                level_element = ET.SubElement(learn_element, "Level")

                                if level_moves_dict[move_level] > 3:
                                    while next_level < 100 and level_moves_dict[next_level] > 3:
                                        next_level += 1
                                    level_element.text = str(next_level)
                                    level_moves_dict[next_level] += 1
                                else:
                                    level_element.text = str(move_level)
                                    level_moves_dict[move_level] += 1

                                move_id = get_closest_move(move_power, move_type, move_category, assigned_level_up_move_ids, all_moves_dict)
                                move_id_element = ET.SubElement(learn_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, all_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_level_up_move_ids.add(move_id)

                    if not assigned_level_up_move_ids:
                        learn_element = ET.SubElement(levelup_moves_element, "Learn")
                        level_element = ET.SubElement(learn_element, "Level")
                        level_element.text = "1"
                        move_id_element = ET.SubElement(learn_element, "MoveID")
                        if DEBUG:
                            move_id_element.text = "Tackle"
                        else:
                            move_id_element.text = str(154)

                    # Create EggMoves element
                    egg_moves_element = ET.SubElement(moveset_element, "EggMoves")
                    assigned_egg_move_ids = set()

                    for move in pokemon_node["eggMoves"]:
                        if len(assigned_egg_move_ids) < length_all_moves_dict:
                            move_name = title_case(move["move"]["name"])
                            move_id = get_move_id_by_name(move_name, all_moves_dict)
                            move_power = move["move"]["power"]
                            move_type = move["move"]["type"]["name"].title()

                            if not fairy_patch_var.get() and move_type == "Fairy":
                                move_type = "Normal"

                            move_category = move["move"]["category"]["name"].title()

                            if move_id is not None:
                                move_id_element = ET.SubElement(egg_moves_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, all_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_egg_move_ids.add(move_id)                            
                            elif move_id is None and newMoves == "Random":
                                move_id = get_random_move(assigned_egg_move_ids, all_moves_dict)
                                move_id_element = ET.SubElement(egg_moves_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, all_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_egg_move_ids.add(move_id)
                            elif move_id is None and newMoves == "Similar":
                                move_id = get_closest_move(move_power, move_type, move_category, assigned_egg_move_ids, all_moves_dict)
                                move_id_element = ET.SubElement(egg_moves_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, all_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_egg_move_ids.add(move_id)

                    # Create HmTmMoves element
                    hmtm_moves_element = ET.SubElement(moveset_element, "HmTmMoves")

                    assigned_tm_hm_ids = {360, 394}

                    hm_tm_ids = set(pokemon_hm_tm_id.values())

                    hm_tm_moves_dict = {}

                    for type_key, type_value in pokemon_moves_dict.items():
                        hm_tm_moves_dict[type_key] = {}
                        for category_key, category_value in type_value.items():
                            hm_tm_moves_dict[type_key][category_key] = [move for move in category_value if move['ID'] in hm_tm_ids]

                    length_hm_tm_moves_dict = 0

                    for move_type in hm_tm_moves_dict.values():
                        for category in move_type.values():
                            length_hm_tm_moves_dict += len(category)

                    for move in pokemon_node["machineMoves"]:
                        if len(assigned_tm_hm_ids) < length_hm_tm_moves_dict:
                            move_name = title_case(move["move"]["name"])
                            move_id = get_move_id_by_name(move_name, hm_tm_moves_dict)
                            move_power = move["move"]["power"]
                            move_type = move["move"]["type"]["name"].title()

                            if not fairy_patch_var.get() and move_type == "Fairy":
                                move_type = "Normal"

                            move_category = move["move"]["category"]["name"].title()

                            if move_id is not None:
                                move_id_element = ET.SubElement(hmtm_moves_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, hm_tm_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_tm_hm_ids.add(move_id)                            
                            elif move_id is None and newMoves == "Random":
                                move_id = get_random_move(assigned_tm_hm_ids, hm_tm_moves_dict)
                                move_id_element = ET.SubElement(hmtm_moves_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, hm_tm_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_tm_hm_ids.add(move_id)
                            elif move_id is None and newMoves == "Similar":
                                move_id = get_closest_move(move_power, move_type, move_category, assigned_tm_hm_ids, hm_tm_moves_dict)
                                move_id_element = ET.SubElement(hmtm_moves_element, "MoveID")
                                if DEBUG:
                                    move_id_element.text = get_move_name_by_id(move_id, hm_tm_moves_dict)
                                else:
                                    move_id_element.text = str(move_id)
                                assigned_tm_hm_ids.add(move_id)
                        else:
                            break

                    default_tm_values = {"Wide Slash": 360, "Vacuum Cut": 394}
                    
                    for key, value in default_tm_values.items():        
                        move_id_element = ET.SubElement(hmtm_moves_element, "MoveID")
                        if DEBUG:
                            move_id_element.text = key
                        else:
                            move_id_element.text = str(value)

                    if expand_pokelist_var.get() and pokeGender == "Normal":
                        xml_string = ET.tostring(root, encoding="unicode")

                        xml_pretty = MD.parseString(xml_string).toprettyxml()

                        with open(f"{requiredDirectory}/{pokemon_node['name']}-Male.xml", "w") as file:
                            file.write(xml_pretty)

                        if preEvoIndexSecond:
                            prev_evo_index_element.text = str(preEvoIndexSecond)

                        if DEBUG:
                            gender_element.text = "Female"
                        else:
                            gender_element.text = str(2)

                        xml_string = ET.tostring(root, encoding="unicode")

                        xml_pretty = MD.parseString(xml_string).toprettyxml()

                        with open(f"{requiredDirectory}/{pokemon_node['name']}-Female.xml", "w") as file:
                            file.write(xml_pretty)

                        console_log.config(state=tk.NORMAL)
                        console_log.insert(tk.END, f"XML file {pokemon_node['name']}-Male.xml Generated.\n")
                        console_log.insert(tk.END, f"XML file {pokemon_node['name']}-Female.xml Generated.\n")
                        console_log.see(tk.END)
                        console_log.config(state=tk.DISABLED)
                    else:
                        xml_string = ET.tostring(root, encoding="unicode")

                        xml_pretty = MD.parseString(xml_string).toprettyxml()

                        with open(f"{requiredDirectory}/{pokemon_node['name']}.xml", "w") as file:
                            file.write(xml_pretty)

                        console_log.config(state=tk.NORMAL)
                        console_log.insert(tk.END, f"XML file {pokemon_node['name']} Generated.\n")
                        console_log.see(tk.END)
                        console_log.config(state=tk.DISABLED)

                    queries_copy.pop(0)
                    query_executed += 1
                except Exception as e:
                    exception_occurred = True
                    messagebox.showerror("Error", e)
                    break

            queries = queries_copy
            query_log.config(state=tk.NORMAL)
            query_log.delete("1.0", f"{query_executed + 1}.0")
            query_log.see(tk.END)
            query_log.config(state=tk.DISABLED)

            if not exception_occurred:
                console_log.config(state=tk.NORMAL)
                console_log.insert(tk.END, "All XML files Generated Successfully.\n")
                console_log.config(state=tk.DISABLED)
            else:
                console_log.config(state=tk.NORMAL)
                console_log.insert(tk.END, "Some XML Were Not Generated.\n")
                console_log.config(state=tk.DISABLED)

            add_query_button.config(state=tk.NORMAL)
            undo_query_button.config(state=tk.NORMAL)
            clear_log_button.config(state=tk.NORMAL)
            reset_data_button.config(state=tk.NORMAL)
            expanded_poke_checkbox.config(state=tk.NORMAL)
            fairy_patch_checkbox.config(state=tk.NORMAL)
            generate_xml_button.config(state=tk.NORMAL)
        thread = threading.Thread(target=generate_xml_thread)
        thread.daemon = True
        thread.start()
    else:
        messagebox.showerror("Error", "Query List is Empty.")   

def update_essential_data(pokemon_data_content):
    with open("essential_data.py", "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if line.startswith("pokemon_data_content"):
            lines[i] = f"pokemon_data_content = {repr(pokemon_data_content)}\n"
            break
    else:
        lines.append(f"\npokemon_data_content = {repr(pokemon_data_content)}\n")

    with open("essential_data.py", "w") as file:
        file.writelines(lines)

    print("Essential Data Updated")

if DEBUG:
    while True:
        sync_mode = input("Enable sync mode? (yes/no): ").strip().lower()
        if sync_mode == "yes" and os.path.exists(requiredFile):
            with open(requiredFile, "r") as file:
                content = file.read()
            update_essential_data(content)
            break
        elif sync_mode == "yes" and not os.path.exists(requiredFile):
            print(f"Error: Maintain a {requiredFile} to use sync mode.")
            print("Sync mode disabled.")
            break            
        elif sync_mode == "no":
            print("Sync mode disabled.")
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

initialize_app()

spec = importlib.util.spec_from_file_location("pokemon_data", f"{requiredFile}")
pokemon_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pokemon_data)

pokemon_types_id = pokemon_data.pokemon_types_id
pokemon_abilities_id = pokemon_data.pokemon_abilities_id
pokemon_hm_tm_id = pokemon_data.pokemon_hm_tm_id
personality_array = pokemon_data.personality_array
pokemon_iq_array = pokemon_data.pokemon_iq_array
movement_types = pokemon_data.movement_types
asleepchance_array = pokemon_data.asleepchance_array
weight_ranges = pokemon_data.weight_ranges
recruitrate_ranges = pokemon_data.recruitrate_ranges
size_ranges = pokemon_data.size_ranges
shadow_ranges = pokemon_data.shadow_ranges
body_size_ranges = pokemon_data.body_size_ranges
pokemon_moves_dict = pokemon_data.pokemon_moves_dict
pokemon_signature_moves = pokemon_data.pokemon_signature_moves
pokemon_signature_abilities = pokemon_data.pokemon_signature_abilities
no_drop_rate_array = pokemon_data.no_drop_rate_array
normal_drop_rate_array = pokemon_data.normal_drop_rate_array
type_one_drop_rate_array = pokemon_data.type_one_drop_rate_array
type_two_drop_rate_array = pokemon_data.type_two_drop_rate_array
normal_base_stats = pokemon_data.normal_base_stats
starter_base_stats = pokemon_data.starter_base_stats
legendary_base_stats = pokemon_data.legendary_base_stats

window = tk.Tk()
window.title("XML Generator")

small_icon = tk.PhotoImage(data=small_icon_data)
large_icon = tk.PhotoImage(data=large_icon_data)
window.iconphoto(True, small_icon, large_icon)

root = tk.LabelFrame(window)
root.pack(padx=10, pady=10)

# Variables for user inputs
pokemon_var = tk.StringVar()
pokemon_var.set("None")
pre_evo_index_var = tk.StringVar()
pre_evo_index_var_second = tk.StringVar()
base_index_var = tk.StringVar()
poke_id_var = tk.StringVar()
moveset_region_var = tk.StringVar()
moveset_region_var.set("Default")
graphql_var = tk.BooleanVar()
graphql_var.set(False)
expand_pokelist_var = tk.BooleanVar()
expand_pokelist_var.set(False)
fairy_patch_var = tk.BooleanVar()
fairy_patch_var.set(True)
move_assign_var = tk.StringVar()
move_assign_var.set("Similar")
stats_assign_var = tk.StringVar()
stats_assign_var.set("Normal")

# Entry for Pokemon
pokemon_label = tk.Label(root, text="Pokemon:")
pokemon_label.grid(row=0, column=0, pady=5)
selected_pokemon = tk.Label(root, textvariable=pokemon_var, wraplength=120, padx=5, pady=5, relief="solid")
selected_pokemon.grid(row=1, column=0, pady=5)
pokemon_search_box = tk.Entry(root, width=30)
pokemon_search_box.grid(row=0, column=1, pady=5)
pokemon_search_box.bind("<KeyRelease>", update_suggestions)

# Listbox for Pokemon suggestions
pokemon_listbox = tk.Listbox(root, width=30, height=4)
pokemon_listbox.grid(row=1, column=1, pady=5)
pokemon_listbox.bind("<ButtonRelease-1>", pokemon_select)
pokemon_listbox.bind("<Return>", pokemon_select)
update_listbox(pokemon_ids.keys())

# Entry for Base Index
poke_id_label = tk.Label(root, text="Entity ID:")
poke_id_label.grid(row=2, column=0, pady=5)
poke_id_entry = tk.Entry(
    root,
    width=30,
    textvariable=poke_id_var,
    validate="key",
    validatecommand=(root.register(validate_numeric_input), "%P"),
)
poke_id_entry.grid(row=2, column=1, pady=5)
poke_id_entry.configure(state=tk.DISABLED)

# Entry for Base Index
base_index_label = tk.Label(root, text="Base Pokemon Index:")
base_index_label.grid(row=3, column=0, pady=5)
base_index_entry = tk.Entry(
    root,
    width=30,
    textvariable=base_index_var,
    validate="key",
    validatecommand=(root.register(validate_numeric_input), "%P"),
)
base_index_entry.grid(row=3, column=1, pady=5)

# Entry for Pre Evolution Index
pre_evo_index_label = tk.Label(root, text="Pre Evolution Index:")
pre_evo_index_label.grid(row=4, column=0, pady=5)
pre_evo_index_entry = tk.Entry(
    root,
    width=10,
    textvariable=pre_evo_index_var,
    validate="key",
    validatecommand=(root.register(validate_numeric_input), "%P"),
)
pre_evo_index_entry.grid(row=4, column=1, padx=(0, 120), pady=5)
pre_evo_index_entry_second = tk.Entry(
    root,
    width=10,
    textvariable=pre_evo_index_var_second,
    validate="key",
    validatecommand=(root.register(validate_numeric_input), "%P"),
)
pre_evo_index_entry_second.grid(row=4, column=1, padx=(120, 0), pady=5)
pre_evo_index_entry_second.config(state=tk.DISABLED)

# Entry for Game Generation
moveset_region_label = tk.Label(root, text="Moveset Region:")
moveset_region_label.grid(row=5, column=0, pady=5)
moveset_region_combobox = ttk.Combobox(
    root, width=28, textvariable=moveset_region_var, values=list(region_to_gen.keys())
)
moveset_region_combobox.grid(row=5, column=1, pady=5)
moveset_region_combobox.configure(state=tk.DISABLED)

# Stats Assign
stats_assign_label = tk.Label(root, text="Stats:")
stats_assign_label.grid(row=6, column=0, pady=5)

normal_stats_radio = tk.Radiobutton(
    root,
    text="Normal",
    variable=stats_assign_var,
    value="Normal",
)
normal_stats_radio.grid(row=6, column=1, padx=(50, 0), pady=5, sticky="w")

starter_stats_radio = tk.Radiobutton(
    root,
    text="Starter",
    variable=stats_assign_var,
    value="Starter",
)
starter_stats_radio.grid(row=6, column=1, pady=5)

legendary_stats_radio = tk.Radiobutton(
    root,
    text="Legendary",
    variable=stats_assign_var,
    value="Legendary",
)
legendary_stats_radio.grid(row=6, column=1, padx=(0, 50), pady=5, sticky="e")

# Config
move_assign_label = tk.Label(root, text="New Generation Moves:")
move_assign_label.grid(row=7, column=0, pady=5)

similar_moves_radio = tk.Radiobutton(
    root,
    text="Similar",
    variable=move_assign_var,
    value="Similar",
)
similar_moves_radio.grid(row=7, column=1, padx=(50, 0), pady=5, sticky="w")

random_moves_radio = tk.Radiobutton(
    root,
    text="Random",
    variable=move_assign_var,
    value="Random",
)
random_moves_radio.grid(row=7, column=1, pady=5)

skip_moves_radio = tk.Radiobutton(
    root,
    text="Skip",
    variable=move_assign_var,
    value="Skip",
)
skip_moves_radio.grid(row=7, column=1, padx=(0, 50), pady=5, sticky="e")

# Radio buttons for data source selection
server_label = tk.Label(root, text="Server:")
server_label.grid(row=8, column=0, pady=5)

static_radio = tk.Radiobutton(
    root,
    text="Static",
    variable=graphql_var,
    value=False,
    command=lambda: toggle_moveset_dropdown(False),
)
static_radio.grid(row=8, column=1, padx=(50, 0), pady=5, sticky="w")

graphql_radio = tk.Radiobutton(
    root,
    text="GraphQL",
    variable=graphql_var,
    value=True,
    command=lambda: toggle_moveset_dropdown(True),
)
graphql_radio.grid(row=8, column=1, padx=(0, 50), pady=5, sticky="e")

# Function Buttons
add_query_button = tk.Button(root, text="Add Query", command=add_query)
add_query_button.grid(row=9, column=0, padx=(50, 0), pady=5, sticky="w")

undo_query_button = tk.Button(root, text="Undo Query", command=undo_query)
undo_query_button.grid(row=9, column=0, padx=(0, 50), pady=5, sticky="e")

clear_log_button = tk.Button(root, text="Clear Log", command=clear_log)
clear_log_button.grid(row=9, column=1, padx=(80, 0), pady=5, sticky="w")

reset_data_button = tk.Button(root, text="Reset Data File", command=reset_data_file)
reset_data_button.grid(row=9, column=1, padx=(0, 80), pady=5, sticky="e")

# Query Log
query_log = tk.Text(root, height=4, width=100)
query_log.grid(row=10, columnspan=2, padx=5, pady=5)

remaining_queries = ""
for query in queries:
    remaining_queries += f"{query}\n"
query_log.delete('1.0', tk.END)
query_log.insert(tk.END, remaining_queries)
query_log.see(tk.END)
query_log.config(state=tk.DISABLED)

# Console Log
console_log = tk.Text(root, height=4, width=100, state=tk.DISABLED)
console_log.grid(row=11, columnspan=2, padx=5, pady=5)

# Footer

applied_patches_label = tk.Label(root, text="Applied Patches:")
applied_patches_label.grid(row=12, column=0, padx=(10, 0), pady=5, sticky="w")

fairy_patch_checkbox = tk.Checkbutton(root, text="Fairy Type", variable=fairy_patch_var, command=fairy_type_patch_warning)
fairy_patch_checkbox.grid(row=12, column=0, padx=(0, 20), pady=5)

expanded_poke_checkbox = tk.Checkbutton(root, text="Expanded PokeList", variable=expand_pokelist_var, command=toggle_poke_id_entry)
expanded_poke_checkbox.grid(row=12, column=0, padx=(40, 0), pady=5, sticky="e")

generate_xml_button = tk.Button(root, text="Generate XML", command=generate_xml)
generate_xml_button.grid(row=12, column=1, pady=5)

root.mainloop()
