"""Run kohya sdxl_train_network with sd-scripts root on sys.path (portable Python safe)."""
import os, sys, runpy
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.insert(0, root)
os.chdir(root)
# Replace argv so sdxl_train_network sees its own flags only
sys.argv = [os.path.join(root, "sdxl_train_network.py")] + sys.argv[1:]
runpy.run_path(os.path.join(root, "sdxl_train_network.py"), run_name="__main__")
