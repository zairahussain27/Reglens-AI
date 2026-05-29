# Official Government URLs for RegLens AI
# Only these trusted sources are used for data ingestion

GOVERNMENT_SOURCES = [
    # RBI Documents
    "https://www.rbi.org.in/Upload/Publications/PDFs/KYC_MASTER_DIRECTIONS_2016.pdf",
    "https://www.rbi.org.in/Upload/DOCs/Guidelines_Payment_Aggregators.pdf",
    "https://www.rbi.org.in/Upload/Publications/PDFs/Digital_Lending_Guidelines_2022.pdf",
    "https://www.rbi.org.in/Upload/Publications/PDFs/NBFC_Master_Directions.pdf",

    # GST Documents
    "https://www.gst.gov.in/download/cgst_rules.pdf",

    # MSME Documents
    "https://www.msme.gov.in/sites/default/files/udyam-registration.pdf",

    # FEMA Documents
    "https://www.rbi.org.in/Upload/Publications/PDFs/FEMA_1999.pdf",

    # Companies Act
    "https://www.mca.gov.in/Ministry/pdf/CompaniesAct2013.pdf",
]

# Usage example:
# from src.ingest import ingest_all_from_urls
# ingest_all_from_urls(GOVERNMENT_SOURCES)