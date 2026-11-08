"""Unprivileged Linux isolation for a pure ``solve(data)`` worker.

Landlock restricts reads to the public project and Python runtime. If unavailable,
a public source snapshot is imported from memory and seccomp denies all file
opens. Both modes deny networking, process creation and privileged interfaces.
No Python source restrictions are used. Restrictions apply equally to ctypes.
"""
import ctypes
import ast
import errno
import importlib
import importlib.util
import os
from pathlib import Path
import platform
import sys
import sysconfig


class SandboxUnavailable(RuntimeError):
    pass


class Ruleset(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


READ_FILE = 1 << 2
READ_DIR = 1 << 3
EXECUTE = 1
PR_SET_NO_NEW_PRIVS = 38


def _fail(libc, operation):
    number = ctypes.get_errno()
    raise SandboxUnavailable(f"{operation}: {os.strerror(number)} (errno {number})")


def _landlock(libc, public_project, runtime_files):
    # These syscall numbers are shared by the supported 64-bit architectures.
    if platform.machine() not in {"x86_64", "aarch64", "riscv64"}:
        raise SandboxUnavailable("Landlock syscall numbers unsupported on this architecture")
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 1:
        _fail(libc, "Landlock unavailable")
    handled = (1 << 13) - 1
    if abi >= 2:
        handled |= 1 << 13  # REFER: link/rename between directories
    if abi >= 3:
        handled |= 1 << 14  # TRUNCATE
    if abi >= 5:
        handled |= 1 << 15  # IOCTL_DEV
    attr = Ruleset(handled)
    ruleset = libc.syscall(444, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if ruleset < 0:
        _fail(libc, "Landlock create_ruleset")
    try:
        paths = [Path(public_project).resolve()]
        paths += [Path(p).resolve() for p in ("/usr", "/lib", "/lib64") if Path(p).exists()]
        # Conda and other non-system runtimes keep stdlib outside /usr.
        # Grant only the interpreter's library directories, never its home
        # directory or prefix. All paths remain read-only under Landlock.
        for key in ("stdlib", "platstdlib"):
            library = sysconfig.get_path(key)
            if library and Path(library).is_dir():
                paths.append(Path(library).resolve())
        paths += [Path(p).resolve() for p in runtime_files]
        for path in dict.fromkeys(paths):
            descriptor = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                access = READ_FILE | EXECUTE
                if path.is_dir():
                    access |= READ_DIR
                rule = PathBeneath(access, descriptor)
                if libc.syscall(445, ruleset, 1, ctypes.byref(rule), 0) < 0:
                    _fail(libc, "Landlock add_rule")
            finally:
                os.close(descriptor)
        if libc.syscall(446, ruleset, 0) < 0:
            _fail(libc, "Landlock restrict_self")
    finally:
        os.close(ruleset)


def _seccomp_library():
    # Load before Landlock so the dynamic loader does not need /etc/ld.so.cache.
    for name in ("libseccomp.so.2", "/lib/x86_64-linux-gnu/libseccomp.so.2",
                 "/lib/aarch64-linux-gnu/libseccomp.so.2"):
        try:
            lib = ctypes.CDLL(name, use_errno=True)
            break
        except OSError:
            continue
    else:
        raise SandboxUnavailable("libseccomp is unavailable")
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_rule_add.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    return lib


def _seccomp(lib, filesystem_closed=False):
    context = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise SandboxUnavailable("seccomp_init failed")
    # A pure function needs no sockets, children, tracing, IPC, mounts or handles.
    denied = """
        socket socketpair socketcall connect bind listen accept accept4
        sendto sendmsg sendmmsg recvfrom recvmsg recvmmsg shutdown
        fork vfork clone clone3 execve execveat ptrace prctl
        process_vm_readv process_vm_writev pidfd_open pidfd_getfd pidfd_send_signal
        kill tkill tgkill rt_sigqueueinfo rt_tgsigqueueinfo
        mount umount umount2 pivot_root chroot move_mount open_tree fsopen
        fsconfig fsmount fspick mount_setattr unshare setns
        open_by_handle_at name_to_handle_at
        io_uring_setup io_uring_enter io_uring_register
        bpf perf_event_open userfaultfd
        fanotify_init fanotify_mark inotify_init inotify_init1 inotify_add_watch
        lookup_dcookie uselib kcmp
        keyctl add_key request_key
        shmget shmat shmdt shmctl semget semop semtimedop semctl msgget msgsnd msgrcv msgctl
        reboot kexec_load kexec_file_load init_module finit_module delete_module
        swapon swapoff iopl ioperm acct quotactl
        setuid setgid setreuid setregid setresuid setresgid setfsuid setfsgid setgroups
        capset sethostname setdomainname settimeofday clock_settime adjtimex clock_adjtime
        chmod fchmod fchmodat fchmodat2 chown fchown lchown fchownat
        setxattr lsetxattr fsetxattr removexattr lremovexattr fremovexattr
        truncate ftruncate fallocate utime utimes futimesat utimensat
        ioctl
    """.split()
    if filesystem_closed:
        denied += """
            open openat openat2 creat memfd_create
            access faccessat faccessat2 stat lstat newfstatat statx
            readlink readlinkat getdents getdents64
            getxattr lgetxattr fgetxattr listxattr llistxattr flistxattr
            statfs statfs64 fstatfs fstatfs64
            chdir fchdir mkdir mkdirat rmdir unlink unlinkat
            rename renameat renameat2 link linkat symlink symlinkat
            mknod mknodat
        """.split()
    try:
        for name in denied:
            number = lib.seccomp_syscall_resolve_name(name.encode())
            # Missing syscalls on this architecture cannot be invoked there.
            if number == -1:
                continue
            result = lib.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0)
            if result < 0:
                raise SandboxUnavailable(f"seccomp rule {name}: {os.strerror(-result)}")
        result = lib.seccomp_load(context)
        if result < 0:
            raise SandboxUnavailable(f"seccomp load: {os.strerror(-result)}")
    finally:
        lib.seccomp_release(context)


class PublicMemoryImporter:
    """A source-only public project snapshot; no submitted code runs at setup."""

    def __init__(self, sources):
        self.sources = sources

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.sources:
            return None
        source, package, filename = self.sources[fullname]
        return importlib.util.spec_from_loader(fullname, self, origin=filename, is_package=package)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source, package, filename = self.sources[module.__name__]
        module.__file__ = filename
        if package:
            module.__path__ = [filename.rsplit("/", 1)[0]]
        exec(compile(source, filename, "exec"), module.__dict__)


def _prepare_memory_importer(project):
    """Preload declared stdlib imports without putting project on sys.path.

    Contract for a kernel without Landlock: public Python source imports work;
    stdlib imports must be declared in source (dynamic imports already loaded
    by those dependencies also work). Runtime filesystem reads are unavailable.
    """
    project = Path(project).resolve()
    sources = {}
    requested = set()
    optional_submodules = set()
    for directory, directories, files in os.walk(project, followlinks=False):
        for name in files:
            if not name.endswith(".py"):
                continue
            file = Path(directory) / name
            if file.is_symlink():
                raise SandboxUnavailable("Public Python source symlinks are forbidden in memory mode")
            relative = file.relative_to(project)
            parts = list(relative.with_suffix("").parts)
            package = parts[-1] == "__init__"
            if package:
                parts.pop()
            if not parts:
                continue
            fullname = ".".join(parts)
            source = file.read_bytes()
            tree = ast.parse(source, filename=str(relative))
            sources[fullname] = (source, package, "public:/" + relative.as_posix())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    requested.update(item.name for item in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    requested.add(node.module)
                    optional_submodules.update(node.module + "." + item.name for item in node.names if item.name != "*")
    # Support ordinary namespace packages as well as __init__.py packages.
    for fullname in list(sources):
        parts = fullname.split(".")
        for length in range(1, len(parts)):
            parent = ".".join(parts[:length])
            sources.setdefault(parent, (b"", True, "public:/" + "/".join(parts[:length]) + "/__init__.py"))
    local_names = {name.split(".", 1)[0] for name in sources}
    stdlib_root = Path(sysconfig.get_path("stdlib")).resolve()
    for name in sorted(requested | optional_submodules):
        top = name.split(".", 1)[0]
        if top in local_names:
            continue
        if top not in sys.stdlib_module_names or top == "antigravity":
            raise SandboxUnavailable(f"Memory sandbox supports only public modules and stdlib imports: {name}")
        # Resolve before executing the trusted module; the project path is
        # deliberately absent, so app files cannot masquerade as stdlib.
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, AttributeError, ValueError):
            if name in optional_submodules and name not in requested:
                continue  # An imported attribute, rather than a submodule.
            raise SandboxUnavailable(f"Stdlib import unavailable: {name}")
        if spec is None:
            if name in optional_submodules and name not in requested:
                continue
            raise SandboxUnavailable(f"Stdlib import unavailable: {name}")
        if spec.origin not in {"built-in", "frozen", None}:
            origin = Path(spec.origin).resolve()
            if not origin.is_relative_to(stdlib_root) or "site-packages" in origin.parts:
                raise SandboxUnavailable(f"Import is outside the standard library: {name}")
        try:
            importlib.import_module(name)
        except Exception as exc:
            raise SandboxUnavailable(f"Cannot preload standard library import {name}: {type(exc).__name__}") from exc
    return PublicMemoryImporter(sources)


def install(public_project, runtime_files=()):
    """Irreversibly restrict this process; raise on any unavailable protection.

    Call only in a fresh worker before importing any submitted Python. Its
    inherited descriptors must contain only the input/output/error streams.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                           ctypes.c_ulong, ctypes.c_ulong]
    libseccomp = _seccomp_library()
    if libc.prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_DUMPABLE
        _fail(libc, "PR_SET_DUMPABLE")
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        _fail(libc, "PR_SET_NO_NEW_PRIVS")
    abi = libc.syscall(444, 0, 0, 1)
    if abi >= 1:
        _landlock(libc, public_project, runtime_files)
        _seccomp(libseccomp)
        return "landlock"
    # If Landlock is absent, forbid all path-based filesystem access instead.
    # Only a source snapshot and declared trusted stdlib imports are prepared
    # before restrictions. Submitted modules execute after seccomp is loaded.
    importer = _prepare_memory_importer(public_project)
    sys.meta_path.insert(0, importer)
    _seccomp(libseccomp, filesystem_closed=True)
    return "memory-seccomp"
