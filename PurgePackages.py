#!/usr/bin/python3
from itertools import chain
from re import compile as reCompile
from subprocess import Popen, PIPE, STDOUT
from sys import exit as sysExit
from typing import Callable, Dict, List, Optional, Sequence

LIST_PACKAGE_PATTERN = reCompile(r'(?m)^(?P<package>[^/]+)/(?P<date>[^ ]+) (?P<version>[^ ]+) (?P<arch>[^ ]+) (?P<status>\[installed,local\])$')

PURGE_PACKAGE_PATTERN = reCompile(r'(?ms).*The following packages will be REMOVED:\n(?P<packages>(?:  [^\n]*\n)+)')

PACKAGE_PATTERN = reCompile(r'[^\s*]+')

PURGE_EXCLUDE_PATTERN = reCompile(r'Note, selecting|is not installed, so not removed')

def purgeFilter(line: str) -> Optional[str]:
    if line.endswith(' disk space will be freed.\n'):
        return line + 'Do you want to continue? [Y/n] ' # Add the question that gets suppressed by subprocess buffering
    return line

def runProcess(args: Sequence[str], lineFilter: Optional[Callable[[str], Optional[str]]] = None, printOut: bool = True, expectedReturnCode: Optional[int] = 0) -> str:
    print('$', ' '.join(args))
    subProcess = Popen(args, stdout = PIPE, stderr = STDOUT, bufsize = 0)
    if lineFilter:
        output: List[str] = []
        assert subProcess.stdout is not None
        for byteLine in subProcess.stdout:
            line = lineFilter(byteLine.decode())
            if line is None:
                continue
            output.append(line)
            if printOut:
                print(line, end = '', flush = True)
        ret = ''.join(output + ['',])
        (out, err) = subProcess.communicate()
        assert not out, f"Unexpected output: {out.decode()!r}"
    else:
        (out, err) = subProcess.communicate()
        if printOut:
            print(out.decode())
        ret = out.decode()
    assert not err, f"Unexpected error output: {err.decode()!r}"
    if expectedReturnCode is not None and subProcess.returncode != expectedReturnCode:
        raise Exception(f"Unexpected return code {subProcess.returncode}")
    return ret

def main() -> None:
    try:
        print("\n## Checking [installed,local] packages:\n")
        packages: List[str] = []
        for match in LIST_PACKAGE_PATTERN.finditer(runProcess(('sudo', 'apt', 'list', '--installed'), printOut = False)):
            package = match.groupdict()['package']
            assert package
            print(package)
            packages.append(package)
        packages.sort()
        if not packages:
            print("No local installed packages found")
            return
        print("\n## Trying to-reinstall:\n")
        reinstalled: List[str] = []
        for package in packages:
            try:
                out = runProcess(('sudo', 'apt-get', 'install', '--reinstall', package))
                if 'is not possible, it cannot be downloaded' not in out:
                    reinstalled.append(package)
            except Exception:
                pass
        if reinstalled:
            print(f"\n## The following packages were re-installed: {' '.join(reinstalled)}\nPlease re-run the script.\n")
            return
        print("## No packages could be re-installed, checking reverse dependencies:\n")
        dependencies: Dict[str, List[str]] = {}
        for package in packages:
            m = PURGE_PACKAGE_PATTERN.match(runProcess(('sudo', 'apt-get', '-s', 'remove', package), printOut = False))
            if not m:
                raise Exception(f"{package}: Error retrieving dependencies")
            packagesToPurge = PACKAGE_PATTERN.findall(m.groupdict()['packages'])
            try:
                packagesToPurge.remove(package)
            except ValueError:
                pass
            if packagesToPurge:
                packagesToPurge.sort()
                print(f"{package}: {' '.join(packagesToPurge)}")
            dependencies[package] = packagesToPurge
        # Resolve dependencies
        externals = set(chain.from_iterable(dependencies.values())) - set(packages) # External dependencies, not present in the dictionary
        blockers = externals
        if externals:
            print(f"\n## The following external dependencies detected: {' '.join(externals)}")
            while True:
                add = set(p for (p, d) in dependencies.items() if p not in blockers and set(d) & blockers) # Packages that are not blockers but depend on blockers
                if not add:
                    break # All blockers identified
                blockers |= add
            for p in dependencies:
                dependencies[p] = sorted(set(dependencies[p]) & blockers)
            print(f"\n## The following packages depend on external dependencies: {' '.join(sorted(blockers - externals))}")
        else:
            print("\n## No external dependencies found")
        toPurge = tuple(sorted(set(packages) - blockers))
        if not toPurge:
            print("Nothing to remove")
            return
        print("\n## Verifying possible remove:\n")
        m = PURGE_PACKAGE_PATTERN.match(runProcess(('sudo', 'apt-get', '-s', 'remove') + toPurge, printOut = False))
        if not m:
            raise Exception(f"{package}: Error verifying remove")
        verified = tuple(sorted(PACKAGE_PATTERN.findall(m.groupdict()['packages'])))
        if verified != toPurge:
            raise Exception(f"Verification failed: missing: {' '.join(sorted(set(toPurge) - set(verified))) or 'None'}, extra: {' '.join(sorted(set(verified) - set(toPurge))) or None}")
        print("\n## Verified, proceeding with remove:\n")
        runProcess(('sudo', 'apt-get', 'remove') + toPurge, lineFilter = purgeFilter)
        print("\n## Trying to-reinstall removed packages:\n")
        for package in toPurge:
            try:
                print(runProcess(('sudo', 'apt-get', 'install', package)))
            except Exception:
                pass
    except Exception as e:
        print(f"ERROR! {e}")
        sysExit(1)

if __name__ == '__main__':
    main()
