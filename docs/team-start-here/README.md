# Team start-here file (to share offline)

`DTJ-Team-Start-Here.pdf` is the file Harsh shares with the team (WhatsApp, email, Drive): what each person needs, the laptop
install steps, who decides when Harsh isn't reachable, and how to get a store ready in a few hours. It holds no secrets.

It is printed from `DTJ-Team-Start-Here.html`. After editing the HTML (keep it in step with `docs/START-HERE.md`), rebuild the PDF
from this folder in Git Bash:

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --no-pdf-header-footer --run-all-compositor-stages-before-draw --virtual-time-budget=15000 --print-to-pdf="$(cygpath -w "$PWD")\DTJ-Team-Start-Here.pdf" "file:///$(cygpath -m "$PWD" | sed 's/ /%20/g')/DTJ-Team-Start-Here.html"
```
