from waterline import Suite, Benchmark, Linker, RunConfiguration
from pathlib import Path
import shutil
import os


class SpecBenchmark(Benchmark):
    def __init__(self, suite, name, bin, runs=[]):
        super().__init__(suite, name)
        self.runs = runs
        self.bin = bin

    def compile(self, output: Path):
        # Run SPEC compilation
        try:
            self.suite.run_support_script("compile", self.name, self.suite.config)
        except Exception as e:
            raise RuntimeError(
                f"Failed to compile SPEC2017 benchmark {self.name}: {e}\n"
                f"Check the SPEC build logs for more details."
            )

        # Check for the binary in the expected location
        src_binary = (
            self.suite.src
            / f"SPEC2017/benchspec/CPU/{self.name}/build/build_peak_gclang.0000/"
            / self.bin
        )
        
        if not src_binary.exists():
            # Provide helpful error message
            build_dir = self.suite.src / f"SPEC2017/benchspec/CPU/{self.name}/build"
            available_builds = list(build_dir.glob("build_*")) if build_dir.exists() else []
            
            error_msg = (
                f"Binary not found: {src_binary}\n"
                f"The benchmark {self.name} compilation may have failed.\n"
            )
            if available_builds:
                error_msg += f"Available build directories: {[b.name for b in available_builds]}\n"
            error_msg += (
                f"Check {build_dir} for compilation logs.\n"
                f"The benchmark may require special configuration or may not be supported."
            )
            raise FileNotFoundError(error_msg)
        
        shutil.copy(src_binary, output)

    def run_configs(self):
        # print('run config for', self.name)
        config = self.suite.config
        if config == "ref":
            config = "refspeed"

        rundir = (
            self.suite.src
            / f"SPEC2017/benchspec/CPU/{self.name}/run/run_peak_{config}_gclang.0000/"
        )
        with open(rundir / "speccmds.cmd") as f:
            for line in f:
                pass
            last_line = line
        # hack: get the arguments :I
        args = last_line.split("peak.gclang ")[1].strip().split(" ")
        print(self.name, args)
        yield RunConfiguration(self.name, args=args, cwd=rundir)

    def link(self, object, output, linker):
        linker.link(
            self.suite.workspace,
            [object],
            output,
            args=["-lm", "-lstdc++", "-lpthread"],
        )


benchmarks = [
    # Integer
    ("600.perlbench_s", "perlbench_s"),
    ("602.gcc_s", "sgcc"),
    ("605.mcf_s", "mcf_s"),
    ("620.omnetpp_s", "omnetpp_s"),
    ("623.xalancbmk_s", "xalancbmk_s"),
    ("625.x264_s", "x264_s"),
    ("631.deepsjeng_s", "deepsjeng_s"),
    ("641.leela_s", "leela_s"),
    ("657.xz_s", "xz_s"),
    # Floating Point
    ("619.lbm_s", "lbm_s"),
    ("638.imagick_s", "imagick_s"),
    ("644.nab_s", "nab_s"),
]

class SPEC2017(Suite):
    name = "SPEC2017"

    def configure(self, tar=None, config="ref", disabled=[]):
        if tar is None:
            raise RuntimeError("No tarball supplied for SPEC2017.")
        self.tarball = Path(tar)
        self.config = config
        for a, b in benchmarks:
            num = int(a.split('.')[0])
            if num in disabled:
                continue
            self.add_benchmark(SpecBenchmark, a, b)

    def acquire(self):
        # the path to the SPEC2017 support folder
        support = Path(__file__).parent / "SPEC2017"
        shutil.copytree(support, self.src)
        shutil.unpack_archive(self.tarball, self.src, format="gztar")

        self.run_support_command(
            "chmod +x -R SPEC2017/bin SPEC2017/tools SPEC2017/*.sh"
        )
        self.run_support_script("install")

    def run_support_command(self, command):
        self.workspace.shell("sh", "-c", f"cd {self.src}; {command}")

    def run_support_script(self, name, *args):
        self.run_support_command(f'scripts/{name}.sh {" ".join(args)}')
