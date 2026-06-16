# Interactive LR(0) Parser Generator
from collections import defaultdict, deque
import matplotlib.pyplot as plt
from matplotlib.table import Table
import numpy as np
import pandas as pd

def get_grammar_input():
    """Get grammar input from user interactively."""
    print("=" * 60)
    print("LR(0) PARSER GENERATOR")
    print("=" * 60)
    
    # Get terminals
    terminals_input = input("Enter terminals (comma-separated, e.g., 'c, d, +, *'): ")
    terminals = set([t.strip() for t in terminals_input.split(',')])
    
    # Add end marker
    terminals.add("$")
    
    # Get non-terminals
    nonterminals_input = input("Enter non-terminals (comma-separated, e.g., 'E, T, F'): ")
    nonterminals = set([nt.strip() for nt in nonterminals_input.split(',')])
    
    # Get start symbol
    start = input("Enter start symbol (must be one of the non-terminals): ").strip()
    
    # Validate start symbol
    while start not in nonterminals:
        print(f"Error: '{start}' is not in non-terminals list.")
        start = input("Enter start symbol: ").strip()
    
    # Create augmented grammar with S'
    augmented_start = start + "'"
    nonterminals.add(augmented_start)
    
    # Get productions
    print("\nEnter productions (one per line, format: 'A -> X Y Z')")
    print("Enter 'done' when finished.")
    print("Example: 'E -> E + T | T' (use '|' for multiple RHS)")
    
    G = defaultdict(list)
    
    while True:
        production = input("> ").strip()
        
        if production.lower() == 'done':
            break
        
        if not production:
            continue
        
        # Split by -> and |
        if '->' not in production:
            print("Error: Missing '->'. Use format: 'A -> X Y Z'")
            continue
        
        lhs, rhs_all = production.split('->', 1)
        lhs = lhs.strip()
        
        if lhs not in nonterminals:
            print(f"Warning: '{lhs}' not in non-terminals list. Adding it.")
            nonterminals.add(lhs)
        
        # Split multiple RHS by '|'
        rhs_list = [r.strip() for r in rhs_all.split('|')]
        
        for rhs in rhs_list:
            if not rhs:  # Handle epsilon productions
                rhs_symbols = []
            else:
                rhs_symbols = [s.strip() for s in rhs.split()]
            
            # Validate symbols
            for symbol in rhs_symbols:
                if (symbol not in terminals and 
                    symbol not in nonterminals and 
                    symbol != ''):
                    print(f"Warning: Symbol '{symbol}' not declared as terminal or non-terminal.")
                    # Ask if user wants to add it
                    add = input(f"Add '{symbol}' as (t)erminal or (n)on-terminal? (t/n/skip): ").lower()
                    if add == 't':
                        terminals.add(symbol)
                    elif add == 'n':
                        nonterminals.add(symbol)
                    else:
                        print(f"Skipping symbol '{symbol}'")
                        continue
            
            G[lhs].append(rhs_symbols)
    
    # Add augmented production
    G[augmented_start] = [[start]]
    
    return terminals, nonterminals, augmented_start, G

def closure(items, G, nonterminals):
    """Compute the closure of a set of LR(0) items."""
    changed = True
    I = set(items)
    while changed:
        changed = False
        add = []
        for (lhs, rhs, dot) in I:
            if dot < len(rhs):
                X = rhs[dot]
                if X in nonterminals:
                    for prod in G[X]:
                        it = (X, tuple(prod), 0)
                        if it not in I:
                            add.append(it)
        if add:
            I.update(add)
            changed = True
    return frozenset(I)

def goto(I, X, G, nonterminals):
    """Compute goto(I, X) for LR(0) items."""
    moved = []
    for (lhs, rhs, dot) in I:
        if dot < len(rhs) and rhs[dot] == X:
            moved.append((lhs, rhs, dot + 1))
    if not moved:
        return None
    return closure(moved, G, nonterminals)

