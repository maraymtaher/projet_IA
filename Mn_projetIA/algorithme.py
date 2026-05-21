
import json, math, random
import numpy as np

random.seed(42)
np.random.seed(42)

#  Charger les données
def charger_donnees():
    with open("eleveurs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["depot"], data["eleveurs"], data["parametres"]


#  Distances GPS (Haversine)
def haversine(p1, p2):
    R = 6371
    lat1, lat2 = math.radians(p1["lat"]), math.radians(p2["lat"])
    lon1, lon2 = math.radians(p1["lon"]), math.radians(p2["lon"])
    dlat, dlon = lat2-lat1, lon2-lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return round(6371*2*math.asin(math.sqrt(a)), 2)

def construire_matrice(depot, eleveurs):
    tous = [depot] + eleveurs
    N = len(tous)
    matrice = [[0.0]*N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i != j:
                matrice[i][j] = haversine(tous[i], tous[j])
    return matrice


#  Volumes prévisionnels (moyenne mobile 7 jours)

def calculer_volumes(eleveurs):
    for e in eleveurs:
        base  = e["volume"]
        jours = np.arange(90)
        vols  = (base + jours*0.05
                 + base*0.1*np.sin(2*np.pi*jours/30)
                 + np.random.normal(0, base*0.15, 90))
        vols  = np.maximum(vols, 5)
        e["volume_prevu"] = round(float(np.mean(vols[-7:])), 1)
    return eleveurs


#  Évaluer un itinéraire

def evaluer(itineraire, depot, eleveurs, matrice, vitesse):
    heure     = depot["ouverture"]
    dist_tot  = 0
    penal_tot = 0
    details   = []
    pos       = 0

    for id_e in itineraire:
        e    = eleveurs[id_e - 1]
        dist = matrice[pos][id_e]
        dist_tot   += dist
        heure_arr   = heure + dist / vitesse

        if heure_arr < e["ouverture"]:
            heure_arr = e["ouverture"]
        elif heure_arr > e["fermeture"]:
            penal_tot += (heure_arr - e["fermeture"]) * 500

        details.append({
            "id":      e["id"],
            "eleveur": e["nom"],
            "lat":     e["lat"],
            "lon":     e["lon"],
            "arrivee": round(heure_arr, 2),
            "volume":  e.get("volume_prevu", e["volume"]),
            "retard":  round(max(0, heure_arr - e["fermeture"]), 2)
        })

        heure = heure_arr + e["duree_collecte"]
        pos   = id_e

    dist_ret  = matrice[pos][0]
    dist_tot += dist_ret
    h_retour  = heure + dist_ret / vitesse

    if h_retour > depot["fermeture"]:
        penal_tot += (h_retour - depot["fermeture"]) * 500

    return dist_tot + penal_tot, dist_tot, penal_tot, round(h_retour, 2), details

#  Algorithme Génétique
def creer_itineraire(eleveurs):
    ids = [e["id"] for e in eleveurs]
    random.shuffle(ids)
    return ids

def creer_population(taille, eleveurs):
    return [creer_itineraire(eleveurs) for _ in range(taille)]

def selection_tournoi(population, depot, eleveurs, matrice, vitesse, k=5):
    candidats = random.sample(population, k)
    candidats.sort(key=lambda x: evaluer(x, depot, eleveurs, matrice, vitesse)[0])
    return candidats[0]

def croisement_pmx(a, b):
    n  = len(a)
    p1 = random.randint(0, n-2)
    p2 = random.randint(p1+1, n-1)
    enfant = [None]*n
    enfant[p1:p2+1] = a[p1:p2+1]
    for g in b:
        if g not in enfant:
            for i in range(n):
                if enfant[i] is None:
                    enfant[i] = g
                    break
    return enfant

def mutation_swap(itin, taux=0.3):
    if random.random() < taux:
        i, j = random.sample(range(len(itin)), 2)
        itin[i], itin[j] = itin[j], itin[i]
    return itin

# Fonction principale appelée par Flask
def optimiser():
    depot, eleveurs, params = charger_donnees()
    vitesse  = params["vitesse_moyenne"]
    eleveurs = calculer_volumes(eleveurs)
    matrice  = construire_matrice(depot, eleveurs)

    TAILLE_POP = 200
    NB_GEN     = 300
    TAUX_MUT   = 0.3

    population    = creer_population(TAILLE_POP, eleveurs)
    meilleur      = None
    meilleur_cout = float('inf')
    historique    = []

    for gen in range(NB_GEN):
        scores = [(evaluer(i, depot, eleveurs, matrice, vitesse)[0], i)
                  for i in population]
        scores.sort(key=lambda x: x[0])

        if scores[0][0] < meilleur_cout:
            meilleur_cout = scores[0][0]
            meilleur      = scores[0][1][:]

        historique.append(meilleur_cout)

        nouvelle_pop = [i for _, i in scores[:10]]
        while len(nouvelle_pop) < TAILLE_POP:
            enfant = croisement_pmx(
                selection_tournoi(population, depot, eleveurs, matrice, vitesse),
                selection_tournoi(population, depot, eleveurs, matrice, vitesse)
            )
            nouvelle_pop.append(mutation_swap(enfant, TAUX_MUT))
        population = nouvelle_pop

    cout, dist, penal, retour, details = evaluer(
        meilleur, depot, eleveurs, matrice, vitesse
    )

    # Distance aléatoire de référence (méthode sans optimisation)
    itin_aleatoire = creer_itineraire(eleveurs)
    _, dist_base, _, _, _ = evaluer(
        itin_aleatoire, depot, eleveurs, matrice, vitesse
    )

    return {
        "distance":      round(dist, 2),
        "distance_base": round(dist_base, 2),
        "penalites":     round(penal, 1),
        "retour":        retour,
        "nb_eleveurs":   len(eleveurs),
        "itineraire":    details,
        "historique":    historique[::10],
        "depot": {
            "nom": depot["nom"],
            "lat": depot["lat"],
            "lon": depot["lon"]
        }
    }

# Test direct
if __name__ == "__main__":
    print("Lancement optimisation 100 eleveurs...")
    r = optimiser()
    print(f"Distance optimisee : {r['distance']} km")
    print(f"Distance aleatoire : {r['distance_base']} km")
    gain = round((1 - r['distance']/r['distance_base'])*100, 1)
    print(f"Gain               : -{gain}%")
    print(f"Penalites          : {r['penalites']} pts")
    print(f"Retour depot       : {r['retour']}h")
    print(f"Nb eleveurs        : {r['nb_eleveurs']}")
