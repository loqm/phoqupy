import numpy as np
import matplotlib.pyplot as plt
from HBT.interface import MultiHarpWrapper
from HBT.analyser import Analyser
from snAPI.Main import *

ptu_path = r"C://Users//LOQM-PC//Documents//default.ptu"
time_window = 20 # in ns

an=Analyser(silent=False, debug=True)
mh = MultiHarpWrapper(silent=False, debug=True)
res = mh.connectFile(ptu_path)
# print("Connect result:", res)

res = mh.measure("correlation")
data, bins = mh.get_data("correlation")
print(bins)
print(data)

syncPeriod = 1/mh.get_sync_rate()
print(mh.sn.measDescription)
print("Sync period:", syncPeriod)
g2 = an.get_g2(readoutData=data, readoutBins=bins, syncPeriod=syncPeriod, normalized=True)

t = time_window * 1E-9
print(t)

for i in range(len(bins)):
    if abs(bins[i])<=t:
        idx = i
        break


max_plot = len(bins)
x = bins[idx:max_plot-idx]
y = data[idx:max_plot-idx]

print(x, y)
plt.figure(figsize=(12,5))

plt.plot(x, y, '-', lw=1)
plt.xlabel('Bin')
plt.ylabel('Counts')
plt.title('Decay (linear)')
plt.grid(True)

plt.show()