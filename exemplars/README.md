# Go Interface Pattern to Petri Net Converter

## Overview

This project converts Go concurrency patterns into simplified Petri net representations. The converter uses tree-sitter AST parsing to extract concurrent structures (goroutines, channels, select statements) and generates workflow nets (WF-nets) with basic control flow.

## Contents

- **`ip_to_petrinet.py`** - Main converter script
- **`wfnets/`** - Generated Petri nets for all 12 Interface Patterns
  - 12 DOT files (GraphViz format)
  - 12 LoLA files (verification format)
  - 12 PNG visualizations
- **`Technical_Report.pdf`** - Complete documentation with diagrams and analysis
- **`ip01_sendreceive/` through `ip12_syncorexchange/`** - Source exemplars

## Usage

```bash
# Install dependencies
pip install tree-sitter tree-sitter-go

# Run converter
python3 ip_to_petrinet.py

# View generated files
cd wfnets/
```

## Petri Net Structure

Each generated Petri net contains:
- **Places**: States (goroutine spawn, channel operations, select cases)
- **Transitions**: Events (go statements, send/receive operations)
- **Arcs**: Control flow between places and transitions
- **Initial Marking**: Single source place with one token (WF-net property)

**Note**: The current implementation generates simplified structural models focusing on control flow patterns. More detailed semantic modeling (e.g., data values, channel capacities, specific synchronization constraints) would require extending the converter.

## Results

All 12 Interface Patterns converted successfully. See `Technical_Report.pdf` for analysis and visualizations.

## Next Steps

Potential applications:
1. Structural pattern classification using Petri net features (place/transition counts, arc patterns)
2. Integration with existing bug detection tools (e.g., GoBench analysis)
3. Enhanced converter with richer semantic modeling

---

**Date**: November 20, 2026
