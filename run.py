from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
import waterline.utils
import os


class RunConfiguration:
    def __init__(self, name, args=[], env={}, cwd=None):
        self.name = name
        self.args = args
        self.env = env
        self.cwd = cwd


class Runner:
    name = "time"

    def run(self, workspace, config, binary):
        """Run the benchmark, and return the metric. By default, it returns the execution time.

        We launch the binary directly and reap it with os.wait4, which returns the
        resource usage for *this* child only. The previous implementation forked a
        multiprocessing worker just to isolate resource.getrusage(RUSAGE_CHILDREN);
        forking this process (which loads numpy/OpenBLAS and runs a background BLAS
        thread pool) inherits OpenBLAS's locked internal mutex and deadlocks the child
        before it ever spawns the benchmark. os.wait4 avoids the fork entirely and is
        strictly more accurate, since RUSAGE_CHILDREN accumulates over all children."""
        assert binary.exists()

        cwd = os.getcwd() if config.cwd is None else config.cwd

        with waterline.utils.cd(cwd):
            proc = subprocess.Popen(
                [binary, *config.args],
                stdout=subprocess.DEVNULL,
                # stderr=subprocess.DEVNULL,
                env=config.env,
                cwd=cwd,
            )
            _, status, usage = os.wait4(proc.pid, 0)
            # Mark the Popen as reaped so its destructor doesn't warn / re-wait.
            proc.returncode = os.waitstatus_to_exitcode(status)

        return {
            "time": usage.ru_utime + usage.ru_stime,
            "stime": usage.ru_stime,
            "utime": usage.ru_utime,
            "major": usage.ru_majflt,
            "minor": usage.ru_minflt,
            "maxrss": usage.ru_maxrss,
            "status": proc.returncode,
        }
