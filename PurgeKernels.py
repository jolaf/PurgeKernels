#!/usr/bin/python3
from re import compile as reCompile
from subprocess import Popen, PIPE, STDOUT
from sys import exit as sysExit
from typing import Callable, List, Optional, Sequence, Tuple

VERSION_SPLIT_PATTERN = reCompile(r'[.-]')

VERSION_PATTERN_STR = r'(?P<version>\d+\.\d+\.\d+-\d+)(?:-(?P<variation>[a-z]+))?'

KERNEL_PATTERN = reCompile(rf'(?P<line>[a-z][a-z]\s+linux-[a-z]+-(?:[a-z]+-)?{VERSION_PATTERN_STR}\s+.*)')

UNAME_R_PATTERN = reCompile(VERSION_PATTERN_STR)

PURGE_EXCLUDE_PATTERN = reCompile(r'Note, selecting|is not installed, so not removed')

def versionTuple(version: str) -> Tuple[int, ...]:
    return tuple(int(v) for v in VERSION_SPLIT_PATTERN.split(version))

def purgeFilter(line: str) -> Optional[str]:
    if PURGE_EXCLUDE_PATTERN.search(line):
        return None
    if line.endswith(' disk space will be freed.\n'):
        return line + 'Do you want to continue? [Y/n] ' # Add the question that gets suppressed by subprocess buffering
    return line

def runProcess(args: Sequence[str], lineFilter: Optional[Callable[[str], Optional[str]]] = None) -> str:
    print('$', ' '.join(args))
    subProcess = Popen(args, stdout = PIPE, stderr = STDOUT, bufsize = 0)
    if lineFilter:
        output = []
        assert subProcess.stdout is not None
        for byteLine in subProcess.stdout:
            line = lineFilter(byteLine.decode())
            if line is None:
                continue
            output.append(line)
            print(line, end = '', flush = True)
        ret = ''.join(output + ['',])
        (out, err) = subProcess.communicate()
        assert not out, f"Unexpected output: {out.decode()!r}"
    else:
        (out, err) = subProcess.communicate()
        ret = out.decode()
    assert not err, f"Unexpected error output: {err.decode()!r}"
    if subProcess.returncode:
        raise Exception(f"Unexpected return code {subProcess.returncode}")
    return ret

def main() -> None:
    try:
        print("\n## Checking installed kernels...\n")
        kernelList: List[str] = []
        for match in KERNEL_PATTERN.finditer(runProcess(('dpkg', '--list'))):
            print(match.groupdict()['line'])
            kernelList.append(match.groupdict()['version'])
        kernels = tuple(sorted(set(kernelList), key = versionTuple))
        if not kernels:
            raise Exception("No installed kernels found!")
        print(f"\n## Installed kernels: {', '.join(kernels)}\n")
        uname_r = runProcess(('uname', '-r')).strip()
        print(uname_r)
        m = UNAME_R_PATTERN.match(uname_r)
        if not m:
            raise Exception(f"Bad version format: {uname_r}")
        currentVersion = m.groupdict()['version']
        print(f"\n## Current kernel version: {currentVersion}\n")
        try:
            currentVersionIndex = kernels.index(currentVersion)
        except ValueError as e:
            raise Exception("Current kernel seems to be not installed!") from None
        if len(kernels) == 1:
            print("The currently loaded kernel is the ONLY kernel installed, there's nothing to be done.\n")
            return
        if currentVersionIndex == 0: # pylint: disable=compare-to-zero
            print("The currently loaded kernel is the OLDEST, please rerun this script after reboot.\n")
            return
        kernelsToRemove = kernels[:currentVersionIndex]
        assert kernelsToRemove
        print(f"## Going to remove kernels: {', '.join(kernelsToRemove)}; please provide root password to proceed:\n")
        runProcess(('sudo', 'apt-get', 'purge') + tuple(f'linux-*-{kernelVersion}*' for kernelVersion in kernelsToRemove), lineFilter = purgeFilter)
        print("\n## Making sure the boot loader is up to date\n")
        runProcess(('sudo', 'update-grub2'))
        if currentVersionIndex == len(kernels) - 1:
            print("\nThe currently loaded kernel is the LATEST, nothing else has to be done, though reboot is suggested to make sure the system boots normally.\n")
            return
        print("\nThe currently loaded kernel is NOT the latest, please rerun this script after reboot.\n")
    except Exception as e:
        print(f"ERROR! {e}")
        sysExit(1)

if __name__ == '__main__':
    main()
