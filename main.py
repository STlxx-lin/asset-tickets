import sys
import os

# Add project root to path to ensure src is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
