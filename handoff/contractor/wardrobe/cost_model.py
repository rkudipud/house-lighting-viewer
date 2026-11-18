"""Retained equal-scope quantity and pricing formulae, without retired placement dependencies.

Inputs/rates come from storage-current.json. This verifies the unchanged reference
allowances; it does not price an unmeasured R04 split design or select R05 loft leaves.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "storage-current.json").read_bytes())
LEDGER = DATA["cost_comparison"]
R = {k: (v["low"], v["high"]) for k, v in LEDGER["rates"].items()}
SQFT, FT, HC = 10.7639, 3.28084, 2.0
DENS = {"ply18": 11.7, "ply9": 5.85, "hdhmr18": 15.7, "liner": 1.15,
        "granite12": 32.4, "granite16": 43.2, "stone20": 54.0, "acp": 5.5}


def unit(room, values):
    lc, nb, ns, nd, nl, wl, locks, rails_m, loft_len, loft_leaves, ends = values
    depth, sd = (.28, .26) if room == "R04a" else (.58, .55)
    return dict(id=f"ST-{room}-WR01+LF01", room=room, lc=lc, nb=nb, ns=ns, nd=nd,
                nl=nl, wl=wl, locks=locks, rails_m=rails_m, loft_len=loft_len,
                loft_leaves=loft_leaves, exposed_ends=ends, d=depth, sd=sd,
                bw=(lc-(nb+1)*.018)/nb, front_sqft=(lc*2.10+loft_len*.95)*SQFT)


UNITS = [unit(room, values) for room, values in DATA["quantity_model_inputs"].items()]


def qty(u):
    q = {}
    q["carcass_m2"] = (u["nb"]+1)*HC*u["d"]+2*u["lc"]*u["d"]
    q["shelves_m2"] = u["ns"]*u["bw"]*u["sd"]
    q["drawer_box_m2"], q["drawer_bottom_m2"] = u["nd"]*.21, u["nd"]*.20
    q["back_m2"], q["shutter_m2"] = u["lc"]*HC, u["nl"]*u["wl"]*2
    q["loft_shutter_m2"] = u["loft_len"]*.85
    q["loft_frame_m2"] = (2*u["loft_len"]+(u["loft_leaves"]+1)*.95)*.075
    q["ply_plinth_m2"] = 4*u["lc"]*.10
    q["stone_plinth_m2"] = (u["lc"]+.025)*(u["d"]+.02)+u["lc"]*.10
    q["exposed_end_m2"] = u["exposed_ends"]*HC*u["d"]
    q["edge_rm"] = (2*HC+(u["nb"]-1)*HC+2*u["lc"]+u["ns"]*u["bw"] +
                    u["nl"]*2*(u["wl"]+2)+u["loft_leaves"]*2*(u["loft_len"]/u["loft_leaves"]+.85))
    q["stone_edge_rft"] = (2*HC+(u["nb"]-1)*HC+2*u["lc"]+u["ns"]*u["bw"])*FT
    q["hinges"] = u["nl"]*4+u["loft_leaves"]*2
    q["front_sqft"] = u["front_sqft"]
    panels = [(HC,u["d"])]*(u["nb"]+1)+[(u["lc"],u["d"])]*2+[(u["bw"],u["sd"])]*u["ns"]
    q["alu_carcass_m"] = .75*sum(2*(a+b) for a,b in panels)
    q["alu_shutter_m"] = u["nl"]*(2*(u["wl"]+2)+u["wl"])+u["loft_leaves"]*2*(u["loft_len"]/u["loft_leaves"]+.85)
    return {k: round(v,3) for k,v in q.items()}


def rng(key, amount):
    return [x*amount for x in R[key]]


def add(acc, name, values):
    previous = acc.get(name, [0,0])
    acc[name] = [a+b for a,b in zip(previous,values)]


def sums(*values):
    return [sum(column) for column in zip(*values)]


def board(acc, name, key, area):
    add(acc,name,[v*(1+w) for v,w in zip(rng(key,area*SQFT),R["wastage_board"])])


def shutters(acc,q,key="ply18"):
    board(acc,"shutters_board",key,q["shutter_m2"]+q["loft_shutter_m2"]+q["loft_frame_m2"])


def laminate(acc,q,inside,outside):
    add(acc,"laminate_liner_edge",sums(rng("lam1",outside*SQFT),rng("liner",inside*SQFT),rng("edge",q["edge_rm"])))


def calculate(option,u):
    q,acc,wt = qty(u),{},{}
    sh,fr = q["shutter_m2"]+q["loft_shutter_m2"],u["front_sqft"]
    if option in ("OPT-A","OPT-E","OPT-E-H"):
        wood = q["carcass_m2"]+q["shelves_m2"]+q["drawer_box_m2"]+(q["ply_plinth_m2"] if option=="OPT-A" else 0)
        board(acc,"carcass_board","ply18",wood)
        board(acc,"back_board","ply9",q["back_m2"]+q["drawer_bottom_m2"])
        shutters(acc,q,"hdhmr18" if option=="OPT-E-H" else "ply18")
        laminate(acc,q,2*(q["carcass_m2"]+q["shelves_m2"])+q["back_m2"]+sh,
                 sh+q["exposed_end_m2"]+(u["lc"]*.10 if option=="OPT-A" else 0))
        add(acc,"labour",sums(rng("carpenter",fr),rng("lam_labour",fr)))
        if option!="OPT-A":
            add(acc,"stone_plinth_kerb",sums(rng("plinth_stone",q["stone_plinth_m2"]*SQFT),
                                            rng("plinth_lay",q["stone_plinth_m2"]*SQFT),rng("kerb",u["lc"])))
            wt["stone"]=q["stone_plinth_m2"]*DENS["stone20"]
        wt["board"]=wood*DENS["ply18"]+(q["back_m2"]+q["drawer_bottom_m2"])*DENS["ply9"]+sh*DENS["hdhmr18" if option=="OPT-E-H" else "ply18"]
        wt["laminate"]=(2*(q["carcass_m2"]+q["shelves_m2"])+2*sh)*DENS["liner"]
    elif option in ("OPT-C","OPT-D"):
        g = ((q["carcass_m2"]+q["shelves_m2"]) if option=="OPT-C" else q["back_m2"])+q["stone_plinth_m2"]
        add(acc,"granite_12mm",[v*(1+w)*(1+p) for v,w,p in zip(rng("granite",g*SQFT),R["wastage_stone"],R["thin_premium"])])
        edge = q["stone_edge_rft"] if option=="OPT-C" else u["lc"]*2*FT
        fix = R["stone_fix"] if option=="OPT-C" else [x/2 for x in R["stone_fix"]]
        add(acc,"granite_fab_edges_fixings",sums(rng("granite_fab",g*SQFT),rng("stone_edge",edge),fix))
        add(acc,"stone_install_labour",rng("stone_install",(g if option=="OPT-C" else q["back_m2"])*SQFT))
        board(acc,"back_board","ply9",q["drawer_bottom_m2"])
        shutters(acc,q)
        add(acc,"stone_plinth_kerb",rng("kerb",u["lc"]))
        if option=="OPT-C":
            board(acc,"wood_in_granite_option","ply18",q["drawer_box_m2"]+u["nl"]*2*.08)
            laminate(acc,q,sh,sh)
            add(acc,"labour",[a*.5+b for a,b in zip(rng("carpenter",fr),rng("lam_labour",sh*SQFT))])
            wt["stone"]=g*DENS["granite12"]
            wt["stone_if_16mm"]=g*DENS["granite16"]
            wt["board"]=(q["drawer_box_m2"]+u["nl"]*.16+sh)*DENS["ply18"]
            wt["laminate"]=2*sh*DENS["liner"]
        else:
            board(acc,"carcass_board","ply18",q["carcass_m2"]+q["shelves_m2"]+q["drawer_box_m2"])
            laminate(acc,q,2*(q["carcass_m2"]+q["shelves_m2"])+sh,sh+q["exposed_end_m2"])
            add(acc,"labour",sums(rng("carpenter",fr),rng("lam_labour",fr)))
            wt["stone"]=q["back_m2"]*DENS["granite12"]+q["stone_plinth_m2"]*DENS["stone20"]
            wt["board"]=(q["carcass_m2"]+q["shelves_m2"]+q["drawer_box_m2"]+sh)*DENS["ply18"]+q["drawer_bottom_m2"]*DENS["ply9"]
            wt["laminate"]=(2*(q["carcass_m2"]+q["shelves_m2"])+2*sh)*DENS["liner"]
    elif option in ("OPT-B1","OPT-F"):
        car=[q["alu_carcass_m"]*r for r in R["alu_kgm"]]
        fronts=[q["alu_shutter_m"]*r for r in R["alu_kgm"]] if option=="OPT-B1" else [0,0]
        acp=q["carcass_m2"]+q["shelves_m2"]+q["back_m2"]+(sh if option=="OPT-B1" else 0)
        add(acc,"aluminium_profiles",[(car[n]+fronts[n])*R["alu_kg"][n]*[1.10,1.15][n] for n in (0,1)])
        board(acc,"acp_infill","acp",acp)
        board(acc,"drawer_boxes","ply18" if option=="OPT-F" else "acp",q["drawer_box_m2"]+q["drawer_bottom_m2"])
        if option=="OPT-F":
            shutters(acc,q)
            laminate(acc,q,sh,sh)
            add(acc,"labour",[.7*a+.4*b+c for a,b,c in zip(rng("alu_fab",fr),rng("carpenter",fr),rng("lam_labour",sh*SQFT))])
            wt["board"]=(sh+q["drawer_box_m2"])*DENS["ply18"]
            wt["laminate"]=2*sh*DENS["liner"]
        else:
            add(acc,"labour",rng("alu_fab",fr))
        wt["aluminium_profiles_lo_hi"]=[round(car[n]+fronts[n],1) for n in (0,1)]
        wt["acp"]=acp*DENS["acp"]
    else:
        raise ValueError("Unknown material option: "+option)
    add(acc,"hardware",sums(rng("hinge",q["hinges"]),rng("runner",u["nd"]),rng("rail",u["rails_m"]),
                           rng("handle",u["nl"]+u["loft_leaves"]),rng("lock",u["locks"]),rng("pins",u["ns"])))
    parts={k:[int(round(n,-1)) for n in v] for k,v in acc.items()}
    total=[sum(v[n] for v in parts.values()) for n in (0,1)]
    weight=sum(v for k,v in wt.items() if isinstance(v,(int,float)) and k!="stone_if_16mm")
    if "aluminium_profiles_lo_hi" in wt:
        weight+=sum(wt["aluminium_profiles_lo_hi"])/2
    return q,parts,total,round(weight,1)


def verify():
    units={u["id"]:u for u in LEDGER["units"]}
    checked=0
    for u in UNITS:
        assert qty(u)==units[u["id"]]["quantities"],u["id"]+" quantities"
        for option,record in LEDGER["options"].items():
            q,parts,total,weight=calculate(option,u)
            expected=record["per_unit"][u["id"]]
            assert parts==expected["breakdown"],(option,u["id"],"breakdown",parts,expected["breakdown"])
            assert total==expected["inr"],(option,u["id"],"total")
            assert weight==expected["installed_weight_kg_excl_contents"],(option,u["id"],"weight")
            checked+=1
    return checked


if __name__=="__main__":
    print(json.dumps({"verified_option_unit_calculations":verify(),"rates_changed":False}))