def build_automaton(G, START, terminals, nonterminals):
    """Build LR(0) automaton from grammar."""
    # Build canonical collection
    I0 = closure([(START, tuple(G[START][0]), 0)], G, nonterminals)
    states = [I0]
    transitions = {}
    work = deque([I0])
    seen = {I0}
    
    symbols = list(terminals - {"$"}) + list(nonterminals - {START})
    
    while work:
        I = work.popleft()
        for X in symbols:
            J = goto(I, X, G, nonterminals)
            if J and J not in seen:
                seen.add(J)
                states.append(J)
                work.append(J)
            if J:
                transitions[(I, X)] = J
    
    return states, transitions

def build_tables(states, transitions, G, START, terminals, nonterminals):
    """Build ACTION and GOTO tables."""
    # Index states
    index = {st: i for i, st in enumerate(states)}
    
    # Build productions list
    productions = []
    prod_map = {}
    pid = 0
    
    for A, prods in G.items():
        for rhs in prods:
            productions.append((A, tuple(rhs)))
            prod_map[(A, tuple(rhs))] = pid
            pid += 1
    
    # Initialize tables
    ACTION = defaultdict(dict)
    GOTO = defaultdict(dict)
    conflicts = []
    
    for I in states:
        i = index[I]
        
        # Check for reduce items
        reduce_items = []
        for (lhs, rhs, dot) in I:
            if dot == len(rhs):
                if lhs == START:  # Accept
                    if "$" in ACTION[i]:
                        conflicts.append(f"State {i}: Accept conflicts with {ACTION[i]['$']} on $")
                    ACTION[i]["$"] = ("accept",)
                else:
                    reduce_items.append((lhs, rhs))
        
        # Add shift actions
        for a in terminals - {"$"}:
            J = transitions.get((I, a))
            if J:
                if a in ACTION[i]:
                    conflicts.append(f"State {i}: Shift/shift conflict on {a}")
                ACTION[i][a] = ("shift", index[J])
        
        # Add reduce actions
        for lhs, rhs in reduce_items:
            rid = prod_map[(lhs, rhs)]
            # For LR(0), reduce on ALL terminals
            for a in terminals:
                if a in ACTION[i]:
                    if ACTION[i][a][0] == "shift":
                        conflicts.append(f"State {i}: Shift/reduce conflict on {a} (reduce {lhs}->{' '.join(rhs)} vs shift)")
                    elif ACTION[i][a][0] == "reduce" and ACTION[i][a][1] != rid:
                        conflicts.append(f"State {i}: Reduce/reduce conflict on {a} (reduce {lhs}->{' '.join(rhs)} vs reduce {productions[ACTION[i][a][1]][0]}->{' '.join(productions[ACTION[i][a][1]][1])})")
                else:
                    ACTION[i][a] = ("reduce", rid)
        
        # Goto table
        for A in nonterminals - {START}:
            J = transitions.get((I, A))
            if J:
                GOTO[i][A] = index[J]
    
    return index, ACTION, GOTO, productions, prod_map, conflicts

