
"""
Main entry point for Crypto Data Fetcher
"""

import sys
import traceback

def main():
    """Main application entry point"""
    # Check for required packages
    try:
        import pandas
        import numpy
        import requests
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("\nPlease install required packages:")
        print("pip install pandas numpy requests")
        
        if sys.platform == 'win32':
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Missing Dependencies", 
                    f"Missing required package: {e}\n\nPlease run:\npip install pandas numpy requests")
                root.destroy()
            except:
                pass
        
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Try to import pybit for Bybit support
    try:
        import pybit
    except ImportError:
        print("Note: pybit not installed. Bybit support disabled.")
        print("To enable Bybit, run: pip install pybit")
    
    # Create and run GUI
    try:
        from gui import BybitGUI
        import tkinter as tk
        
        root = tk.Tk()
        app = BybitGUI(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting GUI: {e}")
        traceback.print_exc()
        
        if sys.platform == 'win32':
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error", f"Failed to start application:\n\n{str(e)}")
                root.destroy()
            except:
                pass
        
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()