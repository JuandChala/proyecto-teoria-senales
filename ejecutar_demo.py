"""Atajo para ejecutar la demostración principal (útil si su editor solo tiene botón "Run").

Equivale a:  python -m src.main
"""
import sys

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
