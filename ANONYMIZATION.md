# Data Anonymization Notice

## Overview

All DICOM files and clinical records processed by this framework are **fully anonymized** at the ingestion and streaming layers to strictly comply with international medical privacy regulations (GDPR, HIPAA).

## Removed Information

The following patient-identifiable data fields are systematically removed or blocked during the file processing pipeline before generating vector embeddings:

### Patient Information
- Patient Name
- Patient ID
- Patient Birth Date
- Patient Age
- Patient Sex

### Study/Series Information
- Study Date & Time
- Series Date & Time
- Acquisition Date & Time
- Content Date & Time
- Study ID
- Series Number
- Instance Number
- Accession Number

### Healthcare Provider Information
- Institution Name & Address
- Referring Physician Name
- Performing Physician Name
- Operators Name
- Requesting Physician

### Unique Identifiers
- Study Instance UID
- Series Instance UID
- SOP Instance UID (except for internal tracking hashes)

### Comments/Notes
- Patient Comments
- Image Comments
- Requested Procedure Description

## Retained Information

Only **non-identifiable clinical, technical, and geometric metadata** is preserved within the unifed `documents.jsonl` dataset and the vector database collections:

- ✅ **Clinical**: Diagnosis labels, View, Modality (ECG, CT, Unity Simulation)
- ✅ **Technical**: Number of frames, FPS, Image dimensions, Volumetric slicing parameters
- ✅ **Computed**: Motion energy features, Mean intensity metrics, Spatial keypoints coord.

## Case IDs & File UUIDs

All tracking identifiers within the framework are managed securely:
- **Case IDs**: Cryptographic hashes (SHA-256) derived from the raw sequence metrics, making them non-reversible and unique per case.
- **File UUIDs**: Randomly generated unique identifiers assigned to temporary triage files inside `data/current/` to ensure full anonymization during live pipeline analysis.

## Compliance

This anonymization architecture ensures:
- ✅ **GDPR Article 4(1)** compliance (strict data pseudonymization workflows)
- ✅ **HIPAA Safe Harbor** method validation (all 18 explicit identifiers removed)
- ✅ Safe for public repository publication and academic demonstration

## Original Data

⚠️ **Original sensitive hospital DICOM files containing real patient data are NOT included in this repository.**

Only the anonymized derived dataset (`data/dataset_built/`) and isolated test samples inside `data/current/` are provided for pipeline evaluation.