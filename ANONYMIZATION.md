# Data Anonymization Notice

## Overview

All DICOM files in this dataset have been **fully anonymized** to comply with privacy regulations (GDPR, HIPAA).

## Removed Information

The following patient-identifiable data has been systematically removed:

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
- SOP Instance UID (except for internal hashing)

### Comments/Notes
- Patient Comments
- Image Comments
- Requested Procedure Description

## Retained Information

Only **non-identifiable clinical and technical metadata** is preserved:

✅ **Clinical**: Diagnosis labels, View, Stage, Modality
✅ **Technical**: Number of frames, FPS, Duration, Image dimensions
✅ **Device**: Manufacturer, Model (anonymized)
✅ **Computed**: Motion features, Intensity metrics

## Case IDs

Case IDs are **cryptographic hashes** (SHA-256) derived from original SOP Instance UIDs, making them:
- Non-reversible
- Unique per case
- Reproducible for consistency

## Compliance

This anonymization process ensures:
- ✅ GDPR Article 4(1) compliance (data pseudonymization)
- ✅ HIPAA Safe Harbor method (all 18 identifiers removed)
- ✅ Safe for public repository publication

## Verification

To verify anonymization:

```bash
python3 scripts/verify_anonymization.py
```

This script checks all generated files for any remaining sensitive data.

## Original Data

⚠️ **Original DICOM files with patient data are NOT included in this repository.**

Only the anonymized derived dataset (`data/dataset_built/`) is provided.
