# LR(0) Parser Generator
 
An interactive command-line tool built as a **Compiler Construction learning platform**. It accepts a user-defined context-free grammar, constructs the full LR(0) automaton, generates ACTION and GOTO tables, detects conflicts, builds parse trees, and exports everything as PNG visualizations.
 
> **Course:** Principles of Compiler Design — Department of Software Engineering  
> **Presented to:** Mr. Kassahun  
> **Authors:** Selahadin Desalegn, Natnahom Asfaw, Nebyu Daniel, Nebiyu Ermiyas, Abenezer Yonathan
 
---
 
## What is LR(0) Parsing?
 
LR(0) is a **bottom-up parsing technique** that scans input left-to-right and traces a rightmost derivation in reverse, using **zero lookahead symbols**.
 
| Property | Detail |
|---|---|
| Scan direction | Left-to-right |
| Derivation | Rightmost (in reverse) |
| Lookahead | 0 symbols |
| Language class | Deterministic context-free languages |
| Basis for | SLR, LALR, and LR(1) parsers |
 
The parser is driven by an **LR(0) automaton** — a finite set of states connected by goto transitions, where each state is a collection of LR(0) items. The ACTION and GOTO tables are derived from this automaton to guide every parsing decision.
 
---
 
## Features
 
- **Interactive grammar input** — enter terminals, non-terminals, and productions at the prompt
- **Automatic grammar augmentation** — adds an `S'` start production internally
- **LR(0) automaton construction** — builds the canonical collection of LR(0) item sets via closure and goto operations
- **ACTION & GOTO table generation** — produces the full parsing tables with color-coded visualizations
- **Conflict detection** — identifies shift/reduce and reduce/reduce conflicts and flags non-LR(0) grammars
- **Parse tree construction** — builds a full parse tree during parsing with both ASCII console output and graphical PNG export
- **Interactive string parsing** — parse any token string and see a step-by-step trace
- **Visual output** — exports PNG files covering tables, state diagram, parse tree, and parsing report
---
 
## Requirements
 
```
Python 3.7+
matplotlib
numpy
pandas
networkx
```
 
Install dependencies:
 
```bash
pip install matplotlib numpy pandas networkx
```
 
---
 
## Usage
 
```bash
python LR_0__parser.py
```
 
The program prompts you interactively through each step:
 
1. **Terminals** — comma-separated (e.g. `id, +, *, (, )`)
2. **Non-terminals** — comma-separated (e.g. `E, T, F`)
3. **Start symbol** — must be one of the declared non-terminals
4. **Productions** — one per line in the format `A -> X Y Z`, with `|` for multiple alternatives. Type `done` when finished.
5. **Strings to parse** — space-separated tokens ending with `$`. Type `q` to quit.
### Example Session
 
```
Enter terminals: id, +, *, (, )
Enter non-terminals: E, T, F
Enter start symbol: E
> E -> E + T | T
> T -> T * F | F
> F -> ( E ) | id
> done
 
Enter a string to parse:
> id + id * id $
```
 
---
 
## Key Algorithms
 
### 1. Closure Computation
 
Expands a set of LR(0) items by adding all productions reachable from the dot position:
 
```python
def closure(items, G, nonterminals):
    I = set(items)
    while changed:
        for (lhs, rhs, dot) in I:
            if dot < len(rhs) and rhs[dot] in nonterminals:
                # add all productions starting with rhs[dot]
    return frozenset(I)
```
 
### 2. Goto Function
 
Moves the dot past a given symbol and applies closure — computes all state transitions.
 
### 3. Canonical Collection
 
Builds every LR(0) state by repeatedly applying goto over all grammar symbols, forming the complete finite automaton.
 
### 4. Table Construction
 
- **ACTION table** — shift/reduce decisions for terminal symbols
- **GOTO table** — state transitions after a reduce, indexed by non-terminals
---
 
## Parse Tree
 
