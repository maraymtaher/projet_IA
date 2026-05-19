# ============================================================
# app.py — Serveur Flask
# Projet IA2 : Optimisation Collecte de Lait
# ENASTIC N'Djaména | Marayim Tahir
# ============================================================
from flask import Flask, jsonify, render_template, request
from algorithme import optimiser

app = Flask(__name__)

@app.route("/")
def accueil():
    return render_template("index.html")

@app.route("/api/itineraire")
def itineraire():
    print("Calcul itineraire 100 eleveurs...")
    resultat = optimiser()
    print(f"OK ! Distance : {resultat['distance']} km | Penalites : {resultat['penalites']}")
    return jsonify(resultat)

@app.route("/api/confirmer/<int:id_eleveur>")
def confirmer(id_eleveur):
    statut   = request.args.get('statut', 'reussi')
    quantite = request.args.get('quantite', 0, type=float)
    print(f"Eleveur {id_eleveur} -> {statut} | {quantite}L")
    return jsonify({
        "statut":     "confirme",
        "id_eleveur": id_eleveur,
        "resultat":   statut,
        "quantite":   quantite
    })

if __name__ == "__main__":
    print("="*50)
    print("  Serveur Flask - Collecte de Lait")
    print("  PC      : http://localhost:5000")
    print("  Mobile  : http://<votre-IP>:5000")
    print("="*50)
    app.run(debug=True, host='0.0.0.0')