def create_action_table_plot(states, ACTION, terminals, productions):
    """Create a matplotlib figure for ACTION table."""
    # Get sorted terminals (with $ at the end)
    sorted_terms = sorted([t for t in terminals if t != "$"]) + ["$"]
    heads = ["State"] + sorted_terms
    
    # Prepare table data
    table_data = []
    for i in range(len(states)):
        row = [str(i)]
        for sym in sorted_terms:
            action = ACTION[i].get(sym)
            if not action:
                row.append("")
            elif action[0] == "shift":
                row.append(f"s{action[1]}")
            elif action[0] == "reduce":
                A, rhs = productions[action[1]]
                # Shorten long productions for display
                rhs_str = ' '.join(rhs) if rhs else "ε"
                if len(rhs_str) > 10:
                    rhs_str = rhs_str[:8] + "..."
                row.append(f"r{action[1]}")
            elif action[0] == "accept":
                row.append("acc")
        table_data.append(row)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(max(8, len(heads) * 1.5), len(states) * 0.5 + 2))
    ax.axis('tight')
    ax.axis('off')
    
    # Create table
    table = ax.table(cellText=table_data,
                     colLabels=heads,
                     cellLoc='center',
                     loc='center',
                     colColours=['#f0f0f0'] * len(heads))
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # Color code cells
    for i in range(len(table_data) + 1):
        for j in range(len(heads)):
            cell = table[i, j]
            if i == 0:  # Header row
                cell.set_facecolor('#4a6fa5')
                cell.set_text_props(color='white', weight='bold')
                cell.set_edgecolor('white')
            else:
                cell.set_facecolor('#e8e8e8' if i % 2 == 0 else '#f8f8f8')
                cell.set_edgecolor('white')
                
                # Color code action types
                if j > 0:  # Skip state column
                    text = cell.get_text().get_text()
                    if text.startswith('s'):
                        cell.set_facecolor('#d4edda')  # Green for shift
                    elif text.startswith('r'):
                        cell.set_facecolor('#f8d7da')  # Red for reduce
                    elif text == 'acc':
                        cell.set_facecolor('#fff3cd')  # Yellow for accept
    
    plt.title('LR(0) ACTION Table', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    return fig

def create_goto_table_plot(states, GOTO, nonterminals, START):
    """Create a matplotlib figure for GOTO table."""
    sorted_nt = sorted([nt for nt in nonterminals if nt != START])
    
    if not sorted_nt:
        # Create empty figure if no goto entries
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.axis('off')
        ax.text(0.5, 0.5, "No GOTO entries (no non-terminals besides start)", 
                ha='center', va='center', fontsize=12)
        plt.title('GOTO Table', fontsize=14, fontweight='bold')
        return fig
    
    heads = ["State"] + sorted_nt
    
    # Prepare table data
    table_data = []
    for i in range(len(states)):
        row = [str(i)]
        for nt in sorted_nt:
            goto_val = GOTO[i].get(nt)
            row.append(str(goto_val) if goto_val is not None else "")
        table_data.append(row)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(max(6, len(heads) * 1.2), len(states) * 0.5 + 2))
    ax.axis('tight')
    ax.axis('off')
    
    # Create table
    table = ax.table(cellText=table_data,
                     colLabels=heads,
                     cellLoc='center',
                     loc='center',
                     colColours=['#f0f0f0'] * len(heads))
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # Color code cells
    for i in range(len(table_data) + 1):
        for j in range(len(heads)):
            cell = table[i, j]
            if i == 0:  # Header row
                cell.set_facecolor('#6c757d')
                cell.set_text_props(color='white', weight='bold')
                cell.set_edgecolor('white')
            else:
                cell.set_facecolor('#e8e8e8' if i % 2 == 0 else '#f8f8f8')
                cell.set_edgecolor('white')
                
                # Highlight non-empty goto entries
                if j > 0:  # Skip state column
                    text = cell.get_text().get_text()
                    if text and text.strip():
                        cell.set_facecolor('#d1ecf1')  # Light blue for goto entries
    
    plt.title('LR(0) GOTO Table', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    return fig

def create_state_diagram(states, transitions, index):
    """Create a visualization of LR(0) states and transitions."""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.axis('off')
    
    # Calculate positions for states in a grid
    n_states = len(states)
    n_cols = min(4, max(2, int(np.sqrt(n_states * 1.5))))
    n_rows = (n_states + n_cols - 1) // n_cols
    
    positions = {}
    for i in range(n_states):
        row = i // n_cols
        col = i % n_cols
        positions[i] = (col * 5, -row * 4)
    
    # Draw states
    for state_idx, (x, y) in positions.items():
        # Draw state circle
        circle = plt.Circle((x, y), 1.0, fill=True, color='white', 
                           edgecolor='black', linewidth=2, zorder=2)
        ax.add_patch(circle)
        
        # Add state number
        ax.text(x, y, f"I{state_idx}", ha='center', va='center', 
                fontsize=12, fontweight='bold', zorder=3)
        
        # Add state items (limited for clarity)
        items = list(states[state_idx])
        max_items = 4
        if len(items) > max_items:
            display_items = items[:max_items]
            extra_count = len(items) - max_items
        else:
            display_items = items
            extra_count = 0
        
        # Add items as text below state
        item_texts = []
        for lhs, rhs, dot in display_items:
            rhs_list = list(rhs)
            rhs_list.insert(dot, "•")
            rhs_str = ' '.join(rhs_list) if rhs_list else "•"
            item_text = f"{lhs} → {rhs_str}"
            if len(item_text) > 15:
                item_text = item_text[:13] + "..."
            item_texts.append(item_text)
        
        if extra_count > 0:
            item_texts.append(f"... +{extra_count}")
        
        # Position item text
        for j, text in enumerate(item_texts):
            y_offset = -1.5 - j * 0.5
            ax.text(x, y + y_offset, text, ha='center', va='top', 
                   fontsize=6, fontstyle='italic')
    
    # Draw transitions
    arrow_styles = {}
    style_counter = 0
    
    for (I, X), J in transitions.items():
        i = index[I]
        j = index[J]
        
        # Skip self transitions for clarity
        if i == j:
            continue
            
        x1, y1 = positions[i]
        x2, y2 = positions[j]
        
        # Calculate direction vector
        dx = x2 - x1
        dy = y2 - y1
        dist = np.sqrt(dx*dx + dy*dy)
        
        if dist > 0:
            # Normalize
            dx /= dist
            dy /= dist
            
            # Start and end points (edge of circles)
            start_x = x1 + dx * 1.0
            start_y = y1 + dy * 1.0
            end_x = x2 - dx * 1.0
            end_y = y2 - dy * 1.0
            
            # Choose arrow style based on X type
            if X.isupper() or "'" in X:  # Non-terminal
                color = 'darkgreen'
                style = '-'
            else:  # Terminal
                color = 'darkblue'
                style = '--'
            
            # Draw arrow
            ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                       arrowprops=dict(arrowstyle='->', color=color, 
                                      linestyle=style, linewidth=1.5, alpha=0.7))
            
            # Add transition label
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            
            # Offset label perpendicular to arrow
            offset = 0.4
            label_x = mid_x - dy * offset
            label_y = mid_y + dx * offset
            
            ax.text(label_x, label_y, str(X), ha='center', va='center',
                   fontsize=8, fontweight='bold', color=color,
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='lightyellow', 
                           alpha=0.8, edgecolor=color), zorder=4)
    
    # Set limits with padding
    all_x = [pos[0] for pos in positions.values()]
    all_y = [pos[1] for pos in positions.values()]
    ax.set_xlim(min(all_x) - 2, max(all_x) + 2)
    ax.set_ylim(min(all_y) - 2, max(all_y) + 2)
    
    plt.title('LR(0) State Diagram', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    return fig

def create_parsing_trace_plot(trace_data, success):
    """Create a visual trace table for parsing steps."""
    if not trace_data:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.axis('off')
        ax.text(0.5, 0.5, "No trace data available", 
                ha='center', va='center', fontsize=14)
        plt.title('Parsing Trace', fontsize=16, fontweight='bold')
        return fig
    
    # Prepare table data
    headers = ["Step", "Stack", "Input", "Action", "Explanation"]
    table_data = []
    
    for i, step_data in enumerate(trace_data):
        if isinstance(step_data, str):
            # Old format string
            table_data.append([str(i+1), "-", "-", "-", step_data])
        else:
            # New format dictionary
            table_data.append([
                str(step_data['step']),
                step_data['stack'],
                step_data['input'],
                step_data['action'],
                step_data['explanation']
            ])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, max(6, len(table_data) * 0.5)))
    ax.axis('tight')
    ax.axis('off')
    
    # Create table
    table = ax.table(cellText=table_data,
                     colLabels=headers,
                     cellLoc='left',
                     loc='center',
                     colWidths=[0.05, 0.3, 0.2, 0.2, 0.25])
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.2)
    
    # Color code rows based on action type
    for i in range(len(table_data) + 1):
        for j in range(len(headers)):
            cell = table[i, j]
            if i == 0:  # Header row
                cell.set_facecolor('#2c3e50')
                cell.set_text_props(color='white', weight='bold')
                cell.set_edgecolor('white')
            else:
                # Get action from the row
                action = table_data[i-1][3].lower()
                explanation = table_data[i-1][4].lower()
                
                # Set background based on action
                if 'shift' in action:
                    cell.set_facecolor('#d4edda')  # Green for shift
                elif 'reduce' in action:
                    cell.set_facecolor('#f8d7da')  # Red for reduce
                elif 'accept' in action or 'accepted' in explanation:
                    cell.set_facecolor('#fff3cd')  # Yellow for accept
                    if i == len(table_data):  # Last row if accepted
                        for k in range(len(headers)):
                            table[i, k].set_facecolor('#d4edda' if success else '#f8d7da')
                elif 'error' in explanation or 'reject' in explanation:
                    cell.set_facecolor('#f5c6cb')  # Darker red for error
                else:
                    cell.set_facecolor('#e8e8e8' if i % 2 == 0 else '#f8f8f8')
                
                cell.set_edgecolor('white')
    
    # Add result box
    result_color = 'green' if success else 'red'
    result_text = '✓ PARSING SUCCESSFUL' if success else '✗ PARSING FAILED'
    
    # Position result box at top
    ax.text(0.5, 0.98, result_text, 
            ha='center', va='top', fontsize=14, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=result_color, 
                     alpha=0.3, edgecolor=result_color),
            transform=ax.transAxes)
    
    plt.title('LR(0) Parsing Trace', fontsize=16, fontweight='bold', pad=30)
    plt.tight_layout()
    return fig

