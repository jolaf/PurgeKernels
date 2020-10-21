#!/usr/bin/python3
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
        print("\n## Checking [installed,local] packages...\n")
        packages: List[str] = []
        for match in LIST_PACKAGE_PATTERN.finditer(runProcess(('sudo', 'apt', 'list', '--installed'))):
            package = match.groupdict()['package']
            assert package
            print(package)
            packages.append(package)
        packages.sort()
        if not packages:
            print("No local installed packages found!")
            return
        print("\n## Checking reverse dependencies:\n")
        dependencies: Dict[str, List[str]] = {}
        for package in packages:
            m = PURGE_PACKAGE_PATTERN.match(runProcess(('apt-get', '-s', 'remove', package)))
            if not m:
                print(f"{package}: Error retrieving dependencies")
                continue
            packagesToPurge = PACKAGE_PATTERN.findall(m.groupdict()['packages'])
            packagesToPurge.remove(package)
            if packagesToPurge:
                packagesToPurge.sort()
                print(f"{package}: {' '.join(packagesToPurge)}")
            dependencies[package] = packagesToPurge
        changed = True
        while changed:
            changed = False
            for (package, d) in dependencies.items():
                for p in d[:]:
                    if dependencies.get(p) == []:
                        d.remove(p)
                        changed = True
        print("\n## Can NOT be purged:", ', '.join(f'{p} ({", ".join(d)})' for (p, d) in dependencies.items() if d) or 'None')
        toPurge = tuple(p for (p, d) in dependencies.items() if not d)
        print(f"\n## Can be purged: {' '.join(toPurge) or 'None'}")
        if toPurge:
            runProcess(('sudo', 'apt-get', 'remove') + toPurge, lineFilter = purgeFilter)
    except Exception as e:
        print(f"ERROR! {e}")
        sysExit(1)

if __name__ == '__main__':
    main()
