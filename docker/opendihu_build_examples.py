#!/usr/bin/env python3
"""Build opendihu examples and collect their executables in $OPENDIHU_HOME/bin.

Usage: opendihu_build_examples.py LIST_FILE

LIST_FILE names one example directory per line, relative to $OPENDIHU_HOME/examples.
For each directory this runs the release build (the `sr` step from the opendihu
documentation), then moves the resulting executables to $OPENDIHU_HOME/bin and leaves
a symlink behind in build_release, so `./<name>` from the documentation still works.

Several examples build executables with the same name (for example `laplace_hermite`
in laplace1d, laplace2d and laplace3d). Such executables are installed as
`<example>_<name>`; all others keep their name. $OPENDIHU_HOME/bin/INDEX.txt lists
every installed command, the example it belongs to, and the examples that failed.

Environment:
  OPENDIHU_HOME        opendihu source directory (required)
  OPENDIHU_BUILD_JOBS  parallel compile jobs per example (default 4)

A failing example does not stop the run; it is reported at the end. The script exits
with an error only if the opendihu core library is missing or nothing was installed.
"""
import collections
import os
import shutil
import subprocess
import sys
import time

ELF_MAGIC = b"\x7fELF"
NOT_PROGRAMS = (".o", ".os", ".a", ".so")


def read_list(path):
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip().strip("/")
            if line and line not in examples:
                examples.append(line)
    return examples


def is_program(path):
    if os.path.islink(path) or not os.path.isfile(path) or not os.access(path, os.X_OK):
        return False
    name = os.path.basename(path)
    if name.endswith(NOT_PROGRAMS) or ".so." in name:
        return False
    with open(path, "rb") as f:
        return f.read(4) == ELF_MAGIC


def find_programs(build_dir):
    found = []
    for root, _dirs, files in os.walk(build_dir):
        for name in files:
            path = os.path.join(root, name)
            if is_program(path):
                found.append(path)
    return sorted(found)


def remove_objects(build_dir):
    for root, _dirs, files in os.walk(build_dir):
        for name in files:
            if name.endswith((".o", ".os")):
                os.remove(os.path.join(root, name))


def unique_prefixes(examples):
    """Shortest trailing part of each example path that tells the given examples apart."""
    prefixes = {}
    for example in examples:
        parts = example.split("/")
        for n in range(1, len(parts) + 1):
            tail = parts[-n:]
            others = [e for e in examples if e != example and e.split("/")[-n:] == tail]
            if not others:
                break
        prefixes[example] = "_".join(tail)
    return prefixes


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    home = os.environ.get("OPENDIHU_HOME")
    if not home or not os.path.isdir(home):
        sys.exit("error: OPENDIHU_HOME is not set to an existing directory")
    jobs = os.environ.get("OPENDIHU_BUILD_JOBS", "4")
    scons = os.path.join(home, "dependencies", "scons", "scons.py")
    core = os.path.join(home, "core", "build_release", "libopendihu.a")
    if not os.path.isfile(core):
        sys.exit("error: %s does not exist; the opendihu core build failed, so no example can be built" % core)

    examples = read_list(sys.argv[1])
    bin_dir = os.path.join(home, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    built = []  # (example, path of executable)
    status = {}  # example -> text for the report
    for number, example in enumerate(examples, 1):
        directory = os.path.join(home, "examples", example)
        print("\n===== [%d/%d] %s =====" % (number, len(examples), example), flush=True)
        if not os.path.isfile(os.path.join(directory, "SConstruct")):
            status[example] = "FAILED: no SConstruct in %s" % directory
            print(status[example], flush=True)
            continue
        start = time.time()
        # -k keeps building the other executables of an example when one of them fails
        result = subprocess.run(
            [sys.executable, scons, "BUILD_TYPE=release", "-k", "-j", jobs], cwd=directory
        )
        minutes = (time.time() - start) / 60
        build_dir = os.path.join(directory, "build_release")
        programs = find_programs(build_dir) if os.path.isdir(build_dir) else []
        if os.path.isdir(build_dir):
            remove_objects(build_dir)
        built.extend((example, p) for p in programs)
        if result.returncode == 0 and programs:
            status[example] = "ok: %d executable(s), %.1f min" % (len(programs), minutes)
        elif programs:
            status[example] = "PARTIAL: build reported errors, %d executable(s) built, %.1f min" % (
                len(programs),
                minutes,
            )
        else:
            status[example] = "FAILED: no executable built (scons exit code %d), %.1f min" % (
                result.returncode,
                minutes,
            )
        print(status[example], flush=True)

    # Decide the installed name of every executable.
    owners = collections.defaultdict(list)
    for example, path in built:
        owners[os.path.basename(path)].append(example)
    installed = []  # (command, example, original name)
    for example, path in built:
        name = os.path.basename(path)
        sharing = sorted(set(owners[name]))
        command = name if len(sharing) == 1 else "%s_%s" % (unique_prefixes(sharing)[example], name)
        target = os.path.join(bin_dir, command)
        if os.path.lexists(target):
            # the chosen name is already taken by another executable: use the full example path
            command = "%s_%s" % (example.replace("/", "_"), name)
            target = os.path.join(bin_dir, command)
        if os.path.lexists(target):
            sys.exit("error: two executables would be installed as %s" % target)
        shutil.move(path, target)
        os.symlink(target, path)
        installed.append((command, example, name))

    lines = ["opendihu example executables in %s" % bin_dir, ""]
    width = max([len(c) for c, _e, _n in installed] + [7])
    lines.append("%-*s  %s" % (width, "COMMAND", "EXAMPLE (under $OPENDIHU_HOME/examples)"))
    for command, example, name in sorted(installed):
        note = "" if command == name else "   [built as %s]" % name
        lines.append("%-*s  %s%s" % (width, command, example, note))
    lines += ["", "BUILD STATUS"]
    for example in examples:
        lines.append("%s: %s" % (example, status[example]))
    not_ok = [e for e in examples if not status[e].startswith("ok")]
    lines += ["", "%d of %d examples built completely, %d executables installed." % (
        len(examples) - len(not_ok), len(examples), len(installed))]
    report = "\n".join(lines) + "\n"
    with open(os.path.join(bin_dir, "INDEX.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    print("\n" + report, flush=True)

    if not installed:
        sys.exit("error: no example executable was built")


if __name__ == "__main__":
    main()