def print_grammar_summary(G, terminals, nonterminals, START):
    """Print a summary of the grammar."""
    print("\n" + "=" * 60)
    print("GRAMMAR SUMMARY")
    print("=" * 60)
    
    print(f"Start Symbol: {START}")
    print(f"Non-terminals: {', '.join(sorted(nonterminals))}")
    print(f"Terminals: {', '.join(sorted([t for t in terminals if t != '$']))}")
    
    print("\nProductions:")
    for lhs in sorted(G.keys()):
        for rhs in G[lhs]:
            rhs_str = ' '.join(rhs) if rhs else "ε"
            print(f"  {lhs:3} → {rhs_str}")

def parse_string(ACTION, GOTO, productions, tokens, verbose=True):
    """Parse a string using the LR(0) tables and return detailed trace data."""
    stack = [0]
    ip = 0
    trace_data = []
    step_counter = 0
    
    # Ensure $ at end
    if tokens[-1] != "$":
        tokens = tokens + ["$"]
    
    # Store input for display
    input_str = ' '.join(tokens)
    
    while True:
        s = stack[-1]
        a = tokens[ip] if ip < len(tokens) else "$"
        
        step_counter += 1
        current_stack = ' '.join([str(x) for x in stack])
        remaining_input = ' '.join(tokens[ip:])
        
        # Default values
        action_str = ""
        explanation = ""
        
        action = ACTION[s].get(a)
        
        if not action:
            action_str = "ERROR"
            explanation = f"No action for state {s} on symbol '{a}'"
            expected = [sym for sym in ACTION[s].keys() if ACTION[s][sym][0] != 'reduce' or sym == a]
            explanation += f". Expected: {expected}"
            trace_data.append({
                'step': step_counter,
                'stack': current_stack,
                'input': remaining_input,
                'action': action_str,
                'explanation': explanation
            })
            return False, trace_data
        
        if action[0] == "shift":
            action_str = f"shift {action[1]}"
            explanation = f"Shift '{a}', push onto stack, goto state {action[1]}"
            
            trace_data.append({
                'step': step_counter,
                'stack': current_stack,
                'input': remaining_input,
                'action': action_str,
                'explanation': explanation
            })
            
            stack.extend([a, action[1]])
            ip += 1
        
        elif action[0] == "reduce":
            A, rhs = productions[action[1]]
            k = 2 * len(rhs)
            
            # Check stack has enough items
            if len(stack) < k:
                action_str = "ERROR"
                explanation = f"Stack underflow during reduce {A} → {' '.join(rhs) if rhs else 'ε'}"
                trace_data.append({
                    'step': step_counter,
                    'stack': current_stack,
                    'input': remaining_input,
                    'action': action_str,
                    'explanation': explanation
                })
                return False, trace_data
            
            action_str = f"reduce {action[1]}"
            rhs_str = ' '.join(rhs) if rhs else 'ε'
            explanation = f"Reduce using {A} → {rhs_str}"
            
            trace_data.append({
                'step': step_counter,
                'stack': current_stack,
                'input': remaining_input,
                'action': action_str,
                'explanation': explanation
            })
            
            # Pop 2*k symbols (state-symbol pairs)
            for _ in range(k):
                stack.pop()
            
            t = stack[-1]
            
            # Push nonterminal
            stack.append(A)
            
            # Get goto state
            goto_state = GOTO[t].get(A)
            if goto_state is None:
                action_str = "ERROR"
                explanation = f"No goto for state {t} on {A} after reduce"
                trace_data.append({
                    'step': step_counter + 1,
                    'stack': ' '.join([str(x) for x in stack]),
                    'input': remaining_input,
                    'action': action_str,
                    'explanation': explanation
                })
                return False, trace_data
            
            stack.append(goto_state)
            
            # Add goto step
            step_counter += 1
            action_str = f"goto {goto_state}"
            explanation = f"Goto state {goto_state} on {A}"
            
            trace_data.append({
                'step': step_counter,
                'stack': ' '.join([str(x) for x in stack]),
                'input': remaining_input,
                'action': action_str,
                'explanation': explanation
            })
        
        elif action[0] == "accept":
            action_str = "accept"
            explanation = "Input successfully parsed!"
            
            trace_data.append({
                'step': step_counter,
                'stack': current_stack,
                'input': remaining_input,
                'action': action_str,
                'explanation': explanation
            })
            
            return True, trace_data
    
    return False, trace_data

