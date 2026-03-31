### 1. Dependencies

> **Download the Dependencies**

**Copy and paste** the following codes in **Ubuntu**

```bash
bash -lc '
set -e

PY=python3
PIP="$PY -m pip"

get_ver () {
  $PY - <<PY
from importlib import metadata
import sys
name = sys.argv[1]
try:
    print(metadata.version(name))
except metadata.PackageNotFoundError:
    print("")
PY
}

install_if_needed () {
  pkg="$1"
  want="$2"

  have="$(get_ver "$pkg")"
  if [ "$have" = "$want" ]; then
    echo "[OK]   $pkg==$want"
    return 0
  fi

  if [ -z "$have" ]; then
    echo "[MISS] $pkg==$want -> installing"
  else
    echo "[DIFF] $pkg: have $have, want $want -> reinstalling"
  fi

  if [ "$pkg" = "torch" ]; then
    $PIP install -U --force-reinstall --index-url https://download.pytorch.org/whl/cu126 "torch==$want"
  else
    $PIP install -U --force-reinstall "$pkg==$want"
  fi
}

install_if_needed fastapi 0.128.0
install_if_needed uvicorn 0.38.0
install_if_needed python-multipart 0.0.21
install_if_needed torch 2.8.0+cu126
install_if_needed transformers 4.57.1
install_if_needed datasets 4.4.1
install_if_needed sentence-transformers 5.1.2
install_if_needed numpy 2.1.2
install_if_needed pandas 2.3.3
install_if_needed bertopic 0.17.4
install_if_needed scikit-learn 1.7.2
install_if_needed umap-learn 0.5.9.post2
install_if_needed hdbscan 0.8.41
install_if_needed tqdm 4.67.1
install_if_needed matplotlib 3.10.7
install_if_needed seaborn 0.13.2
install_if_needed plotly 6.4.0

echo "Done."
'

```



> **Offload the Dependencies**

```python
bash -lc '
set -e

PY=python3
PIP="$PY -m pip"

PKGS=(
  fastapi
  uvicorn
  python-multipart
  torch
  transformers
  datasets
  sentence-transformers
  numpy
  pandas
  bertopic
  scikit-learn
  umap-learn
  hdbscan
  tqdm
  matplotlib
  seaborn
  plotly
)

for p in "${PKGS[@]}"; do
  echo "[UNINSTALL] $p"
  $PIP uninstall -y "$p" || true
done

echo "Done."
'
```



> **Version Check**

```python
import platform
import sys

from importlib import metadata

def _v(dist_name: str) -> str:
    try:
        return metadata.version(dist_name)
    except metadata.PackageNotFoundError:
        return "NOT INSTALLED"


# --- Web server stack ---
print(f"fastapi             : {_v('fastapi')}")
print(f"uvicorn             : {_v('uvicorn')}")
print(f"python-multipart     : {_v('python-multipart')}")  # import name is 'multipart'

# --- Core ML/NLP ---
print(f"torch               : {_v('torch')}")
print(f"transformers        : {_v('transformers')}")
print(f"datasets            : {_v('datasets')}")
print(f"sentence-transformers: {_v('sentence-transformers')}")

# --- CSV / Topic modelling ---
print(f"numpy               : {_v('numpy')}")
print(f"pandas              : {_v('pandas')}")
print(f"bertopic            : {_v('bertopic')}")
print(f"scikit-learn        : {_v('scikit-learn')}")  # import name is 'sklearn'
print(f"umap-learn          : {_v('umap-learn')}")     # import name is 'umap'
print(f"hdbscan             : {_v('hdbscan')}")

# --- Visualisation / utils used in your library code ---
print(f"tqdm                : {_v('tqdm')}")
print(f"matplotlib          : {_v('matplotlib')}")
print(f"seaborn             : {_v('seaborn')}")
print(f"plotly              : {_v('plotly')}")

# Optional: quick runtime info
try:
    import torch
    print(f"cuda_available      : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"cuda_device_name    : {torch.cuda.get_device_name(0)}")
except Exception:
    pass
```

```python
# ========== Output Result ==========
fastapi             : 0.128.0
uvicorn             : 0.38.0
python-multipart     : 0.0.21
torch               : 2.8.0+cu126
transformers        : 4.57.1
datasets            : 4.4.1
sentence-transformers: 5.1.2
numpy               : 2.1.2
pandas              : 2.3.3
bertopic            : 0.17.4
scikit-learn        : 1.7.2
umap-learn          : 0.5.9.post2
hdbscan             : 0.8.41
tqdm                : 4.67.1
matplotlib          : 3.10.7
seaborn             : 0.13.2
plotly              : 6.4.0
```



---



### 2. Customised package: SEDNA_BERT

> **Run the following codes in Ubuntu**

```python
conda activate <Your Interpreter Name>
```

> [!TIP]
>
> For example, `conda activate SEDNA`

```python
# The directory of SEDNA_BERT in the folder
cd "/mnt/f/Warwick_Module/ST415/Sedntiment_Analysis_Web/SEDNA_BERT_lib"
```

```python
# Install as a Library
pip install -e .
```



---



### 3. Launch the Local Web

> **Run the following codes in Ubuntu**

```python
cd "/mnt/f/Warwick_Module/ST415/Sedntiment_Analysis_Web"
```

```python
HF_HUB_OFFLINE=1 python main.py
```

