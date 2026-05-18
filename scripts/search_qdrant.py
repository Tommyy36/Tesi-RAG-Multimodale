"""
Script di Retrieval e Ricerca Multimodale - Tesi Thomas
Inizializza Qdrant in RAM, carica il dataset unificato e permette di fare query cliniche interattive.
"""
import os
import sys

# Forza Python a vedere la cartella scripts per evitare errori di import
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from google import genai
from dotenv import load_dotenv

# Import assoluto dal manager funzionante
from index_Qdrant import get_vectorstore, EMB_MODEL_NAME

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def cerca_nel_database(query_testo: str, limit_risultati: int = 2):
    """Prende una frase, genera l'embedding e interroga Qdrant."""
    print(f"\n🔎 [Query Utente] '{query_testo}'")
    
    # 1. Inizializziamo il database in memoria (attiva merge e indicizzazione)
    qdrant_client = get_vectorstore()
    
    # 2. Generiamo l'embedding della query con lo stesso modello dei documenti
    response = client.models.embed_content(
        model=EMB_MODEL_NAME,
        contents=query_testo
    )
    query_vector = response.embeddings[0].values
    
    # 3. Cerchiamo nella collezione dei casi medici usando il metodo aggiornato query_points
    print("\n--- RISULTATI DALLA COLLEZIONE 'CASES' (Multimodale) ---")
    risultati_casi = qdrant_client.query_points(
        collection_name="cases",
        query=query_vector,
        limit=limit_risultati
    ).points
    
    for i, res in enumerate(risultati_casi):
        p = res.payload
        # Lo score indica la vicinanza semantica (più è alto vicino a 1.0, più sono simili)
        score = getattr(res, 'score', 0.0)
        print(f"\n[Match #{i+1}] Score di Somiglianza: {score:.4f}")
        print(f" -> Modalità: {p.get('modality')} | ID: {p.get('case_id')}")
        print(f" -> Label: {p.get('label')}")
        print(f" -> Path Immagine: {p.get('image_path')}")
        print(f" -> Descrizione Clinica: {p.get('text')}")

    # 4. Cerchiamo nella collezione delle linee guida sempre con query_points
    print("\n--- RISULTATI DALLA COLLEZIONE 'GUIDELINES' (Letteratura Medica) ---")
    try:
        risultati_guide = qdrant_client.query_points(
            collection_name="guidelines",
            query=query_vector,
            limit=limit_risultati
        ).points
        
        if risultati_guide:
            for i, res in enumerate(risultati_guide):
                p = res.payload
                score = getattr(res, 'score', 0.0)
                print(f"\n[Documento #{i+1}] Score: {score:.4f} | Fonte: {p.get('source')}")
                print(f" -> Estratto: {p.get('text')[:200]}...")
        else:
            print("[Info] Nessuna linea guida rilevante trovata o cartella vuota.")
    except Exception as e:
        print(f"[Info] Salto ricerca linee guida: {e}")

if __name__ == "__main__":
    print("--- TEST DI VERIFICA RETRIEVAL MULTIMODALE ---")
    
    # Query pilota: cerchiamo un caso di infarto acuto
    query_test = "Paziente con forte dolore al petto, sospetto infarto miocardico acuto in corso"
    
    cerca_nel_database(query_test, limit_risultati=2)