"""
Convertitore Ufficiale TAC DICOM - Tesi Thomas
Estrae la slice centrale da ogni serie DICOM, la converte in PNG e genera i metadati.
"""
import os
import json
import uuid
import pydicom
import numpy as np
import matplotlib.pyplot as plt

# Percorsi del progetto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAC_DIR = os.path.join(BASE_DIR, "data", "raw_data", "TAC")
OUTPUT_IMG_DIR = os.path.join(BASE_DIR, "data", "dataset_built", "images", "tac_extracted")

# Creiamo la cartella di output se non esiste
os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

# Descrizioni cliniche simulate basate sul tipo di tesi multimodale (Cardio/Toracica)
REFERTI_SERIE = {
    "series-00000": "Scansione TC del torace ad alta risoluzione (HRCT). Si evidenzia regolare espansione dei campi polmonari, assenza di versamento pleurico. Parenchima polmonare indenne da lesioni infiltrative a focolaio in atto.",
    "series-00001": "Angio-TC del distretto toracico e della radice aortica. Calibro dell'aorta ascendente nei limiti della norma. Regolare pervietà dei principali rami arteriosi emergenti dall'arco aortico.",
    "series-00002": "TC Torace di controllo. Presenza di lievi strie di disventilazione basale bilaterale. Non si osservano linfoadenomegalie di rilievo nelle stazioni mediastiniche ed ilari esaminate.",
    "series-00003": "Scansione TC cardiaca di sincronizzazione. Studio della morfologia delle camere cardiache. Ventricolo sinistro nei limiti volumetrici, spessori parietali conservati in assenza di evidenti difetti di perfusione.",
    "series-00004": "TC del torace con mezzo di contrasto, fase tardiva. Regolare distribuzione del contrasto nelle strutture vascolari mediastiniche. Profilo cardiaco globale omogeneo e nei limiti morfologici."
}

def converti_slice_dicom(dcm_path, output_png_path):
    """Legge il file .dcm e lo salva in PNG applicando la scala di grigi medica."""
    try:
        ds = pydicom.dcmread(dcm_path)
        # Estrae la matrice di pixel
        img_array = ds.pixel_array
        
        # Applica il windowing se presente nei metadati DICOM per migliorare il contrasto visivo
        if 'WindowCenter' in ds and 'WindowWidth' in ds:
            wc = ds.WindowCenter
            ww = ds.WindowWidth
            if isinstance(wc, pydicom.multival.MultiValue): wc = wc[0]
            if isinstance(ww, pydicom.multival.MultiValue): ww = ww[0]
            
            # Formula di normalizzazione del contrasto medico
            ymin, ymax = 0, 255
            img_array = ((img_array - (wc - ww/2)) / ww) * (ymax - ymin) + ymin
            img_array = np.clip(img_array, ymin, ymax)

        # Salva in scala di grigi nativa senza assi cartesiani
        plt.imsave(output_png_path, img_array, cmap='gray')
        return True
    except Exception as e:
        print(f"[Errore] Impossibile convertire {os.path.basename(dcm_path)}: {e}")
        return False

def main():
    print("--- INIZIO ELABORAZIONE E CONVERSIONE TAC DICOM ---")
    
    if not os.path.exists(TAC_DIR):
        print(f"[ERRORE] Cartella TAC non trovata in: {TAC_DIR}")
        return

    # Cerchiamo le cartelle delle serie
    serie_folders = [f for f in os.listdir(TAC_DIR) if os.path.isdir(os.path.join(TAC_DIR, f))]
    serie_folders.sort()
    
    lines_to_add = []
    
    for serie in serie_folders:
        serie_path = os.path.join(TAC_DIR, serie)
        # Prendiamo tutti i file .dcm all'interno della serie
        dcm_files = [f for f in os.listdir(serie_path) if f.endswith('.dcm')]
        dcm_files.sort()
        
        if not dcm_files:
            print(f"[Avviso] La cartella {serie} non contiene file .dcm. Salto.")
            continue
            
        total_slices = len(dcm_files)
        # Troviamo la fetta centrale esatta della serie (es: la numero 100 su 200)
        middle_index = total_slices // 2
        middle_dcm_name = dcm_files[middle_index]
        middle_dcm_path = os.path.join(serie_path, middle_dcm_name)
        
        print(f"[Serie: {serie}] Trovate {total_slices} fette. Estrazione della slice centrale: {middle_dcm_name}...")
        
        # Definiamo il nome del file PNG finale
        png_filename = f"{serie}_slice_{middle_index}.png"
        output_png_path = os.path.join(OUTPUT_IMG_DIR, png_filename)
        
        # Eseguiamo la conversione medica reale
        success = converti_slice_dicom(middle_dcm_path, output_png_path)
        
        if success:
            # Recuperiamo il referto clinico associato a quella serie
            referto = REFERTI_SERIE.get(serie, "Scansione TC toraco-cardiaca. Visualizzazione di fette assiali per lo studio delle strutture anatomiche e vascolari.")
            
            # Creiamo la riga per il dataset
            j_line = {
                "id": f"tac_{serie.replace('series-', '')}",
                "image_path": f"data/dataset_built/images/tac_extracted/{png_filename}",
                "modality": "CT",
                "label": "Tomografia Computerizzata (Torace)",
                "description": referto
            }
            lines_to_add.append(j_line)
            print(f"[OK] Slice salvata in: {j_line['image_path']}")

    # Scriviamo il file temporaneo con i risultati delle TAC
    temp_out = os.path.join(BASE_DIR, "data", "dataset_built", "tac_rows.json")
    with open(temp_out, "w", encoding="utf-8") as out_f:
        json.dump(lines_to_add, out_f, indent=4, ensure_ascii=False)
        
    print(f"\n[SUCCESS] Elaborate {len(lines_to_add)} serie TAC DICOM!")
    print(f"[Info] Dati temporanei salvati in: {temp_out}")

if __name__ == "__main__":
    main()