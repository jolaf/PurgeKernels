# PurgeKernels
Python3 script to purge obsolete kernels from Ubuntu OS.

It's a well known problem with Ubuntu OS that sometimes old kernel modules
do not get purged when kernel gets updated, and may clutter up for years.

This script provides a controlled way to check which kernel versions are installed,
which can be purged, and, if necessary, performs the purging effectively after an explicut user consent.

Usage:
```bash
$ python3 PurgeKernels.py
```

Note that sometimes even after this script's action some clutter may remain in the system.
To make sure, run:

```bash
$ ls -la /lib/modules /boot
```

Only the currently loaded kernel should be mentioned in both directories.

# PurgePackages
Python3 script to purge obsolete packages from Ubuntu OS.

After Ubuntu gets upgraded to the next release, some packages from old distribution can get stuck,
meaning they're installed but they don't have any repositories associated with them, so they never get updated.

Typically it happens when some `/etc/apt/sources.list.d/` file has its content commented out at upgrade
and is never edited to enable the respective repository back again.

Also it sometimes happens when some package is not present in a newer Ubuntu version,
but is not removed during upgrade.

These "stalled" packages can stay on the system for years, through multiple upgrades,
and they never get updated so may contain known security vulnerabilities and thus pose a threat.

Also, those packages that were created for older versions of Ubuntu may not work properly on a newer one
causing unexpected problems and frustration. And they take up disk space.

This script locates packages not associated with repositories and not having dependencies from them,
and suggests removing them. Actual removal is only performed after an explicut user consent.

Usage:
```bash
$ python3 PurgePackages.py
```
