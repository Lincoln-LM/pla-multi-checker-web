import numpy as np
from numba_pokemon_prngs.lcrng import PokeRNGDiv
import json

#imports from main.py
from ..app import RESOURCE_PATH
from .core import *
from .filters import compare_all_ivs
from .data import natures, pktype, getSlotRanges, calcCharm, setLevel,get_bdsp_sprite

with open(RESOURCE_PATH + "resources/text_species_en.txt",encoding="utf-8") as text_species:
    SPECIES = text_species.read().split("\n")

enctypetomap = {
    "Grass":"land_mons",
    "RockSmash":"rock_smash_mons",
    "OldRod":"fishing_mons",
    "GoodRod":"fishing_mons",
    "SuperRod":"fishing_mons",
    "Surfing":"water_mons"
}

def populate_routes(gamever,enctype):
    type = enctypetomap[enctype]

    encounters = json.load(open(RESOURCE_PATH + f"resources/gen3/{gamever}_encounter.json"))

    locations = []

    for _,l in enumerate(encounters["encounters"]):
        if l.get(type) is not None:
            info = {
                "location":l["map"].replace("MAP_", '').replace("_", " ").replace("ROUTE", "ROUTE ").title(),
                "rawloc":l["map"]
            }
            locations.append(info)

    return locations

def populate_species(gamever,enctype,location):
    type = enctypetomap[enctype]

    encounters = json.load(open(RESOURCE_PATH + f"resources/gen3/{gamever}_encounter.json"))

    species = []
    table = None

    for _,l in enumerate(encounters["encounters"]):
        if l["map"] == location:
            table = l
            break

    for _,s in enumerate(table[type]["mons"]):
        dupe = False
        for _,i in enumerate(species):
            if i.get("raws", None) == s['species']:
                dupe = True
                break
        if not dupe:
            info = {
                "species":s["species"].replace("SPECIES_", '').title(),
                "raws":s["species"]
            }
            species.append(info)
    
    return species

def autofill(gamever,enctype,location,species):

    if species == "Any":
        return "Any"
    
    slots = []

    type = enctypetomap[enctype]

    encounters = json.load(open(RESOURCE_PATH + f"resources/gen3/{gamever}_encounter.json"))

    for _,l in enumerate(encounters["encounters"]):
        if l["map"] == location:
            table = l
            break
    
    for i,s in enumerate(table[type]["mons"]):
        if s["species"] == species:
            slots.append(i)

    return slots

def check_wilds(tid,sid,filter,delay,method,lead,encounter,rseSafari,rock,leadopt = "None",seed=0):

    result = {}

    type = enctypetomap[encounter["type"]]
    genc = json.load(open(RESOURCE_PATH + f"resources/gen3/{encounter['version']}_encounter.json"))
    table = None

    for _,l in enumerate(genc["encounters"]):
        if l["map"] == encounter["loc"]:
            table = l
            break


    tid = int(tid)
    sid = int(sid)
    tsv = tid ^ sid

    seed = int(seed,16)

    init = PokeRNGDiv(seed)
    init.advance(filter['minadv']+delay)

    cuteCharmFlag = False
    sync = False

    for i in range(0,filter['maxadv']+1):

        rng = PokeRNGDiv(init.seed)

        if encounter['type'] == "RockSmash":
            if rseSafari or not rock:
                rng.next()
            rockenccheck = rng.next_u16() % 2880
            if (rockenccheck) >= (table[type]['encounter_rate'] * 16):
                init.next()
                continue

            slot = getSlotRanges(rng.next_u16(),"RockSmash")
            level,species = setLevel(slot, rng.next_u16(), table[type])

            if rseSafari:
                rng.advance(1)
        elif encounter['type'] == "Grass":

            rng.next()
            slot = getSlotRanges(rng.next_u16(),"Grass")
            level,species = setLevel(slot, rng.next_u16(), table[type])

            if rseSafari:
                rng.next()

        elif encounter['type'] in ["Surfing", "OldRod", "GoodRod", "SuperRod"]:

            rng.next()
            
            slot = getSlotRanges(rng.next_u16(), encounter['type'])
            level,species = setLevel(slot, rng.next_u16(), table[type])

            if encounter['type'] == "GoodRod":
                slot -= 2
            elif encounter['type'] == "SuperRod":
                slot -= 5

            if rseSafari:
                rng.next()
        else:
            slot = 0
            level = 0
            species = "Egg"
        
        if lead == "None":
            nature = natures(rng.next_u16() % 25)
        elif lead == "Synch":
            if (rng.next_u16() & 1) == 0:
                #sync nature
                nature = leadopt
                sync = True
            else:
                #sync failed
                nature = natures(rng.next_u16() % 25)
        else:
            #covers Cute Charm
            cuteCharmFlag = (rng.next_u16() % 3) > 0
            nature = natures(rng.next_u16() % 25)

            #now search for PID that matches hunt nature
            '''
            while True:
                low = rng.next_u16()
                high = rng.next_u16()
                pid = setPID(high,low)
                if not ((pid % 25 != nature) or (cuteCharmFlag and not calcCharm(lead,pid))):
                    break
            '''

        low = rng.next_u16()
        high = rng.next_u16()
        pid = setPID(high,low)
        testnature = natures(pid%25)
        testcalccharm = calcCharm(leadopt,pid)
        while (natures(pid % 25) != nature) or (cuteCharmFlag and not calcCharm(leadopt,pid)):
            testnature = natures(pid%25)
            testcalccharm = calcCharm(leadopt,pid)
            low = rng.next_u16()
            high = rng.next_u16()
            pid = setPID(high,low)
        
        ability = pid & 1
        gender = pid & 255
        shiny,square = setShiny(tsv,high^low)

        if method == 1:
            iv1 = rng.next_u16()
            iv2 = rng.next_u16()
        elif method == 2:
            rng.next()
            iv1 = rng.next_u16()
            iv2 = rng.next_u16()
        else:
            iv1 = rng.next_u16()
            rng.next()
            iv2 = rng.next_u16()
        
        ivs = setIVs(iv1,iv2)
        hidden,power = calcHiddenPower(ivs)

        info = {
            "shiny": shiny,
            "square": square,
            "hidden": pktype(hidden),
            "power": power,
            "ability": ability,
            "nature": nature,
            "pid": pid,
            "gender": gender,
            "adv": i+filter['minadv'],
            "ivs": ivs,
            "slot": slot,
            "sync": sync,
            "level": level,
            "species": species,
            "sprite": get_bdsp_sprite(SPECIES.index(species),shiny)
        }

        if compare_all_ivs(filter['minivs'], filter['maxivs'], ivs):
            result[i] = info
    
        init.next()

    return result
            

            



    