def create_comprehensive_parsing_report(trace_data, success, input_string):
    """Create a comprehensive parsing report with statistics."""
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.axis('off')
    
    # Title
    ax.text(0.5, 0.97, 'LR(0) PARSING REPORT', 
            ha='center', va='top', fontsize=18, fontweight='bold',
            transform=ax.transAxes)
    
    # Input string
    ax.text(0.5, 0.93, f'Input: {input_string}', 
            ha='center', va='top', fontsize=14, 
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.3),
            transform=ax.transAxes)
    
    # Result box
    result_color = 'green' if success else 'red'
    result_text = '✓ ACCEPTED' if success else '✗ REJECTED'
    ax.text(0.5, 0.88, result_text, 
            ha='center', va='top', fontsize=16, fontweight='bold', color=result_color,
            bbox=dict(boxstyle='round,pad=0.5', facecolor=result_color, alpha=0.2),
            transform=ax.transAxes)
    
    # Statistics
    stats_y = 0.82
    stats_text = []
    
    if trace_data:
        total_steps = len(trace_data)
        shift_count = sum(1 for step in trace_data if 'shift' in step['action'].lower())
        reduce_count = sum(1 for step in trace_data if 'reduce' in step['action'].lower())
        goto_count = sum(1 for step in trace_data if 'goto' in step['action'].lower())
        
        stats_text.append(f"Total Steps: {total_steps}")
        stats_text.append(f"Shift Operations: {shift_count}")
        stats_text.append(f"Reduce Operations: {reduce_count}")
        stats_text.append(f"Goto Operations: {goto_count}")
        
        # Find final stack state
        final_step = trace_data[-1]
        stats_text.append(f"Final Stack: {final_step['stack']}")
    
    for i, stat in enumerate(stats_text):
        ax.text(0.1, stats_y - i*0.04, stat, 
                ha='left', va='top', fontsize=11,
                transform=ax.transAxes)
    
    # Trace table (if trace data exists)
    if trace_data and len(trace_data) <= 20:  # Show full trace if 20 steps or less
        # Create a table
        trace_y = 0.65
        cell_height = 0.04
        headers = ["Step", "Stack", "Input", "Action"]
        
        # Draw header
        for j, header in enumerate(headers):
            ax.text(0.1 + j*0.25, trace_y, header, 
                    ha='left', va='top', fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='gray', alpha=0.3),
                    transform=ax.transAxes)
        
        # Draw rows
        for i, step in enumerate(trace_data[:15]):  # Show first 15 steps
            row_y = trace_y - (i+1)*cell_height
            cols = [
                str(step['step']),
                step['stack'][:30] + "..." if len(step['stack']) > 30 else step['stack'],
                step['input'][:20] + "..." if len(step['input']) > 20 else step['input'],
                step['action']
            ]
            
            # Color row based on action
            if 'shift' in step['action'].lower():
                row_color = '#d4edda'
            elif 'reduce' in step['action'].lower():
                row_color = '#f8d7da'
            elif 'goto' in step['action'].lower():
                row_color = '#d1ecf1'
            elif 'accept' in step['action'].lower():
                row_color = '#fff3cd'
            else:
                row_color = '#f8f9fa' if i % 2 == 0 else '#e9ecef'
            
            for j, cell in enumerate(cols):
                ax.text(0.1 + j*0.25, row_y, cell, 
                        ha='left', va='top', fontsize=8,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor=row_color, alpha=0.7),
                        transform=ax.transAxes)
        
        if len(trace_data) > 15:
            ax.text(0.5, row_y - cell_height, f"... and {len(trace_data)-15} more steps", 
                    ha='center', va='top', fontsize=9, fontstyle='italic',
                    transform=ax.transAxes)
    
    elif trace_data:
        # Too many steps, show summary
        ax.text(0.5, 0.5, f"Trace has {len(trace_data)} steps (too many to display)\n"
                         "See the separate trace table for details.", 
                ha='center', va='center', fontsize=12,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.3),
                transform=ax.transAxes)
    
    # Footer
    ax.text(0.5, 0.02, 'LR(0) Parser Generator - Interactive Compiler Construction Tool', 
            ha='center', va='bottom', fontsize=9, fontstyle='italic',
            transform=ax.transAxes)
    
    plt.tight_layout()
    return fig

