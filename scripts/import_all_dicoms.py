# Script for import DICOM file
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.services.doc_service import import_all_rawdata_dicoms

if __name__ == "__main__":
    result = import_all_rawdata_dicoms()
    print(f"imported {result['imported']} file from {result['from']} to {result['to']}")