#!/usr/bin/env python3
"""FIXED: Go to Petri Net with PROPER transitions"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
import subprocess
from tree_sitter import Language, Parser
import tree_sitter_go as tsgo

@dataclass
class Place:
    id: str
    label: str
    tokens: int = 0

@dataclass
class Transition:
    id: str
    label: str

@dataclass
class Arc:
    source: str
    target: str

@dataclass
class WFNet:
    name: str
    places: List[Place] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    arcs: List[Arc] = field(default_factory=list)

def parse_go_file(filepath: Path):
    parser = Parser(Language(tsgo.language()))
    with open(filepath) as f:
        code = f.read()
    
    # Get IP name
    ip_name = "Unknown"
    for line in code.split('\n'):
        if 'IP-' in line and line.startswith('//'):
            ip_name = line.strip('// ').split(':')[0]
            break
    
    tree = parser.parse(bytes(code, "utf8"))
    
    # Build WF-net
    net = WFNet(name=ip_name)
    
    # Count operations
    has_go = 'go func()' in code
    has_send = '<-' in code and 'ch <-' in code
    has_recv = '<-' in code and '<-ch' in code or '<- <-' in code
    has_select = 'select {' in code
    
    # Build simple but PROPER net
    net.places.append(Place("p0", "start", 1))
    net.places.append(Place("p1", "main_ready", 0))
    
    tid = 0
    
    if has_go:
        net.transitions.append(Transition(f"t{tid}", "spawn goroutine"))
        net.arcs.append(Arc("p0", f"t{tid}"))
        net.places.append(Place("p2", "goroutine_running", 0))
        net.arcs.append(Arc(f"t{tid}", "p1"))
        net.arcs.append(Arc(f"t{tid}", "p2"))
        tid += 1
        
        if has_send:
            net.transitions.append(Transition(f"t{tid}", "send on channel"))
            net.arcs.append(Arc("p2", f"t{tid}"))
            net.places.append(Place("p3", "channel_buffer", 0))
            net.arcs.append(Arc(f"t{tid}", "p3"))
            net.places.append(Place("p4", "go_done", 0))
            net.arcs.append(Arc(f"t{tid}", "p4"))
            tid += 1
        
        if has_recv:
            net.transitions.append(Transition(f"t{tid}", "receive from channel"))
            net.arcs.append(Arc("p1", f"t{tid}"))
            if has_send:
                net.arcs.append(Arc("p3", f"t{tid}"))
            net.places.append(Place("p5", "recv_done", 0))
            net.arcs.append(Arc(f"t{tid}", "p5"))
            tid += 1
    
    if has_select:
        net.transitions.append(Transition(f"t{tid}", "select choice"))
        if not has_go:
            net.arcs.append(Arc("p0", f"t{tid}"))
        else:
            net.arcs.append(Arc("p1", f"t{tid}"))
        net.places.append(Place("p6", "after_select", 0))
        net.arcs.append(Arc(f"t{tid}", "p6"))
        tid += 1
    
    # End place
    last_p = f"p{len(net.places)-1}"
    net.places.append(Place(f"p{len(net.places)}", "end", 0))
    net.transitions.append(Transition(f"t{tid}", "finish"))
    net.arcs.append(Arc(last_p, f"t{tid}"))
    if has_go and has_send:
        net.arcs.append(Arc("p4", f"t{tid}"))
    net.arcs.append(Arc(f"t{tid}", f"p{len(net.places)-1}"))
    
    return net

def generate_dot(net: WFNet, path: Path):
    lines = ['digraph PetriNet {', '  rankdir=LR;', '  node [fontname="Arial"];',
             f'  label="{net.name}";', '  labelloc=t; fontsize=14;', '']
    
    for p in net.places:
        shape = "doublecircle" if "start" in p.label or "end" in p.label else "circle"
        color = "#90EE90" if p.tokens > 0 else "#ADD8E6"
        lbl = p.label + (f" ({p.tokens})" if p.tokens > 0 else "")
        lines.append(f'  {p.id} [shape={shape}, style=filled, fillcolor="{color}", label="{lbl}"];')
    
    lines.append('')
    for t in net.transitions:
        lines.append(f'  {t.id} [shape=box, style=filled, fillcolor="#FFD700", label="{t.label}"];')
    
    lines.append('')
    for arc in net.arcs:
        lines.append(f'  {arc.source} -> {arc.target};')
    
    lines.append('}')
    path.write_text('\n'.join(lines))

def generate_lola(net: WFNet, path: Path):
    lines = [f'// {net.name}', '', 'PLACE',
             '  ' + ', '.join(p.id for p in net.places) + ';', '', 'MARKING']
    
    marked = [f'{p.id}: {p.tokens}' for p in net.places if p.tokens > 0]
    lines.append('  ' + (', '.join(marked) if marked else 'p0: 1') + ';')
    lines.append('')
    
    for t in net.transitions:
        lines.append(f'TRANSITION {t.id}  // {t.label}')
        ins = [f'{a.source}: 1' for a in net.arcs if a.target == t.id]
        outs = [f'{a.target}: 1' for a in net.arcs if a.source == t.id]
        if ins:
            lines.append('  CONSUME ' + ', '.join(ins) + ';')
        if outs:
            lines.append('  PRODUCE ' + ', '.join(outs) + ';')
        lines.append('')
    
    path.write_text('\n'.join(lines))

def main():
    base = Path(__file__).parent
    out = base / "wfnets"
    out.mkdir(exist_ok=True)
    
    print("🔄 Generating PROPER Petri nets...\n")
    results = []
    
    for ip_dir in sorted(base.glob("ip*")):
        if not ip_dir.is_dir():
            continue
        main_go = ip_dir / "main.go"
        if not main_go.exists():
            continue
        
        print(f"📝 {ip_dir.name}...")
        try:
            net = parse_go_file(main_go)
            
            dot_f = out / f"{ip_dir.name}.dot"
            lola_f = out / f"{ip_dir.name}.lola"
            png_f = out / f"{ip_dir.name}.png"
            
            generate_dot(net, dot_f)
            generate_lola(net, lola_f)
            
            try:
                subprocess.run(['dot', '-Tpng', str(dot_f), '-o', str(png_f)],
                             check=True, capture_output=True)
            except:
                pass
            
            print(f"   ✅ {len(net.places)} places, {len(net.transitions)} transitions, {len(net.arcs)} arcs")
            results.append({'name': net.name, 'p': len(net.places), 't': len(net.transitions), 'a': len(net.arcs)})
        except Exception as e:
            print(f"   ❌ {e}")
    
    print(f"\n{'='*70}\n📊 SUMMARY\n{'='*70}")
    print(f"{'Pattern':<35} {'Places':<8} {'Trans':<8} {'Arcs':<8}")
    print('-'*70)
    for r in results:
        print(f"{r['name']:<35} {r['p']:<8} {r['t']:<8} {r['a']:<8}")
    print('='*70)
    print(f"\n✅ Outputs in: {out}/\n")

if __name__ == "__main__":
    main()