def main():
    """Main interactive LR(0) parser generator."""
    # Get grammar from user
    terminals, nonterminals, START, G = get_grammar_input()
    
    # Print grammar summary
    print_grammar_summary(G, terminals, nonterminals, START)
    
    # Build LR(0) automaton
    print("\nBuilding LR(0) automaton...")
    states, transitions = build_automaton(G, START, terminals, nonterminals)
    
    # Build parsing tables
    index, ACTION, GOTO, productions, prod_map, conflicts = build_tables(
        states, transitions, G, START, terminals, nonterminals
    )
    
    # Print states
    print(f"\nGenerated {len(states)} LR(0) states.")
    
    # Show conflicts
    if conflicts:
        print("\n" + "!" * 60)
        print(f"Found {len(conflicts)} CONFLICT(S):")
        for conflict in conflicts:
            print(f"  {conflict}")
        print("!" * 60)
        print("Note: This grammar is NOT LR(0) due to conflicts.")
        print("It requires lookahead (SLR/LR(1)) for correct parsing.")
    else:
        print("\nNo conflicts found. Grammar appears to be LR(0).")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    
    # Create tables
    action_fig = create_action_table_plot(states, ACTION, terminals, productions)
    goto_fig = create_goto_table_plot(states, GOTO, nonterminals, START)
    state_fig = create_state_diagram(states, transitions, index)
    
    # Save figures
    action_fig.savefig('lr0_action_table.png', dpi=150, bbox_inches='tight')
    goto_fig.savefig('lr0_goto_table.png', dpi=150, bbox_inches='tight')
    state_fig.savefig('lr0_state_diagram.png', dpi=150, bbox_inches='tight')
    
    print("✓ ACTION table saved as 'lr0_action_table.png'")
    print("✓ GOTO table saved as 'lr0_goto_table.png'")
    print("✓ State diagram saved as 'lr0_state_diagram.png'")
    
    # Interactive parsing loop
    print("\n" + "=" * 60)
    print("INTERACTIVE PARSING")
    print("=" * 60)
    
    while True:
        print("\nEnter a string to parse (space-separated tokens, 'q' to quit):")
        print("Example: 'c d d $' or 'id + id * id $'")
        
        user_input = input("> ").strip()
        
        if user_input.lower() in ['q', 'quit', 'exit']:
            break
        
        if not user_input:
            continue
        
        # Tokenize input
        tokens = [t.strip() for t in user_input.split()]
        
        # Parse
        success, trace_data = parse_string(ACTION, GOTO, productions, tokens, verbose=True)
        
        print("\n" + "-" * 80)
        print("PARSING TRACE TABLE:")
        print("-" * 80)
        print(f"{'Step':<5} {'Stack':<40} {'Input':<30} {'Action':<20} {'Explanation'}")
        print("-" * 80)
        
        for step in trace_data:
            print(f"{step['step']:<5} {step['stack'][:38]:<40} {step['input'][:28]:<30} "
                  f"{step['action'][:18]:<20} {step['explanation']}")
        
        print("-" * 80)
        
        if success:
            print("\n✓ String is ACCEPTED by the grammar")
        else:
            print("\n✗ String is REJECTED or parse error")
        
        # Create visual trace
        trace_fig = create_parsing_trace_plot(trace_data, success)
        trace_fig.savefig('lr0_parsing_trace.png', dpi=150, bbox_inches='tight')
        
        # Create comprehensive report
        report_fig = create_comprehensive_parsing_report(trace_data, success, ' '.join(tokens))
        report_fig.savefig('lr0_parsing_report.png', dpi=150, bbox_inches='tight')
        
        print("\n✓ Parsing trace saved as 'lr0_parsing_trace.png'")
        print("✓ Parsing report saved as 'lr0_parsing_report.png'")
        
        # Ask if user wants to display visualizations
        show_viz = input("\nDisplay visualizations? (y/n): ").lower()
        if show_viz == 'y':
            plt.show()
        
        # Clear figures to avoid memory issues
        plt.close('all')
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Grammar analyzed with {len(states)} LR(0) states.")
    print(f"Found {len(conflicts)} conflicts.")
    print("\nFiles created for your grammar:")
    print("  1. lr0_action_table.png - ACTION table")
    print("  2. lr0_goto_table.png - GOTO table")
    print("  3. lr0_state_diagram.png - State transition diagram")
    print("  4. lr0_parsing_trace.png - Parsing trace table")
    print("  5. lr0_parsing_report.png - Comprehensive parsing report")
    print("\nThank you for using the LR(0) Parser Generator!")

if __name__ == "__main__":
    print("Welcome to the Interactive LR(0) Parser Generator with Visual Trace!")
    print("\nKey Features:")
    print("  • Interactive grammar input")
    print("  • LR(0) automaton construction")
    print("  • Conflict detection")
    print("  • Visual parsing trace tables")
    print("  • Comprehensive parsing reports")
    print("  • Export all results as PNG images")
    
    main()