During parsing, each shift and reduce operation builds a parse tree in real time.
 
**Node structure:**
```python
class ParseTreeNode:
    def __init__(self, symbol, children, is_terminal):
        self.symbol = symbol        # Grammar symbol
        self.children = children    # Child nodes
        self.is_terminal = is_terminal
        self.parent = None
```
 
**Build process:**
1. Push a terminal node onto the stack during each **shift**
2. Pop child nodes during each **reduce**
3. Create a new parent node and push it back
### ASCII Console View
 
```
E' (NT)
└── E (NT)
    ├── E (NT)
    │   └── T (NT)
    │       └── F (NT)
    │           └── id (T)
    ├── + (T)
    └── T (NT)
        ├── T (NT)
        │   └── F (NT)
        │       └── id (T)
        ├── * (T)
        └── F (NT)
            └── id (T)
```
 
### Graphical View
 
The parse tree is also rendered as a PNG using **NetworkX** (graph structure) and **Matplotlib** (rendering):
- Green nodes → Non-terminals
- Blue nodes → Terminals
- Directed edges → Parent-child relationships
- Automatic hierarchical layout
---
 
## Conflict Detection
 
LR(0) parsers reduce on **all** lookahead symbols, so many real-world grammars produce conflicts.
 
**Types detected:**
 
| Conflict | Description |
|---|---|
| Shift/Reduce | Parser cannot decide between shifting the next token and reducing by a rule |
| Reduce/Reduce | Two or more rules are eligible for reduction in the same state |
 
When conflicts are found, the tool lists each one with its state, symbol, and competing actions, then notes that the grammar requires SLR or LR(1) for correct parsing.
 
```python
if a in ACTION[i]:
    if ACTION[i][a][0] == "shift":
        conflicts.append(f"Shift/reduce conflict on {a}")
    elif ACTION[i][a][0] == "reduce":
        conflicts.append(f"Reduce/reduce conflict on {a}")
```
 
---
 
## Output Files
 
| File | Description |
|---|---|
| `lr0_action_table.png` | Color-coded ACTION table (green = shift, red = reduce, yellow = accept) |
| `lr0_goto_table.png` | GOTO table for non-terminal transitions |
| `lr0_state_diagram.png` | State transition diagram with item sets |
| `lr0_parse_tree.png` | Graphical parse tree for the last parsed string |
| `lr0_parsing_trace.png` | Step-by-step parsing trace table |
| `lr0_parsing_report.png` | Comprehensive parsing report with statistics |
 
---
 
## Key Functions
 
| Function | Description |
|---|---|
| `get_grammar_input()` | Collects and validates grammar interactively |
| `closure(items, G, nonterminals)` | Computes the closure of a set of LR(0) items |
| `goto(I, X, G, nonterminals)` | Computes the goto set for a state and symbol |
| `build_automaton(...)` | Builds the canonical LR(0) item sets and transitions |
| `build_tables(...)` | Constructs ACTION and GOTO tables; detects conflicts |
| `parse_string(...)` | Simulates the LR(0) parse and builds the parse tree |
| `create_action_table_plot(...)` | Renders the ACTION table as a matplotlib figure |
| `create_goto_table_plot(...)` | Renders the GOTO table as a matplotlib figure |
| `create_state_diagram(...)` | Renders the LR(0) state transition diagram |
| `create_parsing_trace_plot(...)` | Renders the parsing trace as a visual table |
| `create_comprehensive_parsing_report(...)` | Renders a full parsing summary with statistics |
 
---
 
## Notes
 
- The `$` end-of-input marker is added automatically — do not declare it as a terminal
- Input strings must be space-separated and must end with `$`
- The state diagram truncates item labels for readability when states contain many items
- The parsing trace displays up to 15 steps inline; longer traces are summarised with a count
- Symbol validation runs interactively — undeclared symbols in productions prompt you to classify them as terminal or non-terminal
