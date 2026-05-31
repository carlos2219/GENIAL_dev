# Add this after the imports in main.py, around line 43 (after _setup_logging function):

# Suppress pdfminer debug logs
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("pdfminer.psparser").setLevel(logging.WARNING)
logging.getLogger("pdfminer.pdfinterp").setLevel(logging.WARNING)
