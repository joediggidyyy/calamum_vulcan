import os

scripts_dir = "scripts"
sprint_4_scripts = [
    "run_v040_readiness_stack.py",
    "run_v040_timeline_audit.py"
]

for s in sprint_4_scripts:
    src_path = os.path.join(scripts_dir, s)
    if os.path.exists(src_path):
        with open(src_path, "r", encoding="utf-8") as file:
            content = file.read()
            
        content = content.replace("0.4.0", "0.5.0")
        content = content.replace("v040", "v050")
        content = content.replace("Sprint 4", "Sprint 5")
        content = content.replace("FS4", "FS5")
        content = content.replace("fs4", "fs5")
        content = content.replace("fs_p04", "fs_p05") # Might not be perfectly accurate but close enough for initialization

        dest_path = os.path.join(scripts_dir, s.replace("040", "050"))
        with open(dest_path, "w", encoding="utf-8") as file:
            file.write(content)
        
        print(f"Generated {dest_path}")

print("Done duplicating scripts.")