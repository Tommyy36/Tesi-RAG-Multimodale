"""
Parser Automatico Unity Imaging - Tesi Thomas
Legge i metadati geometrici dei keypoints e genera descrizioni cliniche in italiano
per il file documents.jsonl.
"""
import os
import json
import glob

# Percorsi del progetto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITY_DIR = os.path.join(BASE_DIR, "data", "raw_data", "Unity_Imaging")
LABELS_DIR = os.path.join(UNITY_DIR, "labels")
IMAGES_DIR = os.path.join(UNITY_DIR, "78") # La cartella con i PNG

def traduci_piani_e_punti(label_data: dict) -> str:
    """Traduce i metadati grezzi di Unity in una descrizione clinica fluida."""
    piani_rilevati = []
    punti_rilevati = []
    
    # 1. Identifica il piano ecocardiografico dal dizionario
    if label_data.get("plane_plax") == "yes" or label_data.get("unity-plax-1") == "yes":
        piani_rilevati.append("Asse Lungo Parasternale (PLAX)")
    if label_data.get("plane_a4c") == "yes" or label_data.get("unity-a4c-1") == "yes":
        piani_rilevati.append("Apicale 4 Camere (A4C)")
    if label_data.get("plane_a2c") == "yes" or label_data.get("unity-a2c-1") == "yes":
        piani_rilevati.append("Apicale 2 Camere (A2C)")
    if label_data.get("plane_a3c") == "yes" or label_data.get("imp-echo-stowell-a3c") == "yes":
        piani_rilevati.append("Apicale 3 Camere (A3C)")
        
    # 2. Controlla quali strutture anatomiche principali hanno punti attivi
    for punto, info in label_data.items():
        if isinstance(info, dict) and info.get("type") in ["on", "point", "active"]:
            if "ao-sinus" in punto:
                punti_rilevati.append("Seni di Valsalva dell'aorta")
            elif "ao-stj" in punto:
                punti_rilevati.append("Giunzione Sinotubulare")
            elif "lv-apex" in punto:
                punti_rilevati.append("Apice del Ventricolo Sinistro")
            elif "la-" in punto:
                punti_rilevati.append("Atrio Sinistro")
                
    # Rimuovi duplicati dalle liste
    punti_rilevati = list(set(punti_rilevati))
    
    # 3. Costruisci la frase per Gemini
    piano_str = " e ".join(piani_rilevati) if piani_rilevati else "proiezione non standard"
    descrizione = f"Simulazione ecocardiografica virtuale 3D generata in ambiente Unity, visualizzazione in {piano_str}."
    
    if punti_rilevati:
        descrizione += f" Il fotogramma presenta annotazioni geometriche attive e tracciamento dei keypoints per: {', '.join(punti_rilevati)}."
    else:
        descrizione += " Fotogramma utilizzato per l'addestramento della rete neurale sulla segmentazione delle camere cardiache."
        
    return descrizione

def main():
    print("--- INIZIO PARSING METADATI UNITY ---")
    
    # Cerchiamo il file principale delle etichette (es. labels-all.json o simili)
    # Se i dati sulle singole immagini sono spezzati, cerchiamo tutti i file .json
    json_files = glob.glob(os.path.join(LABELS_DIR, "*.json"))
    
    if not json_files:
        print(f"[ERRORE] Nessun file JSON trovato in {LABELS_DIR}")
        return
        
    print(f"[Info] Trovati {len(json_files)} file di configurazione delle label.")
    
    lines_to_add = []
    
    # Leggiamo i file JSON per estrarre le informazioni sulle immagini
    for json_path in json_files:
        filename = os.path.basename(json_path)
        print(f"[Lettura] Analizzo {filename}...")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Caso A: Il JSON ha le chiavi con i nomi dei file PNG (struttura a dizionario nidificato)
            for key, val in data.items():
                if key.endswith(".png") and isinstance(val, dict) and "labels" in val:
                    png_name = key
                    # Prendiamo le label specifiche di quell'immagine
                    img_labels = val["labels"]
                    
                    # Generiamo la descrizione clinica pulita
                    descrizione_clinica = traduci_piani_e_punti(img_labels)
                    
                    # Calcoliamo il percorso relativo che userà l'app
                    rel_img_path = f"data/raw_data/Unity_Imaging/78/{png_name}"
                    
                    # Creiamo la riga per il documents.jsonl
                    j_line = {
                        "id": f"unity_78_{png_name.split('-')[-1].replace('.png', '')}",
                        "image_path": rel_img_path,
                        "modality": "Unity_Simulation",
                        "label": "Ecocardiografia Virtuale Annotata",
                        "description": descrizione_clinica
                    }
                    lines_to_add.append(j_line)
                    
            # Caso B: Il JSON contiene la configurazione generale dei punti (come il primo esempio che mi hai fatto)
            # In questo caso cerchiamo se c'è un file labels-all.json che mappa i file.
        except Exception as e:
            print(f"[Avviso] Salto {filename} dovuto a errore di lettura o formato diverso: {e}")

    if not lines_to_add:
        print("[WARNING] Non è stato possibile associare automaticamente i dati ai file .png. Forziamo una lettura della cartella '78'.")
        # Fallback manuale: leggiamo i PNG nella cartella 78 e gli diamo una descrizione generica strutturata
        png_in_78 = glob.glob(os.path.join(IMAGES_DIR, "*.png"))
        print(f"[Info] Rilevati {len(png_in_78)} file PNG reali nella cartella '78'. Genero mapping standard.")
        
        for p_path in png_in_78:
            p_name = os.path.basename(p_path)
            j_line = {
                "id": f"unity_78_{uuid.uuid4().hex[:6]}",
                "image_path": f"data/raw_data/Unity_Imaging/78/{p_name}",
                "modality": "Unity_Simulation",
                "label": "Ecocardiografia Virtuale",
                "description": "Simulazione ecocardiografica tridimensionale estratti dall'ambiente Unity. Visualizzazione delle strutture cardiache ed endocardiche (Ventricolo Sinistro, Radice Aortica) per l'addestramento del modello di segmentazione dei keypoints anatomici."
            }
            lines_to_add.append(j_line)

    # Scriviamo un file temporaneo con i risultati di Unity
    temp_out = os.path.join(BASE_DIR, "data", "dataset_built", "unity_rows.json")
    with open(temp_out, "w", encoding="utf-8") as out_f:
        json.dump(lines_to_add, out_f, indent=4, ensure_ascii=False)
        
    print(f"\n[SUCCESS] Generati {len(lines_to_add)} casi clinici virtuali da Unity!")
    print(f"[Info] Dati temporanei salvati in: {temp_out}")

if __name__ == "__main__":
    main()