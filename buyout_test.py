import matplotlib.pyplot as plt
import numpy as np

salaries = np.arange(6e5, 6e6, 1e5)
buyout_old = salaries*(0.5 + 0.25*(salaries > 2.5e6))
buyout_new = salaries*0.75 - 3e5

fig, ax = plt.subplots(ncols=2)
ax[0].plot(salaries, buyout_old)
ax[0].plot(salaries, buyout_new)
ax[1].plot(salaries, buyout_old/salaries)
ax[1].plot(salaries, buyout_new/salaries)

plt.show()
