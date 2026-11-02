#!/bin/bash
# usage: _sweep.sh name D P A RAIL RUNG   (rebuilds the board for the candidate, routes once, reports failed nets)
cd "$(dirname "$0")/.."
n=$1
DNA_D=$2 DNA_P=$3 DNA_A=$4 DNA_RAIL=$5 DNA_RUNG=$6 PYTHONPATH=gen/_deps/py313 python gen/make_dna_geometry.py > gen/_runs/sw_$n.geo 2>&1 || { echo "$n geometry FAILED"; exit; }
DNA_DEPS=gen/_deps/py311 "/c/Program Files/KiCad/9.0/bin/python.exe" gen/rebuild_dna_board.py > gen/_runs/sw_$n.rebuild 2>&1 || { echo "$n rebuild FAILED: $(tail -1 gen/_runs/sw_$n.rebuild)"; exit; }
"/c/Program Files/KiCad/9.0/bin/python.exe" gen/route_prep.py > /dev/null 2>&1
WS=0.15 CL=0.16 WP=0.2 EDGE=0.56 VIAD=0.56 OUT=gen/_runs/sw_$n.json python gen/route_board.py > /dev/null 2> gen/_runs/sw_$n.log
python -c "import json;f=json.load(open('gen/_runs/sw_$n.json'))['failed'];print('$n D$2 P$3 A$4 R$5 U$6: failed nets',len(f),f[:6]); print(open('gen/_runs/sw_$n.geo').read().split('\n')[1])"
