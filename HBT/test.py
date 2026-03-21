import numpy as np
import matplotlib.pyplot as plt
from HBT.interface import MultiHarpWrapper
from HBT.analyser import Analyser
from snAPI.Main import *

ptu_path = r"F:/AMRITA/MultiHarp/QD_Lifetime_30s.ptu"  # <-- change to your file

# sn = snAPI()
# sn.getFileDevice(ptu_path)

# sn.histogram.measure()
# data, bins = sn.histogram.getData()
# print(np.array(bins), np.array(data))
an = Analyser(silent=False, debug=True)
mh = MultiHarpWrapper(silent=False, debug=True)
res = mh.connectFile(ptu_path)
# print("Connect result:", res)

res = mh.measure("histogram")
data, bins = mh.get_data("histogram")
print(bins)
print(data)

# an.get_lifetimes(readoutData=data[1], readoutBins=bins, horizon=1000, nExp=2)
# an.plot_lifetimes(horizon=1000)
# print(mh.sn.measDescription)

syncPeriod = 1/mh.get_sync_rate()
print(mh.sn.measDescription)
print("Sync period:", syncPeriod)
g2 = an.get_g2(readoutData=data, readoutBins=bins, syncPeriod=syncPeriod, normalized=True)

# if multi-channel, pick first detector channel
# if data.ndim == 2:
#     decay = data[1]
# else:
#     decay = data
# bins = np.asarray(bins)
# decay = np.asarray(decay)

# choose how many points to plot (adjust or set to len(bins) to plot all)
# max_plot = len(bins)
# x = bins[:max_plot]
# y = data[:max_plot]

# plt.figure(figsize=(12,5))

# plt.subplot(1,2,1)
# plt.plot(x, y, '-', lw=1)
# plt.xlabel('Bin')
# plt.ylabel('Counts')
# plt.title('Decay (linear)')
# plt.grid(True)

# plt.subplot(1,2,2)
# # avoid plotting zeros on log scale
# y_log = np.where(y > 0, y, np.nan)
# plt.semilogy(x, y_log, '-', lw=1)
# plt.xlabel('Bin')
# plt.title('Decay (semilog)')
# plt.grid(True)

# plt.tight_layout()
# plt.show()


# print(np.shape(bins))
# print(decay)
# an = Analyser(silent=False, debug=False)
# lf = an.get_lifetimes(readoutData=decay, readoutBins=bins, horizon=1000, nExp=2)
# print("Fit success:", lf["success"], lf["message"])
# an.plot_lifetimes(horizon=1000)
# plt.show()