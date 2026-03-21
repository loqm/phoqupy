import numpy as np
import matplotlib.pyplot as plt
from HBT.interface import MultiHarpWrapper
from HBT.analyser import Analyser
from snAPI.Main import *

ptu_path = r"C://Users//LOQM-PC//Documents//demo 3.ptu"
channel = 1

an = Analyser(silent=False, debug=True)
mh = MultiHarpWrapper(silent=False, debug=True)
res = mh.connectFile(ptu_path)

res = mh.measure("histogram")
data, bins = mh.get_data("histogram")
print(bins)
print(data)

# Capture the returned fit result when computing lifetimes
fit_result = an.get_lifetimes(readoutData=data[channel], readoutBins=bins, horizon=1000, nExp=2)

# Create the plot and get the figure and axes (DOESN'T show yet)
fig, ax = an.plot_lifetimes(horizon=1000)

if fig is not None and ax is not None:
    # Extract lifetimes from the fit result stored in the analyser
    if an.lifetime_fit and 'lifetimes' in an.lifetime_fit:
        lifetimes = an.lifetime_fit['lifetimes']
        amplitudes = an.lifetime_fit.get('amplitudes', [])
        
        # Format lifetime text
        lines = []
        for i, tau in enumerate(lifetimes):
            amp_text = f", A={amplitudes[i]:.2f}" if i < len(amplitudes) else ""
            if abs(tau) >= 1:
                lines.append(f"τ{i+1} = {tau:.2f} ps{amp_text}")
            else:
                lines.append(f"τ{i+1} = {tau:.3g} ps{amp_text}")
        
        # Add offset if present
        if len(amplitudes) > len(lifetimes):
            lines.append(f"Offset = {amplitudes[-1]:.2f}")
        
        text = "\n".join(lines)
        
        # Calculate number of lines to determine vertical spacing
        num_lines = len(lines)
        # Approximate height per line in axes coordinates (adjust as needed)
        line_height = 0.04
        box_height = num_lines * line_height + 0.06  # Add padding
        
        # Add text annotation to the plot (upper right)
        ax.text(0.98, 0.98, text, transform=ax.transAxes,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(facecolor='white', alpha=0.85, edgecolor='black', boxstyle='round,pad=0.8'),
                fontsize=11, fontfamily='monospace')
        
        # Position legend just below the lifetime box
        legend_y = 0.98 - box_height - 0.02  # Small gap below the box
        ax.legend(loc='upper right', bbox_to_anchor=(1.0, legend_y))
        
        print(f"\nFitted lifetimes: {lifetimes}")
        print(f"Amplitudes: {amplitudes}")
        print(f"Residual norm: {an.lifetime_fit.get('rnorm', 'N/A')}")
    else:
        ax.text(0.02, 0.98, "No lifetime fit available", transform=ax.transAxes,
                verticalalignment='top', horizontalalignment='left',
                bbox=dict(facecolor='yellow', alpha=0.8, edgecolor='red'),
                fontsize=9)
        ax.legend(loc='upper right')

# NOW show the plot with annotations
plt.tight_layout()
plt.show()