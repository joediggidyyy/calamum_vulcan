import os
import re

doc_dir = "docs"
sprint_4_files = [
    "Samsung_Android_Flashing_Platform_0.4.0_Detailed_Planning.md",
    "Samsung_Android_Flashing_Platform_0.4.0_Execution_Evidence.md",
    "Samsung_Android_Flashing_Platform_0.4.0_Testing_and_Readiness_Plan.md",
    "Samsung_Android_Flashing_Platform_0.4.0_Closeout_and_Prepackage_Checklist.md"
]

replacements = {
    "0.4.0": "0.5.0",
    "Sprint 4": "Sprint 5",
    "Stage II": "Stage III",
    "FS4": "FS5",
    "fs4": "fs5",
    "session and safe-path extraction": "efficient integrated transport extraction",
    "2026-04-22": "2026-04-23" 
}

for f in sprint_4_files:
    # Handle the fact that Detailed Planning for 0.4.0 might not exist or might need to be sourced from 0.1.0
    src_path = os.path.join(doc_dir, f)
    if not os.path.exists(src_path):
        if "Detailed_Planning" in f:
            src_path = os.path.join(doc_dir, "Samsung_Android_Flashing_Platform_0.1.0_Detailed_Planning.md")
        else:
            continue
            
    with open(src_path, "r", encoding="utf-8") as file:
        content = file.read()
        
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    dest_path = os.path.join(doc_dir, f.replace("0.4.0", "0.5.0"))
    
    with open(dest_path, "w", encoding="utf-8") as file:
        file.write(content)
        
    print(f"Generated {dest_path}")

print("Done generating Sprint 5 scaffolds.")