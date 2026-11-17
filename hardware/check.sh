#!/usr/bin/env bash
# Run KiCad's electrical (ERC) and design rule (DRC) checks and regenerate the
# schematic PDF and the board renders. Needs KiCad 10 (kicad-cli).
#   hardware/check.sh            reports in hardware/reports/
# Set KICAD_CLI if kicad-cli is not on the PATH, e.g. on macOS:
#   KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli hardware/check.sh
set -euo pipefail

cd "$(dirname "$0")"
cli=${KICAD_CLI:-kicad-cli}
mkdir -p reports images

"$cli" sch erc --severity-all -o reports/erc.rpt kicad/H2S_Sensor.kicad_sch
"$cli" pcb drc --schematic-parity --severity-all -o reports/drc.rpt kicad/H2S_Sensor.kicad_pcb
"$cli" sch export pdf -o schematic.pdf kicad/H2S_Sensor.kicad_sch
for side in top bottom; do
    "$cli" pcb render --side "$side" --quality high -w 1600 -h 1200 \
        -o "images/render-$side.png" kicad/H2S_Sensor.kicad_pcb
done

echo
grep -E '^\*\* Found' reports/drc.rpt || true
printf 'ERC: %s findings\n' "$(grep -c '^\[' reports/erc.rpt || true)"
echo "Compare with the reviewed list in hardware/README.md (section 'Design checks')."
