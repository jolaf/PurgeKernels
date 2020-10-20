# PurgeKernels
Python3 script to purge obsolete kernels from Ubuntu OS.

It's a well known problem with Ubuntu OS that old kernel modules do not get purged when the kernel gets updated, and may clutter up for years.

This script provides a controlled way to check which kernel versions are installed, which can be purged, and, if necessary, perform the purging effectively after a user consent is given.

Usage:
`python3 PurgeKernels.py`

No options are supported and none is needed.

# PurgePackages
Python3 script to purge obsolete packages from Ubuntu OS.

After Ubuntu gets upgraded to the next release, some packages from old distribution can get stuck.
They're installed, but don't have any repositories associated with them, so they never get updated.

These packages can be an unneeded waste of disk space,
they can produce frustration when they don't work as expected on a newer distribution,
or can provide a security gap as new discovered vulnerabilities do not get fixed.

This script locates packages not associated with repositories and not having dependencies from them,
and suggests removing them.

Usage:
`python3 PurgePackages.py`
